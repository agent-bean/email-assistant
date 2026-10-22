"""Canonical SQLAlchemy Core metadata. Migrations contain frozen DDL."""

from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def identity() -> Column[Any]:
    return Column("id", UUID(as_uuid=True), primary_key=True)


def account() -> Column[Any]:
    return Column("account_id", UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)


def created() -> Column[Any]:
    return Column(
        "created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


def record_fk(column: str = "id") -> ForeignKeyConstraint:
    return ForeignKeyConstraint([column, "account_id"], ["records.id", "records.account_id"])


accounts = Table(
    "accounts",
    metadata,
    identity(),
    Column("provider", Text, nullable=False),
    Column("subject", Text, nullable=False),
    Column("owner_subject", Text, nullable=False),
    Column("state", Text, nullable=False, server_default="active"),
    created(),
    UniqueConstraint("provider", "subject"),
    CheckConstraint("provider <> '' AND subject <> '' AND owner_subject <> ''", name="identity"),
    CheckConstraint("state IN ('active', 'disconnected')", name="state"),
)
Index(
    "uq_active_gmail",
    accounts.c.provider,
    unique=True,
    postgresql_where=text("provider = 'gmail' AND state = 'active'"),
)
records = Table(
    "records",
    metadata,
    identity(),
    account(),
    Column("record_type", Text, nullable=False),
    Column("revision", Integer, nullable=False, server_default="0"),
    Column("deleted", Boolean, nullable=False, server_default=text("false")),
    created(),
    UniqueConstraint("id", "account_id"),
    CheckConstraint(
        "record_type IN ('company','contact','source','meeting','report','action')", name="type"
    ),
    CheckConstraint("revision >= 0", name="revision"),
)
revisions = Table(
    "revisions",
    metadata,
    identity(),
    account(),
    Column("record_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("submission_key", Text, nullable=False),
    Column("payload_version", Integer, nullable=False, server_default="1"),
    Column("payload", JSONB, nullable=False),
    Column("content_hash", Text, nullable=False),
    created(),
    record_fk("record_id"),
    UniqueConstraint("record_id", "revision", "account_id"),
    UniqueConstraint("record_id", "submission_key"),
    CheckConstraint("revision > 0 AND payload_version = 1", name="version"),
    CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload"),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="hash"),
)
companies = Table(
    "companies",
    metadata,
    identity(),
    account(),
    Column("name", Text, nullable=False),
    Column("domain", Text),
    record_fk(),
    CheckConstraint("name <> ''", name="name"),
)
Index("ix_companies_domain", companies.c.domain)
Index("ix_companies_name", companies.c.name)
contacts = Table(
    "contacts",
    metadata,
    identity(),
    account(),
    Column("address", Text, nullable=False),
    Column("address_key", Text, nullable=False),
    record_fk(),
    UniqueConstraint("account_id", "address_key"),
    CheckConstraint(
        "address_key ~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'", name="address"
    ),
)
company_contacts = Table(
    "company_contacts",
    metadata,
    account(),
    Column("company_id", UUID(as_uuid=True), primary_key=True),
    Column("contact_id", UUID(as_uuid=True), primary_key=True),
    ForeignKeyConstraint(["company_id", "account_id"], ["records.id", "records.account_id"]),
    ForeignKeyConstraint(["contact_id", "account_id"], ["records.id", "records.account_id"]),
)
sources = Table(
    "sources",
    metadata,
    identity(),
    account(),
    Column("provider", Text, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("external_key", Text, nullable=False),
    record_fk(),
    UniqueConstraint("account_id", "provider", "source_type", "external_key"),
)
company_identifiers = Table(
    "company_identifiers",
    metadata,
    identity(),
    account(),
    Column("company_id", UUID(as_uuid=True), nullable=False),
    Column("kind", Text, nullable=False),
    Column("normalized_value", Text, nullable=False),
    Column("source_id", UUID(as_uuid=True), nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("confirmed", Boolean, nullable=False, server_default=text("false")),
    ForeignKeyConstraint(["company_id", "account_id"], ["records.id", "records.account_id"]),
    ForeignKeyConstraint(["source_id", "account_id"], ["records.id", "records.account_id"]),
    UniqueConstraint("company_id", "kind", "normalized_value"),
)
runs = Table(
    "runs",
    metadata,
    identity(),
    account(),
    Column("workflow_kind", Text, nullable=False),
    Column("logical_key", Text, nullable=False),
    Column("input_revision", Text, nullable=False),
    Column("execution_generation", Integer, nullable=False, server_default="0"),
    Column("predecessor_id", UUID(as_uuid=True), ForeignKey("runs.id"), unique=True),
    Column("retry_submission_key", Text),
    Column("state", Text, nullable=False, server_default="queued"),
    Column("version", Integer, nullable=False, server_default="0"),
    created(),
    UniqueConstraint(
        "account_id",
        "workflow_kind",
        "logical_key",
        "input_revision",
        "execution_generation",
        name="uq_run_input_generation",
    ),
    UniqueConstraint("account_id", "retry_submission_key"),
    CheckConstraint(
        "state IN ('queued','running','awaiting_owner','succeeded','partial','failed','canceled')",
        name="state",
    ),
    CheckConstraint("version >= 0 AND execution_generation >= 0", name="version"),
    CheckConstraint(
        "(execution_generation=0 AND predecessor_id IS NULL "
        "AND retry_submission_key IS NULL) OR (execution_generation>0 "
        "AND predecessor_id IS NOT NULL AND retry_submission_key IS NOT NULL)",
        name="generation",
    ),
)
run_steps = Table(
    "run_steps",
    metadata,
    identity(),
    Column("run_id", UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False),
    Column("step_key", Text, nullable=False),
    Column("input_revision", Text, nullable=False),
    Column("input_ref", Text, nullable=False),
    Column("output_ref", Text),
    Column("state", Text, nullable=False, server_default="pending"),
    UniqueConstraint("run_id", "step_key", "input_revision"),
    CheckConstraint("state IN ('pending','running','completed','failed')", name="state"),
    CheckConstraint("state <> 'completed' OR output_ref IS NOT NULL", name="completed"),
)
artifacts = Table(
    "artifacts",
    metadata,
    identity(),
    account(),
    Column("storage_key", Text, nullable=False, unique=True),
    Column("checksum", Text, nullable=False),
    Column("byte_length", BigInteger, nullable=False),
    Column("mime", Text, nullable=False),
    Column("role", Text, nullable=False),
    Column("retention_class", Text, nullable=False),
    Column("expires_at", DateTime(timezone=True)),
    Column("record_id", UUID(as_uuid=True)),
    Column("source_revision", Integer),
    Column("state", Text, nullable=False, server_default="pending"),
    Column("deleted_at", DateTime(timezone=True)),
    created(),
    UniqueConstraint("id", "account_id", "checksum"),
    ForeignKeyConstraint(
        ["record_id", "source_revision", "account_id"],
        ["revisions.record_id", "revisions.revision", "revisions.account_id"],
    ),
    CheckConstraint("storage_key ~ '^[0-9a-f]{32}$'", name="key"),
    CheckConstraint("checksum ~ '^[0-9a-f]{64}$' AND byte_length >= 0", name="bytes"),
    CheckConstraint("state IN ('pending','ready')", name="state"),
    CheckConstraint("(record_id IS NULL) = (source_revision IS NULL)", name="source"),
    CheckConstraint(
        "retention_class IN ('approved_report','temporary','cached_vector')", name="retention"
    ),
    CheckConstraint("retention_class <> 'temporary' OR expires_at IS NOT NULL", name="expiry"),
)
actions = Table(
    "actions",
    metadata,
    identity(),
    account(),
    Column("kind", Text, nullable=False),
    Column("logical_key", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("state", Text, nullable=False, server_default="draft"),
    Column("version", Integer, nullable=False, server_default="0"),
    Column("fence", Integer, nullable=False, server_default="0"),
    Column("evidence_id", UUID(as_uuid=True)),
    created(),
    record_fk(),
    UniqueConstraint("account_id", "kind", "logical_key"),
    UniqueConstraint("id", "account_id", "kind"),
    CheckConstraint("kind IN ('send_reply','forward_report','publish_knowledge')", name="kind"),
    CheckConstraint(
        "state IN ('draft','awaiting_approval','approved','claimed','succeeded',"
        "'failed_known','unknown')",
        name="state",
    ),
    CheckConstraint("version >= 0 AND fence >= 0", name="version"),
)
action_revisions = Table(
    "action_revisions",
    metadata,
    account(),
    Column("action_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("kind", Text, nullable=False),
    Column("destinations", JSONB, nullable=False),
    Column("attachments", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["action_id", "account_id", "kind"],
        ["actions.id", "actions.account_id", "actions.kind"],
        deferrable=True,
        initially="DEFERRED",
    ),
    ForeignKeyConstraint(
        ["action_id", "revision", "account_id"],
        ["revisions.record_id", "revisions.revision", "revisions.account_id"],
    ),
    UniqueConstraint("action_id", "revision", "account_id"),
    CheckConstraint(
        "jsonb_typeof(destinations) = 'array' AND jsonb_typeof(attachments) = 'array'",
        name="snapshot",
    ),
)
actions.append_constraint(
    ForeignKeyConstraint(
        ["id", "current_revision", "account_id"],
        ["action_revisions.action_id", "action_revisions.revision", "action_revisions.account_id"],
        name="fk_actions_current_revision",
        deferrable=True,
        initially="DEFERRED",
        use_alter=True,
    )
)
approvals = Table(
    "approvals",
    metadata,
    identity(),
    account(),
    Column("action_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("actor_ref", Text, nullable=False),
    Column("decision", Text, nullable=False),
    Column("submission_key", Text, nullable=False),
    created(),
    UniqueConstraint("action_id", "revision"),
    UniqueConstraint("account_id", "submission_key"),
    ForeignKeyConstraint(
        ["action_id", "revision", "account_id"],
        ["action_revisions.action_id", "action_revisions.revision", "action_revisions.account_id"],
    ),
    CheckConstraint("decision IN ('approved','rejected') AND actor_ref <> ''", name="decision"),
)
action_attempts = Table(
    "action_attempts",
    metadata,
    identity(),
    account(),
    Column("action_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("attempt_number", Integer, nullable=False),
    Column("claim_token", UUID(as_uuid=True), nullable=False, unique=True),
    Column("fence", Integer, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("lease_until", DateTime(timezone=True), nullable=False),
    Column("heartbeat_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("result", Text),
    Column("provider_id", Text),
    Column("failure_code", Text),
    UniqueConstraint("action_id", "attempt_number"),
    UniqueConstraint("action_id", "fence"),
    ForeignKeyConstraint(
        ["action_id", "revision", "account_id"],
        ["action_revisions.action_id", "action_revisions.revision", "action_revisions.account_id"],
    ),
    CheckConstraint("attempt_number>0 AND fence>0 AND lease_until>started_at", name="claim"),
    CheckConstraint(
        "result IS NULL OR result IN ('succeeded','failed_known','unknown')", name="result"
    ),
    CheckConstraint("(result IS NULL) = (finished_at IS NULL)", name="finished"),
)
Index(
    "uq_live_attempt",
    action_attempts.c.action_id,
    unique=True,
    postgresql_where=text("finished_at IS NULL"),
)
action_evidence = Table(
    "action_evidence",
    metadata,
    identity(),
    account(),
    Column("action_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("kind", Text, nullable=False),
    Column("reference", Text, nullable=False),
    Column("actor_ref", Text, nullable=False),
    created(),
    ForeignKeyConstraint(
        ["action_id", "revision", "account_id"],
        ["action_revisions.action_id", "action_revisions.revision", "action_revisions.account_id"],
    ),
    CheckConstraint(
        "kind IN ('safe_retry','resolution') AND reference <> '' AND actor_ref <> ''",
        name="evidence",
    ),
)
actions.append_constraint(
    ForeignKeyConstraint(
        ["evidence_id"],
        ["action_evidence.id"],
        name="fk_actions_evidence",
        use_alter=True,
        deferrable=True,
        initially="DEFERRED",
    )
)
audit_history = Table(
    "audit_history",
    metadata,
    identity(),
    account(),
    Column("entity_type", Text, nullable=False),
    Column("entity_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("prior_state", Text),
    Column("new_state", Text, nullable=False),
    created(),
)

# Projection identities are typed canonical records; bodies remain in revisions/artifacts.
relationships = Table(
    "relationships",
    metadata,
    identity(),
    account(),
    Column("record_id", UUID(as_uuid=True), nullable=False),
    Column("source_revision", Integer, nullable=False),
    Column("subject_id", UUID(as_uuid=True), nullable=False),
    Column("object_id", UUID(as_uuid=True), nullable=False),
    Column("predicate", Text, nullable=False),
    Column("evidence_id", UUID(as_uuid=True), nullable=False),
    Column("evidence_revision", Integer, nullable=False),
    Column("confirmed", Boolean, nullable=False),
    ForeignKeyConstraint(
        ["record_id", "source_revision", "account_id"],
        ["revisions.record_id", "revisions.revision", "revisions.account_id"],
    ),
    ForeignKeyConstraint(
        ["evidence_id", "evidence_revision", "account_id"],
        ["revisions.record_id", "revisions.revision", "revisions.account_id"],
    ),
    ForeignKeyConstraint(["subject_id", "account_id"], ["records.id", "records.account_id"]),
    ForeignKeyConstraint(["object_id", "account_id"], ["records.id", "records.account_id"]),
)
outbox = Table(
    "outbox",
    metadata,
    identity(),
    account(),
    Column("entity_id", UUID(as_uuid=True), nullable=False),
    Column("entity_type", Text, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("operation", Text, nullable=False),
    Column("schema_version", Integer, nullable=False, server_default="1"),
    created(),
    ForeignKeyConstraint(
        ["entity_id", "revision", "account_id"],
        ["revisions.record_id", "revisions.revision", "revisions.account_id"],
    ),
    UniqueConstraint("entity_type", "entity_id", "revision", "operation"),
    CheckConstraint("operation IN ('upsert','delete') AND schema_version=1", name="event"),
)
projection_deliveries = Table(
    "projection_deliveries",
    metadata,
    Column("event_id", UUID(as_uuid=True), ForeignKey("outbox.id"), primary_key=True),
    Column("target", Text, primary_key=True),
    Column("state", Text, nullable=False, server_default="pending"),
    Column("version", Integer, nullable=False, server_default="0"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("retry_at", DateTime(timezone=True)),
    Column("failure_code", Text),
    CheckConstraint(
        "target IN ('neo4j','qdrant') AND state IN ('pending','applied')", name="state"
    ),
    CheckConstraint("version >= 0 AND attempts >= 0", name="version"),
)
projection_checkpoints = Table(
    "projection_checkpoints",
    metadata,
    Column("entity_id", UUID(as_uuid=True), ForeignKey("records.id"), primary_key=True),
    Column("target", Text, primary_key=True),
    Column("revision", Integer, nullable=False),
    Column("deleted", Boolean, nullable=False),
    Column("version", Integer, nullable=False, server_default="0"),
    CheckConstraint("target IN ('neo4j','qdrant') AND revision>0 AND version>=0", name="version"),
)
index_generations = Table(
    "index_generations",
    metadata,
    identity(),
    Column("provider", Text, nullable=False),
    Column("model", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("dimension", Integer, nullable=False),
    UniqueConstraint("id", "provider", "model", "model_version", "dimension"),
    CheckConstraint(
        "dimension > 0 AND provider <> '' AND model <> '' AND model_version <> ''", name="model"
    ),
)
embedding_cache = Table(
    "embedding_cache",
    metadata,
    identity(),
    account(),
    Column("record_id", UUID(as_uuid=True), nullable=False),
    Column("source_revision", Integer, nullable=False),
    Column("chunk_key", Text, nullable=False),
    Column("chunk_text", Text, nullable=False),
    Column("generation_id", UUID(as_uuid=True), nullable=False),
    Column("provider", Text, nullable=False),
    Column("model", Text, nullable=False),
    Column("model_version", Text, nullable=False),
    Column("dimension", Integer, nullable=False),
    Column("artifact_id", UUID(as_uuid=True), nullable=False),
    Column("artifact_hash", Text, nullable=False),
    ForeignKeyConstraint(
        ["record_id", "source_revision", "account_id"],
        ["revisions.record_id", "revisions.revision", "revisions.account_id"],
    ),
    ForeignKeyConstraint(
        ["generation_id", "provider", "model", "model_version", "dimension"],
        [
            "index_generations.id",
            "index_generations.provider",
            "index_generations.model",
            "index_generations.model_version",
            "index_generations.dimension",
        ],
    ),
    ForeignKeyConstraint(
        ["artifact_id", "account_id", "artifact_hash"],
        ["artifacts.id", "artifacts.account_id", "artifacts.checksum"],
    ),
    UniqueConstraint("record_id", "source_revision", "chunk_key", "generation_id"),
)

# Index FK lookups, except those already covered by a leading primary/unique key.
for table in list(metadata.tables.values()):
    for constraint in table.foreign_key_constraints:
        columns = tuple(constraint.columns)
        existing = [
            tuple(c.columns)
            for c in table.constraints
            if isinstance(c, UniqueConstraint) or c is table.primary_key
        ]
        existing += [tuple(i.columns) for i in table.indexes]
        if not any(cols[: len(columns)] == columns for cols in existing):
            Index("ix_" + table.name + "_" + columns[0].name, *columns)
