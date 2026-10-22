"""Database transition, immutable history and maintenance guards."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(r"""
CREATE FUNCTION storage_write_lock() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT pg_try_advisory_xact_lock_shared(1200261021) THEN
        RAISE EXCEPTION 'maintenance in progress';
    END IF;
    RETURN NULL;
END $$;
CREATE FUNCTION immutable_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable history'; END $$;
CREATE FUNCTION guard_run() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE previous runs;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.state <> 'queued' OR NEW.version <> 0 THEN
            RAISE EXCEPTION 'invalid initial run';
        END IF;
        IF NEW.predecessor_id IS NOT NULL THEN
            SELECT * INTO previous FROM runs WHERE id=NEW.predecessor_id FOR UPDATE;
            IF previous.id IS NULL OR previous.state NOT IN
('succeeded','partial','failed','canceled')
               OR (NEW.account_id,NEW.workflow_kind,NEW.logical_key,NEW.input_revision,
                   NEW.execution_generation) IS DISTINCT FROM
                  (previous.account_id,previous.workflow_kind,previous.logical_key,
                   previous.input_revision,previous.execution_generation+1) THEN
                RAISE EXCEPTION 'invalid retry generation';
            END IF;
        END IF;
    ELSE
        IF (NEW.id,NEW.account_id,NEW.workflow_kind,NEW.logical_key,NEW.input_revision,
            NEW.execution_generation,NEW.predecessor_id,NEW.retry_submission_key,NEW.created_at)
           IS DISTINCT FROM
           (OLD.id,OLD.account_id,OLD.workflow_kind,OLD.logical_key,OLD.input_revision,
            OLD.execution_generation,OLD.predecessor_id,OLD.retry_submission_key,OLD.created_at)
           OR NEW.version <> OLD.version+1 OR NOT (
             (OLD.state='queued' AND NEW.state IN ('running','canceled')) OR
             (OLD.state='running' AND NEW.state IN
                 ('awaiting_owner','succeeded','partial','failed','canceled')) OR
             (OLD.state='awaiting_owner' AND NEW.state IN ('queued','canceled'))) THEN
            RAISE EXCEPTION 'invalid run transition';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_run BEFORE INSERT OR UPDATE ON runs FOR EACH ROW EXECUTE FUNCTION guard_run();
CREATE FUNCTION guard_step() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='UPDATE' AND (OLD.state='completed' OR
       (NEW.id,NEW.run_id,NEW.step_key,NEW.input_revision,NEW.input_ref) IS DISTINCT FROM
       (OLD.id,OLD.run_id,OLD.step_key,OLD.input_revision,OLD.input_ref)) THEN
        RAISE EXCEPTION 'completed step or identity immutable';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_step BEFORE UPDATE ON run_steps FOR EACH ROW EXECUTE FUNCTION guard_step();
CREATE FUNCTION guard_record() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='UPDATE' THEN
        IF OLD.deleted OR (NEW.id,NEW.account_id,NEW.record_type,NEW.created_at) IS DISTINCT FROM
           (OLD.id,OLD.account_id,OLD.record_type,OLD.created_at)
           OR NEW.revision <> OLD.revision+1 THEN RAISE EXCEPTION 'invalid record revision'; END IF;
    ELSIF NEW.revision<>0 OR NEW.deleted THEN RAISE EXCEPTION 'invalid initial record';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_record BEFORE INSERT OR UPDATE ON records
    FOR EACH ROW EXECUTE FUNCTION guard_record();
CREATE FUNCTION guard_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent records;
BEGIN
    SELECT * INTO parent FROM records WHERE id=NEW.record_id FOR UPDATE;
    IF parent.deleted OR parent.account_id<>NEW.account_id OR NEW.revision<>parent.revision+1
    THEN RAISE EXCEPTION 'stale revision'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_revision BEFORE INSERT ON revisions
    FOR EACH ROW EXECUTE FUNCTION guard_revision();
CREATE FUNCTION guard_action_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent actions; item jsonb; key uuid; digest text;
BEGIN
    SELECT * INTO parent FROM actions WHERE id=NEW.action_id FOR UPDATE;
    IF parent.state IN ('claimed','unknown','succeeded') THEN
        RAISE EXCEPTION 'action intent locked';
    END IF;
    IF jsonb_typeof(NEW.destinations)<>'array' OR jsonb_array_length(NEW.destinations)=0 OR
       jsonb_typeof(NEW.attachments)<>'array' THEN RAISE EXCEPTION 'invalid snapshot'; END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(NEW.destinations) LOOP
        IF jsonb_typeof(item)<>'string' OR length(item#>>'{}')=0 OR
           (NEW.kind<>'publish_knowledge' AND (item#>>'{}') !~
             '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$')
        THEN RAISE EXCEPTION 'invalid destination'; END IF;
    END LOOP;
    IF (SELECT count(*)<>count(DISTINCT value->>'id') FROM jsonb_array_elements(NEW.attachments))
    THEN RAISE EXCEPTION 'duplicate attachment'; END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(NEW.attachments) LOOP
        key := (item->>'id')::uuid; digest := item->>'hash';
        IF NOT EXISTS (SELECT 1 FROM artifacts WHERE id=key AND account_id=NEW.account_id
            AND checksum=digest AND state='ready' AND deleted_at IS NULL AND role='attachment'
            AND byte_length<=20971520) THEN RAISE EXCEPTION 'invalid attachment'; END IF;
    END LOOP;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_action_revision BEFORE INSERT ON action_revisions
    FOR EACH ROW EXECUTE FUNCTION guard_action_revision();
CREATE FUNCTION guard_action() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='INSERT' THEN
        IF NEW.state<>'draft' OR NEW.version<>0 OR NEW.fence<>0 OR NEW.current_revision<>1
        THEN RAISE EXCEPTION 'invalid initial action'; END IF;
        RETURN NEW;
    END IF;
    IF (NEW.id,NEW.account_id,NEW.kind,NEW.logical_key,NEW.created_at) IS DISTINCT FROM
       (OLD.id,OLD.account_id,OLD.kind,OLD.logical_key,OLD.created_at)
       OR NEW.version<>OLD.version+1 THEN RAISE EXCEPTION 'invalid action identity/version'; END IF;
    IF NEW.current_revision<>OLD.current_revision THEN
        IF OLD.state IN ('claimed','unknown','succeeded') OR NEW.state<>'draft' OR
           NEW.current_revision<>OLD.current_revision+1 OR NEW.fence<>OLD.fence
        THEN RAISE EXCEPTION 'action revision locked'; END IF;
    ELSE
        IF NOT ((OLD.state='draft' AND NEW.state='awaiting_approval') OR
           (OLD.state='awaiting_approval' AND NEW.state IN ('approved','draft')) OR
           (OLD.state='approved' AND NEW.state IN ('claimed','draft')) OR
           (OLD.state='claimed' AND NEW.state IN ('succeeded','failed_known','unknown')) OR
           (OLD.state='failed_known' AND NEW.state IN ('approved','draft')) OR
           (OLD.state='unknown' AND NEW.state IN ('succeeded','failed_known'))) THEN
            RAISE EXCEPTION 'invalid action transition';
        END IF;
        IF NEW.state='claimed' THEN
            IF NEW.fence<>OLD.fence+1 THEN RAISE EXCEPTION 'invalid claim fence'; END IF;
        ELSIF NEW.fence<>OLD.fence THEN RAISE EXCEPTION 'invalid fence'; END IF;
        IF OLD.state='unknown' OR (OLD.state='failed_known' AND NEW.state='approved') THEN
            IF NOT EXISTS (SELECT 1 FROM action_evidence e WHERE e.id=NEW.evidence_id
                AND e.action_id=NEW.id AND e.account_id=NEW.account_id
                AND e.revision=NEW.current_revision
                AND e.kind=CASE WHEN OLD.state='unknown' THEN 'resolution' ELSE 'safe_retry' END)
            OR NEW.evidence_id IS NOT DISTINCT FROM OLD.evidence_id
            THEN RAISE EXCEPTION 'explicit evidence required'; END IF;
        END IF;
        IF OLD.state='awaiting_approval' AND NEW.state='draft' AND NOT EXISTS (
            SELECT 1 FROM approvals WHERE action_id=NEW.id AND revision=NEW.current_revision
            AND decision='rejected') THEN RAISE EXCEPTION 'rejection required'; END IF;
        IF OLD.state IN ('approved','failed_known') AND NEW.state='draft' THEN
            RAISE EXCEPTION 'editing requires new revision';
        END IF;
    END IF;
    IF NEW.state IN ('approved','claimed') AND NOT EXISTS (
        SELECT 1 FROM approvals WHERE action_id=NEW.id AND revision=NEW.current_revision
        AND account_id=NEW.account_id AND decision='approved')
    THEN RAISE EXCEPTION 'exact revision approval required'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_action BEFORE INSERT OR UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION guard_action();
CREATE FUNCTION guard_decision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent actions;
BEGIN
    SELECT * INTO parent FROM actions WHERE id=NEW.action_id FOR UPDATE;
    IF parent.state<>'awaiting_approval' OR parent.current_revision<>NEW.revision OR
       NEW.actor_ref<>(SELECT owner_subject FROM accounts WHERE id=NEW.account_id)
    THEN RAISE EXCEPTION 'invalid decision relationship'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_decision BEFORE INSERT ON approvals
    FOR EACH ROW EXECUTE FUNCTION guard_decision();
CREATE FUNCTION guard_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent actions;
BEGIN
    SELECT * INTO parent FROM actions WHERE id=NEW.action_id FOR UPDATE;
    IF parent.current_revision<>NEW.revision OR parent.fence<>NEW.fence OR
       parent.state<>'claimed' THEN RAISE EXCEPTION 'stale attempt'; END IF;
    IF TG_OP='UPDATE' AND (OLD.finished_at IS NOT NULL OR
       (NEW.id,NEW.account_id,NEW.action_id,NEW.revision,NEW.attempt_number,NEW.claim_token,
        NEW.fence,NEW.started_at) IS DISTINCT FROM
       (OLD.id,OLD.account_id,OLD.action_id,OLD.revision,OLD.attempt_number,OLD.claim_token,
        OLD.fence,OLD.started_at)) THEN RAISE EXCEPTION 'immutable attempt identity/result'; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_attempt BEFORE INSERT OR UPDATE ON action_attempts
    FOR EACH ROW EXECUTE FUNCTION guard_attempt();
CREATE FUNCTION check_action_consistency() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent actions; live integer;
BEGIN
    SELECT * INTO parent FROM actions WHERE id=NEW.id;
    SELECT count(*) INTO live FROM action_attempts WHERE action_id=parent.id AND finished_at IS
NULL;
    IF (parent.state='claimed' AND live<>1) OR (parent.state<>'claimed' AND live<>0)
       OR (parent.state IN ('succeeded','failed_known','unknown') AND NOT EXISTS (
           SELECT 1 FROM action_attempts WHERE action_id=parent.id AND fence=parent.fence
           AND revision=parent.current_revision AND (result=parent.state OR
               (result='unknown' AND EXISTS (SELECT 1 FROM action_evidence e
                WHERE e.id=parent.evidence_id AND e.kind='resolution'))))) THEN
        RAISE EXCEPTION 'action/attempt mismatch';
    END IF;
    RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER check_action_consistency AFTER INSERT OR UPDATE ON actions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_action_consistency();
CREATE FUNCTION audit_state() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO audit_history(id,account_id,entity_type,entity_id,revision,prior_state,new_state)
    VALUES(gen_random_uuid(),NEW.account_id,TG_TABLE_NAME,NEW.id,
           CASE WHEN TG_TABLE_NAME='actions' THEN (to_jsonb(NEW)->>'current_revision')::int
                ELSE (to_jsonb(NEW)->>'execution_generation')::int END,
           CASE WHEN TG_OP='UPDATE' THEN OLD.state ELSE NULL END,NEW.state);
    RETURN NULL;
END $$;
CREATE TRIGGER audit_run AFTER INSERT OR UPDATE ON runs
    FOR EACH ROW EXECUTE FUNCTION audit_state();
CREATE TRIGGER audit_action AFTER INSERT OR UPDATE ON actions
    FOR EACH ROW EXECUTE FUNCTION audit_state();
DO $$ DECLARE name text; BEGIN
    FOREACH name IN ARRAY ARRAY['revisions','action_revisions','approvals','action_evidence',
                                'audit_history'] LOOP
        EXECUTE format('CREATE TRIGGER immutable_history BEFORE UPDATE OR DELETE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION immutable_history()',name);
    END LOOP;
    FOR name IN SELECT tablename FROM pg_tables WHERE schemaname='public'
        AND tablename<>'alembic_version' LOOP
        EXECUTE format('CREATE TRIGGER maintenance_lock BEFORE INSERT OR UPDATE OR DELETE '
            'ON %I FOR EACH STATEMENT EXECUTE FUNCTION storage_write_lock()',name);
    END LOOP;
END $$;""")


def downgrade():
    raise RuntimeError("Restore a verified snapshot into a new isolated target")
