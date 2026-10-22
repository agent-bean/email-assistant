"""create canonical storage. Frozen DDL."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r"""

CREATE TABLE accounts (
	id UUID NOT NULL,
	provider TEXT NOT NULL,
	subject TEXT NOT NULL,
	owner_subject TEXT NOT NULL,
	state TEXT DEFAULT 'active' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_accounts PRIMARY KEY (id),
	CONSTRAINT uq_accounts_provider_subject UNIQUE (provider, subject),
	CONSTRAINT ck_accounts_identity CHECK (provider <> '' AND subject <> '' AND owner_subject
<> ''),
	CONSTRAINT ck_accounts_state CHECK (state IN ('active', 'disconnected'))
)

;

CREATE TABLE audit_history (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	entity_type TEXT NOT NULL,
	entity_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	prior_state TEXT,
	new_state TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_audit_history PRIMARY KEY (id),
	CONSTRAINT fk_audit_history_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE records (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	record_type TEXT NOT NULL,
	revision INTEGER DEFAULT '0' NOT NULL,
	deleted BOOLEAN DEFAULT false NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_records PRIMARY KEY (id),
	CONSTRAINT uq_records_id_account_id UNIQUE (id, account_id),
	CONSTRAINT ck_records_type CHECK (record_type IN
('company','contact','source','meeting','report','action')),
	CONSTRAINT ck_records_revision CHECK (revision >= 0),
	CONSTRAINT fk_records_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE runs (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	workflow_kind TEXT NOT NULL,
	logical_key TEXT NOT NULL,
	input_revision TEXT NOT NULL,
	execution_generation INTEGER DEFAULT '0' NOT NULL,
	predecessor_id UUID,
	retry_submission_key TEXT,
	state TEXT DEFAULT 'queued' NOT NULL,
	version INTEGER DEFAULT '0' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_runs PRIMARY KEY (id),
	CONSTRAINT uq_run_input_generation UNIQUE (account_id, workflow_kind, logical_key,
input_revision, execution_generation),
	CONSTRAINT uq_runs_account_id_retry_submission_key UNIQUE (account_id,
retry_submission_key),
	CONSTRAINT ck_runs_state CHECK (state IN
('queued','running','awaiting_owner','succeeded','partial','failed','canceled')),
	CONSTRAINT ck_runs_version CHECK (version >= 0 AND execution_generation >= 0),
	CONSTRAINT ck_runs_generation CHECK ((execution_generation=0 AND predecessor_id IS NULL
AND retry_submission_key IS NULL) OR (execution_generation>0 AND predecessor_id IS NOT
NULL AND retry_submission_key IS NOT NULL)),
	CONSTRAINT fk_runs_account_id FOREIGN KEY(account_id) REFERENCES accounts (id),
	CONSTRAINT uq_runs_predecessor_id UNIQUE (predecessor_id),
	CONSTRAINT fk_runs_predecessor_id FOREIGN KEY(predecessor_id) REFERENCES runs (id)
)

;

CREATE TABLE actions (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	kind TEXT NOT NULL,
	logical_key TEXT NOT NULL,
	current_revision INTEGER NOT NULL,
	state TEXT DEFAULT 'draft' NOT NULL,
	version INTEGER DEFAULT '0' NOT NULL,
	fence INTEGER DEFAULT '0' NOT NULL,
	evidence_id UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_actions PRIMARY KEY (id),
	CONSTRAINT fk_actions_id_account_id FOREIGN KEY(id, account_id) REFERENCES records (id,
account_id),
	CONSTRAINT uq_actions_account_id_kind_logical_key UNIQUE (account_id, kind, logical_key),
	CONSTRAINT uq_actions_id_account_id_kind UNIQUE (id, account_id, kind),
	CONSTRAINT ck_actions_kind CHECK (kind IN
('send_reply','forward_report','publish_knowledge')),
	CONSTRAINT ck_actions_state CHECK (state IN
('draft','awaiting_approval','approved','claimed','succeeded','failed_known','unknown')),
	CONSTRAINT ck_actions_version CHECK (version >= 0 AND fence >= 0),
	CONSTRAINT fk_actions_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE companies (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	name TEXT NOT NULL,
	domain TEXT,
	CONSTRAINT pk_companies PRIMARY KEY (id),
	CONSTRAINT fk_companies_id_account_id FOREIGN KEY(id, account_id) REFERENCES records (id,
account_id),
	CONSTRAINT ck_companies_name CHECK (name <> ''),
	CONSTRAINT fk_companies_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE company_contacts (
	account_id UUID NOT NULL,
	company_id UUID NOT NULL,
	contact_id UUID NOT NULL,
	CONSTRAINT pk_company_contacts PRIMARY KEY (company_id, contact_id),
	CONSTRAINT fk_company_contacts_company_id_account_id FOREIGN KEY(company_id, account_id)
REFERENCES records (id, account_id),
	CONSTRAINT fk_company_contacts_contact_id_account_id FOREIGN KEY(contact_id, account_id)
REFERENCES records (id, account_id),
	CONSTRAINT fk_company_contacts_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE company_identifiers (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	company_id UUID NOT NULL,
	kind TEXT NOT NULL,
	normalized_value TEXT NOT NULL,
	source_id UUID NOT NULL,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	confirmed BOOLEAN DEFAULT false NOT NULL,
	CONSTRAINT pk_company_identifiers PRIMARY KEY (id),
	CONSTRAINT fk_company_identifiers_company_id_account_id FOREIGN KEY(company_id,
account_id) REFERENCES records (id, account_id),
	CONSTRAINT fk_company_identifiers_source_id_account_id FOREIGN KEY(source_id, account_id)
REFERENCES records (id, account_id),
	CONSTRAINT uq_company_identifiers_company_id_kind_normalized_value UNIQUE (company_id,
kind, normalized_value),
	CONSTRAINT fk_company_identifiers_account_id FOREIGN KEY(account_id) REFERENCES accounts
(id)
)

;

CREATE TABLE contacts (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	address TEXT NOT NULL,
	address_key TEXT NOT NULL,
	CONSTRAINT pk_contacts PRIMARY KEY (id),
	CONSTRAINT fk_contacts_id_account_id FOREIGN KEY(id, account_id) REFERENCES records (id,
account_id),
	CONSTRAINT uq_contacts_account_id_address_key UNIQUE (account_id, address_key),
	CONSTRAINT ck_contacts_address CHECK (address_key ~
'^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'),
	CONSTRAINT fk_contacts_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE revisions (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	record_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	submission_key TEXT NOT NULL,
	payload_version INTEGER DEFAULT '1' NOT NULL,
	payload JSONB NOT NULL,
	content_hash TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_revisions PRIMARY KEY (id),
	CONSTRAINT fk_revisions_record_id_account_id FOREIGN KEY(record_id, account_id)
REFERENCES records (id, account_id),
	CONSTRAINT uq_revisions_record_id_revision_account_id UNIQUE (record_id, revision,
account_id),
	CONSTRAINT uq_revisions_record_id_submission_key UNIQUE (record_id, submission_key),
	CONSTRAINT ck_revisions_version CHECK (revision > 0 AND payload_version = 1),
	CONSTRAINT ck_revisions_payload CHECK (jsonb_typeof(payload) = 'object'),
	CONSTRAINT ck_revisions_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
	CONSTRAINT fk_revisions_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE run_steps (
	id UUID NOT NULL,
	run_id UUID NOT NULL,
	step_key TEXT NOT NULL,
	input_revision TEXT NOT NULL,
	input_ref TEXT NOT NULL,
	output_ref TEXT,
	state TEXT DEFAULT 'pending' NOT NULL,
	CONSTRAINT pk_run_steps PRIMARY KEY (id),
	CONSTRAINT uq_run_steps_run_id_step_key_input_revision UNIQUE (run_id, step_key,
input_revision),
	CONSTRAINT ck_run_steps_state CHECK (state IN ('pending','running','completed','failed')),
	CONSTRAINT ck_run_steps_completed CHECK (state <> 'completed' OR output_ref IS NOT NULL),
	CONSTRAINT fk_run_steps_run_id FOREIGN KEY(run_id) REFERENCES runs (id)
)

;

CREATE TABLE sources (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	provider TEXT NOT NULL,
	source_type TEXT NOT NULL,
	external_key TEXT NOT NULL,
	CONSTRAINT pk_sources PRIMARY KEY (id),
	CONSTRAINT fk_sources_id_account_id FOREIGN KEY(id, account_id) REFERENCES records (id,
account_id),
	CONSTRAINT uq_sources_account_id_provider_source_type_external_key UNIQUE (account_id,
provider, source_type, external_key),
	CONSTRAINT fk_sources_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE action_revisions (
	account_id UUID NOT NULL,
	action_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	kind TEXT NOT NULL,
	destinations JSONB NOT NULL,
	attachments JSONB NOT NULL,
	CONSTRAINT pk_action_revisions PRIMARY KEY (action_id, revision),
	CONSTRAINT fk_action_revisions_action_id_account_id_kind FOREIGN KEY(action_id,
account_id, kind) REFERENCES actions (id, account_id, kind) DEFERRABLE INITIALLY DEFERRED,
	CONSTRAINT fk_action_revisions_action_id_revision_account_id FOREIGN KEY(action_id,
revision, account_id) REFERENCES revisions (record_id, revision, account_id),
	CONSTRAINT uq_action_revisions_action_id_revision_account_id UNIQUE (action_id, revision,
account_id),
	CONSTRAINT ck_action_revisions_snapshot CHECK (jsonb_typeof(destinations) = 'array' AND
jsonb_typeof(attachments) = 'array'),
	CONSTRAINT fk_action_revisions_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE artifacts (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	storage_key TEXT NOT NULL,
	checksum TEXT NOT NULL,
	byte_length BIGINT NOT NULL,
	mime TEXT NOT NULL,
	role TEXT NOT NULL,
	retention_class TEXT NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE,
	record_id UUID,
	source_revision INTEGER,
	state TEXT DEFAULT 'pending' NOT NULL,
	deleted_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_artifacts PRIMARY KEY (id),
	CONSTRAINT uq_artifacts_id_account_id_checksum UNIQUE (id, account_id, checksum),
	CONSTRAINT fk_artifacts_record_id_source_revision_account_id FOREIGN KEY(record_id,
source_revision, account_id) REFERENCES revisions (record_id, revision, account_id),
	CONSTRAINT ck_artifacts_key CHECK (storage_key ~ '^[0-9a-f]{32}$'),
	CONSTRAINT ck_artifacts_bytes CHECK (checksum ~ '^[0-9a-f]{64}$' AND byte_length >= 0),
	CONSTRAINT ck_artifacts_state CHECK (state IN ('pending','ready')),
	CONSTRAINT ck_artifacts_source CHECK ((record_id IS NULL) = (source_revision IS NULL)),
	CONSTRAINT ck_artifacts_retention CHECK (retention_class IN
('approved_report','temporary','cached_vector')),
	CONSTRAINT ck_artifacts_expiry CHECK (retention_class <> 'temporary' OR expires_at IS NOT
NULL),
	CONSTRAINT fk_artifacts_account_id FOREIGN KEY(account_id) REFERENCES accounts (id),
	CONSTRAINT uq_artifacts_storage_key UNIQUE (storage_key)
)

;

CREATE TABLE action_attempts (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	action_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	attempt_number INTEGER NOT NULL,
	claim_token UUID NOT NULL,
	fence INTEGER NOT NULL,
	started_at TIMESTAMP WITH TIME ZONE NOT NULL,
	lease_until TIMESTAMP WITH TIME ZONE NOT NULL,
	heartbeat_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	result TEXT,
	provider_id TEXT,
	failure_code TEXT,
	CONSTRAINT pk_action_attempts PRIMARY KEY (id),
	CONSTRAINT uq_action_attempts_action_id_attempt_number UNIQUE (action_id, attempt_number),
	CONSTRAINT uq_action_attempts_action_id_fence UNIQUE (action_id, fence),
	CONSTRAINT fk_action_attempts_action_id_revision_account_id FOREIGN KEY(action_id,
revision, account_id) REFERENCES action_revisions (action_id, revision, account_id),
	CONSTRAINT ck_action_attempts_claim CHECK (attempt_number>0 AND fence>0 AND
lease_until>started_at),
	CONSTRAINT ck_action_attempts_result CHECK (result IS NULL OR result IN
('succeeded','failed_known','unknown')),
	CONSTRAINT ck_action_attempts_finished CHECK ((result IS NULL) = (finished_at IS NULL)),
	CONSTRAINT fk_action_attempts_account_id FOREIGN KEY(account_id) REFERENCES accounts (id),
	CONSTRAINT uq_action_attempts_claim_token UNIQUE (claim_token)
)

;

CREATE TABLE action_evidence (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	action_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	kind TEXT NOT NULL,
	reference TEXT NOT NULL,
	actor_ref TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_action_evidence PRIMARY KEY (id),
	CONSTRAINT fk_action_evidence_action_id_revision_account_id FOREIGN KEY(action_id,
revision, account_id) REFERENCES action_revisions (action_id, revision, account_id),
	CONSTRAINT ck_action_evidence_evidence CHECK (kind IN ('safe_retry','resolution') AND
reference <> '' AND actor_ref <> ''),
	CONSTRAINT fk_action_evidence_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE approvals (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	action_id UUID NOT NULL,
	revision INTEGER NOT NULL,
	actor_ref TEXT NOT NULL,
	decision TEXT NOT NULL,
	submission_key TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_approvals PRIMARY KEY (id),
	CONSTRAINT uq_approvals_action_id_revision UNIQUE (action_id, revision),
	CONSTRAINT uq_approvals_account_id_submission_key UNIQUE (account_id, submission_key),
	CONSTRAINT fk_approvals_action_id_revision_account_id FOREIGN KEY(action_id, revision,
account_id) REFERENCES action_revisions (action_id, revision, account_id),
	CONSTRAINT ck_approvals_decision CHECK (decision IN ('approved','rejected') AND actor_ref
<> ''),
	CONSTRAINT fk_approvals_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;
CREATE UNIQUE INDEX uq_active_gmail ON accounts (provider) WHERE provider = 'gmail' AND
state = 'active';
CREATE INDEX ix_audit_history_account_id ON audit_history (account_id);
CREATE INDEX ix_records_account_id ON records (account_id);
CREATE INDEX ix_actions_evidence_id ON actions (evidence_id);
CREATE INDEX ix_actions_id ON actions (id, current_revision, account_id);
ALTER TABLE actions ADD CONSTRAINT fk_actions_evidence FOREIGN KEY(evidence_id) REFERENCES
action_evidence (id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE actions ADD CONSTRAINT fk_actions_current_revision FOREIGN KEY(id,
current_revision, account_id) REFERENCES action_revisions (action_id, revision,
account_id) DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX ix_companies_account_id ON companies (account_id);
CREATE INDEX ix_companies_domain ON companies (domain);
CREATE INDEX ix_companies_id ON companies (id, account_id);
CREATE INDEX ix_companies_name ON companies (name);
CREATE INDEX ix_company_contacts_account_id ON company_contacts (account_id);
CREATE INDEX ix_company_contacts_company_id ON company_contacts (company_id, account_id);
CREATE INDEX ix_company_contacts_contact_id ON company_contacts (contact_id, account_id);
CREATE INDEX ix_company_identifiers_account_id ON company_identifiers (account_id);
CREATE INDEX ix_company_identifiers_company_id ON company_identifiers (company_id, account_id);
CREATE INDEX ix_company_identifiers_source_id ON company_identifiers (source_id, account_id);
CREATE INDEX ix_contacts_id ON contacts (id, account_id);
CREATE INDEX ix_revisions_account_id ON revisions (account_id);
CREATE INDEX ix_revisions_record_id ON revisions (record_id, account_id);
CREATE INDEX ix_sources_id ON sources (id, account_id);
CREATE INDEX ix_action_revisions_account_id ON action_revisions (account_id);
CREATE INDEX ix_action_revisions_action_id ON action_revisions (action_id, account_id, kind);
CREATE INDEX ix_artifacts_account_id ON artifacts (account_id);
CREATE INDEX ix_artifacts_record_id ON artifacts (record_id, source_revision, account_id);
CREATE INDEX ix_action_attempts_account_id ON action_attempts (account_id);
CREATE INDEX ix_action_attempts_action_id ON action_attempts (action_id, revision, account_id);
CREATE UNIQUE INDEX uq_live_attempt ON action_attempts (action_id) WHERE finished_at IS NULL;
CREATE INDEX ix_action_evidence_account_id ON action_evidence (account_id);
CREATE INDEX ix_action_evidence_action_id ON action_evidence (action_id, revision, account_id);
CREATE INDEX ix_approvals_action_id ON approvals (action_id, revision, account_id);
""")


def downgrade():
    raise RuntimeError("Restore a verified snapshot into a new isolated target")
