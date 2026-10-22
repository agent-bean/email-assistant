from alembic import context

from email_assistant.config import load_database_settings
from email_assistant.models.records import metadata


def run() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    # Operator upgrades go through storage-snapshot.py, which supplies its locked connection.
    if not context.is_offline_mode():
        raise RuntimeError("Use make storage-migrate; verified backup/exclusion required")
    context.configure(
        url=load_database_settings().url(admin=True), target_metadata=metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


run()
