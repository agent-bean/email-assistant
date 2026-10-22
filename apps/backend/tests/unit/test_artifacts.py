import hashlib
import os
from uuid import uuid4

import pytest

from email_assistant.persistence.artifacts import private_root, verify_file
from email_assistant.persistence.database import StorageError

pytestmark = pytest.mark.unit


def test_private_files_reject_escapes_and_corruption(tmp_path):
    tmp_path.chmod(0o700)
    data = b"permitted synthetic artifact"
    key = uuid4().hex
    path = tmp_path / key
    path.write_bytes(data)
    path.chmod(0o600)
    digest = hashlib.sha256(data).hexdigest()
    verify_file(tmp_path, key, digest, len(data))
    for bad in ["../escape", "/tmp/escape", key + "/nested"]:
        with pytest.raises(StorageError):
            verify_file(tmp_path, bad, digest, len(data))
    path.write_bytes(b"x" * len(data))
    with pytest.raises(StorageError, match="checksum"):
        verify_file(tmp_path, key, digest, len(data))
    path.unlink()
    path.symlink_to("/etc/passwd")
    with pytest.raises(StorageError):
        verify_file(tmp_path, key, digest, len(data))
    path.unlink()
    os.mkfifo(path, 0o600)
    with pytest.raises(StorageError):
        verify_file(tmp_path, key, digest, 0)
    tmp_path.chmod(0o755)
    with pytest.raises(StorageError):
        with private_root(tmp_path):
            pass
