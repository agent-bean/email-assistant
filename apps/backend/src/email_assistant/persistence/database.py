"""Explicit transaction ownership, private errors and shared maintenance exclusion."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from email_assistant.config import DatabaseSettings

MAINTENANCE_KEY = 1200261021


class StorageError(Exception):
    """Sanitized storage failure; never expose driver statements or parameters."""


class Conflict(StorageError):
    """Expected state, version, fence or idempotency payload no longer matches."""


def engine_for(settings: DatabaseSettings, *, admin: bool = False) -> Engine:
    return create_engine(
        settings.url(admin=admin),
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
        pool_pre_ping=True,
    )


def verify_runtime(session: Session) -> None:
    unsafe = session.execute(
        text("""
        SELECT r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
          OR r.rolbypassrls OR has_schema_privilege(current_user,'public','CREATE')
          OR has_database_privilege(current_user,current_database(),'CREATE')
          OR has_database_privilege(current_user,current_database(),'TEMP')
          OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
                     WHERE n.nspname='public' AND pg_has_role(c.relowner,'USAGE'))
        FROM pg_roles r WHERE r.rolname=current_user
    """)
    ).scalar_one()
    if unsafe:
        raise StorageError("Runtime DB role must have only application DML privileges")


def write_lock(session: Session) -> None:
    session.execute(text("SET LOCAL lock_timeout = '3s'"))
    session.execute(text("SET LOCAL statement_timeout = '10s'"))
    session.execute(text("SELECT pg_advisory_xact_lock_shared(:key)"), {"key": MAINTENANCE_KEY})


@contextmanager
def transaction(engine: Engine, *, runtime: bool = True) -> Iterator[Session]:
    try:
        with Session(engine, expire_on_commit=False) as session, session.begin():
            if runtime:
                verify_runtime(session)
            write_lock(session)
            yield session
    except StorageError:
        raise
    except SQLAlchemyError:
        raise StorageError("Storage transaction failed; no partial change committed") from None


def provision_runtime(session: Session, settings: DatabaseSettings) -> None:
    """Called under exclusive maintenance lock after a verified backup."""
    from psycopg import sql

    raw: Any = session.connection().connection.driver_connection
    role = sql.Identifier(settings.runtime_user)
    if (
        raw.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (settings.runtime_user,)).fetchone()
        is not None
    ):
        raise StorageError("Runtime role already exists; verify ownership/grants privately")
    raw.execute(
        sql.SQL(
            "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
            "NOREPLICATION NOBYPASSRLS PASSWORD {}"
        ).format(role, sql.Literal(settings.runtime_password.get_secret_value()))
    )
    grant_runtime(session, settings)


def grant_runtime(session: Session, settings: DatabaseSettings) -> None:
    """Reapply DML grants to an existing safe role after upgrade/isolated restore."""
    from psycopg import sql

    raw: Any = session.connection().connection.driver_connection
    role = sql.Identifier(settings.runtime_user)
    row = raw.execute(
        "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
        "FROM pg_roles WHERE rolname=%s",
        (settings.runtime_user,),
    ).fetchone()
    if row is None or any(row):
        raise StorageError("Existing least-privilege runtime role required")
    raw.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
    raw.execute(
        sql.SQL("REVOKE CREATE, TEMP ON DATABASE {} FROM PUBLIC").format(
            sql.Identifier(settings.database)
        )
    )
    raw.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(settings.database), role
        )
    )
    raw.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
    raw.execute(
        sql.SQL("GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {}").format(role)
    )
    raw.execute(sql.SQL("REVOKE ALL ON alembic_version FROM {}").format(role))

    raw.execute(sql.SQL("ALTER ROLE {} SET lock_timeout='3s'").format(role))
    raw.execute(sql.SQL("ALTER ROLE {} SET statement_timeout='10s'").format(role))
