"""add projection storage. Frozen DDL."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r"""

CREATE TABLE index_generations (
	id UUID NOT NULL,
	provider TEXT NOT NULL,
	model TEXT NOT NULL,
	model_version TEXT NOT NULL,
	dimension INTEGER NOT NULL,
	CONSTRAINT pk_index_generations PRIMARY KEY (id),
	CONSTRAINT uq_index_generations_id_provider_model_model_version_dimension UNIQUE (id,
provider, model, model_version, dimension),
	CONSTRAINT ck_index_generations_model CHECK (dimension > 0 AND provider <> '' AND model
<> '' AND model_version <> '')
)

;

CREATE TABLE projection_checkpoints (
	entity_id UUID NOT NULL,
	target TEXT NOT NULL,
	revision INTEGER NOT NULL,
	deleted BOOLEAN NOT NULL,
	version INTEGER DEFAULT '0' NOT NULL,
	CONSTRAINT pk_projection_checkpoints PRIMARY KEY (entity_id, target),
	CONSTRAINT ck_projection_checkpoints_version CHECK (target IN ('neo4j','qdrant') AND
revision>0 AND version>=0),
	CONSTRAINT fk_projection_checkpoints_entity_id FOREIGN KEY(entity_id) REFERENCES records
(id)
)

;

CREATE TABLE outbox (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	entity_id UUID NOT NULL,
	entity_type TEXT NOT NULL,
	revision INTEGER NOT NULL,
	operation TEXT NOT NULL,
	schema_version INTEGER DEFAULT '1' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_outbox PRIMARY KEY (id),
	CONSTRAINT fk_outbox_entity_id_revision_account_id FOREIGN KEY(entity_id, revision,
account_id) REFERENCES revisions (record_id, revision, account_id),
	CONSTRAINT uq_outbox_entity_type_entity_id_revision_operation UNIQUE (entity_type,
entity_id, revision, operation),
	CONSTRAINT ck_outbox_event CHECK (operation IN ('upsert','delete') AND schema_version=1),
	CONSTRAINT fk_outbox_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE relationships (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	record_id UUID NOT NULL,
	source_revision INTEGER NOT NULL,
	subject_id UUID NOT NULL,
	object_id UUID NOT NULL,
	predicate TEXT NOT NULL,
	evidence_id UUID NOT NULL,
	evidence_revision INTEGER NOT NULL,
	confirmed BOOLEAN NOT NULL,
	CONSTRAINT pk_relationships PRIMARY KEY (id),
	CONSTRAINT fk_relationships_record_id_source_revision_account_id FOREIGN KEY(record_id,
source_revision, account_id) REFERENCES revisions (record_id, revision, account_id),
	CONSTRAINT fk_relationships_evidence_id_evidence_revision_account_id FOREIGN
KEY(evidence_id, evidence_revision, account_id) REFERENCES revisions (record_id, revision,
account_id),
	CONSTRAINT fk_relationships_subject_id_account_id FOREIGN KEY(subject_id, account_id)
REFERENCES records (id, account_id),
	CONSTRAINT fk_relationships_object_id_account_id FOREIGN KEY(object_id, account_id)
REFERENCES records (id, account_id),
	CONSTRAINT fk_relationships_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE embedding_cache (
	id UUID NOT NULL,
	account_id UUID NOT NULL,
	record_id UUID NOT NULL,
	source_revision INTEGER NOT NULL,
	chunk_key TEXT NOT NULL,
	chunk_text TEXT NOT NULL,
	generation_id UUID NOT NULL,
	provider TEXT NOT NULL,
	model TEXT NOT NULL,
	model_version TEXT NOT NULL,
	dimension INTEGER NOT NULL,
	artifact_id UUID NOT NULL,
	artifact_hash TEXT NOT NULL,
	CONSTRAINT pk_embedding_cache PRIMARY KEY (id),
	CONSTRAINT fk_embedding_cache_record_id_source_revision_account_id FOREIGN KEY(record_id,
source_revision, account_id) REFERENCES revisions (record_id, revision, account_id),
	CONSTRAINT fk_embedding_cache_generation_id_provider_model_model_v_7de9 FOREIGN
KEY(generation_id, provider, model, model_version, dimension) REFERENCES index_generations
(id, provider, model, model_version, dimension),
	CONSTRAINT fk_embedding_cache_artifact_id_account_id_artifact_hash FOREIGN
KEY(artifact_id, account_id, artifact_hash) REFERENCES artifacts (id, account_id,
checksum),
	CONSTRAINT uq_embedding_cache_record_id_source_revision_chunk_key__4e8f UNIQUE
(record_id, source_revision, chunk_key, generation_id),
	CONSTRAINT fk_embedding_cache_account_id FOREIGN KEY(account_id) REFERENCES accounts (id)
)

;

CREATE TABLE projection_deliveries (
	event_id UUID NOT NULL,
	target TEXT NOT NULL,
	state TEXT DEFAULT 'pending' NOT NULL,
	version INTEGER DEFAULT '0' NOT NULL,
	attempts INTEGER DEFAULT '0' NOT NULL,
	retry_at TIMESTAMP WITH TIME ZONE,
	failure_code TEXT,
	CONSTRAINT pk_projection_deliveries PRIMARY KEY (event_id, target),
	CONSTRAINT ck_projection_deliveries_state CHECK (target IN ('neo4j','qdrant') AND state
IN ('pending','applied')),
	CONSTRAINT ck_projection_deliveries_version CHECK (version >= 0 AND attempts >= 0),
	CONSTRAINT fk_projection_deliveries_event_id FOREIGN KEY(event_id) REFERENCES outbox (id)
)

;
CREATE INDEX ix_outbox_account_id ON outbox (account_id);
CREATE INDEX ix_outbox_entity_id ON outbox (entity_id, revision, account_id);
CREATE INDEX ix_relationships_account_id ON relationships (account_id);
CREATE INDEX ix_relationships_evidence_id ON relationships (evidence_id,
evidence_revision, account_id);
CREATE INDEX ix_relationships_object_id ON relationships (object_id, account_id);
CREATE INDEX ix_relationships_record_id ON relationships (record_id, source_revision,
account_id);
CREATE INDEX ix_relationships_subject_id ON relationships (subject_id, account_id);
CREATE INDEX ix_embedding_cache_account_id ON embedding_cache (account_id);
CREATE INDEX ix_embedding_cache_artifact_id ON embedding_cache (artifact_id, account_id,
artifact_hash);
CREATE INDEX ix_embedding_cache_generation_id ON embedding_cache (generation_id, provider,
model, model_version, dimension);
CREATE INDEX ix_embedding_cache_record_id ON embedding_cache (record_id, source_revision,
account_id);
""")

    op.execute(r"""
CREATE FUNCTION guard_checkpoint() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.revision<=OLD.revision OR NEW.version<>OLD.version+1 OR
       (OLD.deleted AND NOT NEW.deleted) OR
       (NEW.entity_id,NEW.target) IS DISTINCT FROM (OLD.entity_id,OLD.target)
    THEN RAISE EXCEPTION 'stale projection checkpoint'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_checkpoint BEFORE UPDATE ON projection_checkpoints
    FOR EACH ROW EXECUTE FUNCTION guard_checkpoint();
CREATE FUNCTION check_checkpoint_event() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM outbox o JOIN projection_deliveries d ON d.event_id=o.id
        WHERE o.entity_id=NEW.entity_id AND o.revision=NEW.revision AND d.target=NEW.target
        AND d.state='applied' AND NEW.deleted=(o.operation='delete'))
    THEN RAISE EXCEPTION 'checkpoint requires matching applied event'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_checkpoint_event AFTER INSERT OR UPDATE ON projection_checkpoints
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_checkpoint_event();
CREATE FUNCTION guard_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        IF NEW.state<>'pending' OR NEW.version<>0 OR NEW.attempts<>0
        THEN RAISE EXCEPTION 'invalid initial delivery'; END IF;
    ELSIF (NEW.event_id,NEW.target) IS DISTINCT FROM (OLD.event_id,OLD.target)
        OR OLD.state='applied' OR NEW.version<>OLD.version+1 OR NEW.attempts<OLD.attempts
    THEN RAISE EXCEPTION 'invalid delivery update'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_delivery BEFORE INSERT OR UPDATE ON projection_deliveries
    FOR EACH ROW EXECUTE FUNCTION guard_delivery();
CREATE FUNCTION check_applied_delivery() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.state='applied' AND NOT EXISTS (
        SELECT 1 FROM outbox o JOIN projection_checkpoints c ON c.entity_id=o.entity_id
        WHERE o.id=NEW.event_id AND c.target=NEW.target AND c.revision>=o.revision)
    THEN RAISE EXCEPTION 'applied delivery requires checkpoint'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_applied_delivery AFTER UPDATE ON projection_deliveries
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_applied_delivery();
CREATE FUNCTION check_outbox_event() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM records WHERE id=NEW.entity_id AND record_type=NEW.entity_type)
       OR (SELECT count(*) FROM projection_deliveries WHERE event_id=NEW.id)<>2
       OR (SELECT count(*) FROM outbox WHERE entity_id=NEW.entity_id AND revision=NEW.revision)<>1
    THEN RAISE EXCEPTION 'canonical event/targets mismatch'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_outbox_event AFTER INSERT ON outbox
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_outbox_event();
CREATE FUNCTION guard_subtype() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected text;
BEGIN
    expected := CASE TG_TABLE_NAME WHEN 'companies' THEN 'company' WHEN 'contacts' THEN 'contact'
                WHEN 'sources' THEN 'source' ELSE 'action' END;
    IF NOT EXISTS (SELECT 1 FROM records WHERE id=NEW.id AND account_id=NEW.account_id
                   AND record_type=expected) THEN RAISE EXCEPTION 'record type mismatch'; END IF;
    RETURN NEW;
END $$;
CREATE FUNCTION guard_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM companies WHERE id=NEW.company_id) THEN
        RAISE EXCEPTION 'company identity required'; END IF;
    IF TG_TABLE_NAME='company_contacts' THEN
        IF NOT EXISTS (SELECT 1 FROM contacts WHERE id=NEW.contact_id) THEN
            RAISE EXCEPTION 'contact identity required'; END IF;
    ELSE
        IF NOT EXISTS (SELECT 1 FROM sources WHERE id=NEW.source_id) THEN
            RAISE EXCEPTION 'source identity required'; END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE FUNCTION guard_artifact() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.id,NEW.account_id,NEW.storage_key,NEW.checksum,NEW.byte_length,NEW.mime,NEW.role,
        NEW.retention_class,NEW.expires_at,NEW.record_id,NEW.source_revision,NEW.created_at)
       IS DISTINCT FROM
       (OLD.id,OLD.account_id,OLD.storage_key,OLD.checksum,OLD.byte_length,OLD.mime,OLD.role,
        OLD.retention_class,OLD.expires_at,OLD.record_id,OLD.source_revision,OLD.created_at)
       OR (OLD.state='ready' AND NEW.state<>'ready') OR
       (OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS DISTINCT FROM OLD.deleted_at)
    THEN RAISE EXCEPTION 'artifact metadata immutable'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_artifact BEFORE UPDATE ON artifacts
    FOR EACH ROW EXECUTE FUNCTION guard_artifact();
CREATE FUNCTION check_canonical_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent records;
BEGIN
    SELECT * INTO parent FROM records WHERE id=NEW.id;
    IF parent.revision>0 AND (NOT EXISTS (
        SELECT 1 FROM revisions WHERE record_id=parent.id AND revision=parent.revision)
        OR NOT EXISTS (SELECT 1 FROM outbox WHERE entity_id=parent.id
            AND revision=parent.revision AND entity_type=parent.record_type
            AND operation=CASE WHEN parent.deleted THEN 'delete' ELSE 'upsert' END)
        OR (SELECT count(*) FROM projection_deliveries d JOIN outbox o ON o.id=d.event_id
            WHERE o.entity_id=parent.id AND o.revision=parent.revision)<>2)
    THEN RAISE EXCEPTION 'canonical revision/outbox mismatch'; END IF;
    IF parent.record_type='action' AND NOT EXISTS (SELECT 1 FROM actions
        WHERE id=parent.id AND current_revision=parent.revision AND NOT parent.deleted)
    THEN RAISE EXCEPTION 'action canonical revision mismatch'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_canonical_revision AFTER INSERT OR UPDATE ON records
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_canonical_revision();
DO $$ DECLARE name text; BEGIN
    FOREACH name IN ARRAY ARRAY['relationships','outbox','projection_deliveries',
        'projection_checkpoints','index_generations','embedding_cache'] LOOP
        EXECUTE format('CREATE TRIGGER maintenance_lock BEFORE INSERT OR UPDATE OR DELETE '
            'ON %I FOR EACH STATEMENT EXECUTE FUNCTION storage_write_lock()',name);
    END LOOP;
    FOREACH name IN ARRAY ARRAY['relationships','outbox','index_generations','embedding_cache'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION immutable_history()',name);
    END LOOP;
    FOREACH name IN ARRAY ARRAY['companies','contacts','sources','actions'] LOOP
        EXECUTE format('CREATE TRIGGER guard_subtype BEFORE INSERT OR UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION guard_subtype()',name);
    END LOOP;
    FOREACH name IN ARRAY ARRAY['company_contacts','company_identifiers'] LOOP
        EXECUTE format('CREATE TRIGGER guard_membership BEFORE INSERT OR UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION guard_membership()',name);
    END LOOP;
END $$;
CREATE FUNCTION guard_account() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.id,NEW.provider,NEW.subject,NEW.owner_subject,NEW.created_at) IS DISTINCT FROM
       (OLD.id,OLD.provider,OLD.subject,OLD.owner_subject,OLD.created_at)
    THEN RAISE EXCEPTION 'immutable account identity'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_account BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION guard_account();
CREATE FUNCTION guard_snapshot_binding() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE payload jsonb;
BEGIN
    SELECT r.payload INTO payload FROM revisions r WHERE r.record_id=NEW.action_id
        AND r.revision=NEW.revision AND r.account_id=NEW.account_id;
    IF payload->'kind' IS DISTINCT FROM to_jsonb(NEW.kind) OR
       payload->'destinations' IS DISTINCT FROM NEW.destinations OR
       payload->'attachments' IS DISTINCT FROM NEW.attachments
    THEN RAISE EXCEPTION 'action snapshot mismatch'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_snapshot_binding BEFORE INSERT ON action_revisions
    FOR EACH ROW EXECUTE FUNCTION guard_snapshot_binding();
CREATE FUNCTION guard_claim_attachments() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE item jsonb; artifact artifacts;
BEGIN
    IF NEW.state='claimed' THEN
        FOR item IN SELECT jsonb_array_elements(attachments) FROM action_revisions
            WHERE action_id=NEW.id AND revision=NEW.current_revision LOOP
            SELECT * INTO artifact FROM artifacts WHERE id=(item->>'id')::uuid FOR UPDATE;
            IF artifact.id IS NULL OR artifact.account_id<>NEW.account_id OR
               artifact.checksum IS DISTINCT FROM item->>'hash' OR artifact.state<>'ready'
               OR artifact.deleted_at IS NOT NULL OR artifact.byte_length>20971520
            THEN RAISE EXCEPTION 'claim attachment invalid'; END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_claim_attachments BEFORE UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION guard_claim_attachments();
CREATE FUNCTION check_attempt_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent actions; live integer;
BEGIN
    SELECT * INTO parent FROM actions WHERE id=NEW.action_id;
    SELECT count(*) INTO live FROM action_attempts WHERE action_id=parent.id
        AND finished_at IS NULL;
    IF (parent.state='claimed' AND live<>1) OR (parent.state<>'claimed' AND live<>0)
    THEN RAISE EXCEPTION 'attempt/action mismatch'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_attempt_consistency AFTER INSERT OR UPDATE ON action_attempts
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_attempt_consistency();
CREATE FUNCTION guard_attempt_expiry() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.lease_until<=clock_timestamp() AND NEW.result IS DISTINCT FROM 'unknown'
    THEN RAISE EXCEPTION 'expired external claim permits only unknown'; END IF;
    IF NEW.heartbeat_at<OLD.heartbeat_at OR NEW.lease_until<OLD.lease_until THEN
        RAISE EXCEPTION 'claim heartbeat cannot move backward'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_attempt_expiry BEFORE UPDATE ON action_attempts
    FOR EACH ROW EXECUTE FUNCTION guard_attempt_expiry();
CREATE FUNCTION check_revision_commit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM records WHERE id=NEW.record_id
                   AND revision>=NEW.revision)
       OR NOT EXISTS (SELECT 1 FROM outbox WHERE entity_id=NEW.record_id
                      AND revision=NEW.revision)
    THEN RAISE EXCEPTION 'revision requires canonical update and outbox'; END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_revision_commit AFTER INSERT ON revisions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_revision_commit();
CREATE FUNCTION check_metadata_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent uuid;
BEGIN
    parent := CASE WHEN TG_TABLE_NAME IN ('company_contacts','company_identifiers')
                   THEN (to_jsonb(NEW)->>'company_id')::uuid
                   ELSE (to_jsonb(NEW)->>'id')::uuid END;
    IF NOT EXISTS (SELECT 1 FROM records p JOIN revisions r
                   ON r.record_id=p.id AND r.revision=p.revision WHERE p.id=parent
                   AND r.xmin=pg_current_xact_id()::text::xid)
    THEN RAISE EXCEPTION 'canonical metadata requires new revision'; END IF;
    RETURN NULL;
END $$;
DO $$ DECLARE name text; BEGIN
    FOREACH name IN ARRAY ARRAY['companies','contacts','sources',
                               'company_contacts','company_identifiers'] LOOP
        EXECUTE format('CREATE CONSTRAINT TRIGGER check_metadata_mutation '
            'AFTER INSERT OR UPDATE ON %I DEFERRABLE INITIALLY DEFERRED '
            'FOR EACH ROW EXECUTE FUNCTION check_metadata_mutation()',name);
    END LOOP;
END $$;
""")


def downgrade():
    raise RuntimeError("Restore a verified snapshot into a new isolated target")
