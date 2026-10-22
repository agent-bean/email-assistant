"""Owner-only opaque files; pending DB metadata bridges filesystem transactions."""

import hashlib
import os
import re
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from email_assistant.models.records import artifacts
from email_assistant.persistence.database import Conflict, StorageError, write_lock

CHUNK = 1024 * 1024


@contextmanager
def private_root(root: Path) -> Iterator[int]:
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise StorageError("Artifact root must be an absolute private directory without symlinks")
    try:
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            os.close(fd)
            raise StorageError("Artifact root must be owner-only")
        try:
            yield fd
        finally:
            os.close(fd)
    except OSError:
        raise StorageError("Private artifact I/O failed") from None


def key_check(key: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{32}", key):
        raise StorageError("Opaque artifact key required")


def verify_file(root: Path, key: str, checksum: str, byte_length: int) -> None:
    key_check(key)
    with private_root(root) as directory:
        try:
            fd = os.open(key, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or (stat.S_IMODE(info.st_mode) & 0o077)
                    or info.st_size != byte_length
                    or info.st_nlink != 1
                ):
                    raise StorageError("Invalid artifact file or byte length")
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != checksum:
                    raise StorageError("Artifact checksum mismatch")
        except OSError:
            raise StorageError("Artifact missing or unsafe") from None


def prepare(
    session: Session,
    account_id: UUID,
    checksum: str,
    byte_length: int,
    mime: str,
    role: str,
    retention_class: str,
    *,
    record_id: UUID | None = None,
    source_revision: int | None = None,
) -> UUID:
    if not re.fullmatch(r"[0-9a-f]{64}", checksum) or byte_length < 0:
        raise ValueError("Invalid artifact hash/length")
    if role == "attachment" and byte_length > 20 * 1024 * 1024:
        raise ValueError("Attachment exceeds 20 MB")
    identity = uuid4()
    session.execute(
        insert(artifacts).values(
            id=identity,
            account_id=account_id,
            storage_key=uuid4().hex,
            checksum=checksum,
            byte_length=byte_length,
            mime=mime,
            role=role,
            retention_class=retention_class,
            record_id=record_id,
            source_revision=source_revision,
            expires_at=datetime.now(UTC) + timedelta(days=30)
            if retention_class == "temporary"
            else None,
        )
    )
    return identity


def publish(session: Session, root: Path, identity: UUID, source: BinaryIO) -> None:
    write_lock(session)
    row = (
        session.execute(select(artifacts).where(artifacts.c.id == identity).with_for_update())
        .mappings()
        .one()
    )
    if row.deleted_at is not None:
        raise Conflict("Deleted artifact")
    key = row.storage_key
    key_check(key)
    if row.state == "ready":
        verify_file(root, key, row.checksum, row.byte_length)
        return
    with private_root(root) as directory:
        partial = key + ".part"
        try:
            fd = os.open(
                partial,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            digest = hashlib.sha256()
            total = 0
            with os.fdopen(fd, "wb") as output:
                while chunk := source.read(CHUNK):
                    total += len(chunk)
                    if total > row.byte_length:
                        raise StorageError("Artifact exceeds declared size")
                    output.write(chunk)
                    digest.update(chunk)
                if total != row.byte_length or digest.hexdigest() != row.checksum:
                    raise StorageError("Artifact content mismatch")
                output.flush()
                os.fsync(output.fileno())
            os.link(partial, key, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            os.unlink(partial, dir_fd=directory)
            os.fsync(directory)
        except OSError:
            raise StorageError("Artifact write incomplete; pending metadata retained") from None
    verify_file(root, key, row.checksum, row.byte_length)
    session.execute(update(artifacts).where(artifacts.c.id == identity).values(state="ready"))


def inspect_files(session: Session, root: Path) -> dict[str, list[str]]:
    """Detect interrupted writes without deleting anything."""
    rows = list(session.execute(select(artifacts)).mappings())
    with private_root(root):
        names = {p.name for p in root.iterdir()}
    return {
        "pending": [str(r.id) for r in rows if r.state == "pending"],
        "unreferenced": sorted(names - {r.storage_key for r in rows}),
        "missing_ready": [
            str(r.id) for r in rows if r.state == "ready" and r.storage_key not in names
        ],
    }
