-- M2 — initial schema + RLS: tables (FK order), indexes, updated_at trigger,
-- RLS policies and grants.

-- ─── ADVISORS — the GIP advisor (prescribes and validates) ───
CREATE TABLE advisors (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id   UUID REFERENCES auth.users(id) UNIQUE,
    full_name      VARCHAR(100) NOT NULL,
    dni            VARCHAR(15) UNIQUE NOT NULL,
    ropo_number    VARCHAR(50) NOT NULL,   -- ROPO, "asesoramiento" sector
    account_status VARCHAR(20) CHECK (account_status IN
                       ('PENDING','ACTIVE','SUSPENDED')) DEFAULT 'PENDING',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ
);

-- ─── HOLDINGS — the legal owner of the record (REA/REGEPA + NIF) ───
CREATE TABLE holdings (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advisor_id             UUID NOT NULL REFERENCES advisors(id),
    owner_name             VARCHAR(100) NOT NULL,
    owner_nif              VARCHAR(15) NOT NULL,
    rea_regepa_number      VARCHAR(50) NOT NULL,
    -- Default operator: if the audio names nobody, the owner applies.
    default_operator_name  VARCHAR(100),
    default_operator_ropo  VARCHAR(50),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ
);

-- ─── PLOTS — the where (SIGPAC enclosure) ───
CREATE TABLE plots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    holding_id          UUID NOT NULL REFERENCES holdings(id),
    voice_alias         VARCHAR(100) NOT NULL,   -- "Finca de Pepe", as dictated
    crop                VARCHAR(50) NOT NULL,
    variety             VARCHAR(50),
    enclosure_area_ha   DECIMAL(10,2) NOT NULL,  -- legal cap on treated area
    sigpac_province     VARCHAR(2) NOT NULL,
    sigpac_municipality VARCHAR(3) NOT NULL,
    sigpac_polygon      VARCHAR(3) NOT NULL,
    sigpac_parcel       VARCHAR(5) NOT NULL,
    sigpac_enclosure    VARCHAR(5) NOT NULL,
    lat                 DECIMAL(9,6),            -- centroid: weather fallback
    lon                 DECIMAL(9,6),            -- when the phone sends no GPS
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

-- ─── PRODUCTS — official MAPA product catalog (preloaded) ───
CREATE TABLE products (
    registration_number       VARCHAR(20) PRIMARY KEY,  -- MAPA registration no.
    trade_name                VARCHAR(150) NOT NULL,    -- what the advisor dictates
    active_substance          VARCHAR(150) NOT NULL,
    authorized                BOOLEAN DEFAULT TRUE,
    max_allowed_dose          DECIMAL(10,2),
    dose_unit                 VARCHAR(10),              -- 'L/ha', 'Kg/ha'
    pre_harvest_interval_days INTEGER,                  -- PHI
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── EQUIPMENT — the with-what (ROMA = machine, ROPO = person) ───
CREATE TABLE equipment (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    holding_id            UUID NOT NULL REFERENCES holdings(id),
    equipment_alias       VARCHAR(100) NOT NULL,   -- "tractor", as dictated
    equipment_type        VARCHAR(20) CHECK (equipment_type IN
                              ('TRACTOR','ATOMIZER','BACKPACK','DRONE')),
    roma_number           VARCHAR(50),
    aesa_registration     VARCHAR(50),             -- drones only
    iteaf_inspection_date DATE,                    -- RD 1702/2011
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ
);

-- ─── INTERVENTIONS — the central event ───
-- State machine: OBSERVATION | PRESCRIBED | EXECUTED | ASSESSED
CREATE TABLE interventions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID UNIQUE NOT NULL,    -- idempotency key from the client;
                                             -- UNIQUE already creates its index

    lifecycle_state VARCHAR(15) NOT NULL CHECK (lifecycle_state IN
                        ('OBSERVATION','PRESCRIBED','EXECUTED','ASSESSED')),

    advisor_id                  UUID NOT NULL REFERENCES advisors(id),
    holding_id                  UUID NOT NULL REFERENCES holdings(id),
    plot_id                     UUID NOT NULL REFERENCES plots(id),
    product_registration_number VARCHAR(20) REFERENCES products(registration_number),
                                             -- NULL for OBSERVATION
    equipment_id                UUID REFERENCES equipment(id),  -- NULL for OBSERVATION

    -- ── Observation block (GIP surveillance) ──
    observation           TEXT,              -- "3 catches, below threshold"

    -- ── Prescription block (what the advisor orders) ──
    prescription_date     TIMESTAMPTZ,       -- device timestamp of the audio
    planned_date          DATE,
    prescribed_dose       DECIMAL(10,2),
    target_pest           VARCHAR(100),
    justification         TEXT,
    previous_alternatives TEXT,              -- auto-filled from the plot's
                                             -- observations (≤60 days)
    prescription_pdf_key  VARCHAR(255),

    -- ── Execution block (the real application → CUE/SIEX annotation) ──
    treatment_date        TIMESTAMPTZ,       -- REAL date, from the confirmation
    treated_area_ha       DECIMAL(10,2),     -- ≤ enclosure_area_ha
    applied_dose          DECIMAL(10,2),     -- real (default: prescribed_dose)
    dose_unit             VARCHAR(10),
    spray_volume_l_ha     DECIMAL(8,2),
    operator_name         VARCHAR(100),      -- who drives the tractor
    operator_ropo         VARCHAR(50),       -- their ROPO card
    delivery_note_number  VARCHAR(100),
    earliest_harvest_date DATE,              -- treatment_date + PHI
    iteaf_warning         BOOLEAN DEFAULT FALSE,  -- inspection expired

    -- ── Weather block (captured at execution, for the REAL date) ──
    temperature_c         DECIMAL(4,1),
    relative_humidity_pct DECIMAL(5,2),
    wind_speed_kmh        DECIMAL(5,2),
    wind_direction        VARCHAR(10),
    gps_lat               DECIMAL(9,6),
    gps_lon               DECIMAL(9,6),

    -- ── Assessment block ──
    effectiveness         VARCHAR(10) CHECK (effectiveness IN
                              ('GOOD','FAIR','POOR')),

    -- ── Traceability (internal) ──
    audio_storage_key     VARCHAR(255),
    execution_audio_key   VARCHAR(255),
    raw_transcription     TEXT,
    prompt_version        VARCHAR(10),
    audit_state           VARCHAR(20) CHECK (audit_state IN
                              ('VALID','WEATHER_PENDING','DOSE_ERROR',
                               'PRODUCT_ERROR','AREA_ERROR','FIELD_ERROR')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ
);

-- ─── VALIDATIONS — the advisor's own legal duty ───
-- "Validated by the advisor at least twice, once during the crop cycle and
-- once at the end" (official MAPA advisory document).
CREATE TABLE validations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advisor_id          UUID NOT NULL REFERENCES advisors(id),
    holding_id          UUID NOT NULL REFERENCES holdings(id),
    campaign            VARCHAR(9) NOT NULL,         -- '2026' or '2026-2027'
    type                VARCHAR(10) NOT NULL CHECK (type IN ('MID_CYCLE','FINAL')),
    validation_date     TIMESTAMPTZ NOT NULL,
    conformity          BOOLEAN NOT NULL,
    remarks             TEXT,                        -- mandatory when NOT conform
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    intervention_count  INTEGER NOT NULL,
    validation_pdf_key  VARCHAR(255),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE (holding_id, campaign, type)
);

-- ─── Indexes ───
CREATE INDEX idx_interv_advisor    ON interventions (advisor_id);
CREATE INDEX idx_interv_holding    ON interventions (holding_id);
CREATE INDEX idx_interv_plot_date  ON interventions (plot_id, prescription_date);
CREATE INDEX idx_interv_state      ON interventions (advisor_id, lifecycle_state);
CREATE INDEX idx_interv_product    ON interventions (product_registration_number);
CREATE INDEX idx_interv_equipment  ON interventions (equipment_id);
CREATE INDEX idx_holdings_advisor  ON holdings (advisor_id);
CREATE INDEX idx_plots_holding     ON plots (holding_id);
CREATE INDEX idx_plots_alias       ON plots (holding_id, voice_alias);
CREATE INDEX idx_equipment_holding ON equipment (holding_id, equipment_alias);
CREATE INDEX idx_valid_holding     ON validations (holding_id, campaign);
CREATE INDEX idx_valid_advisor     ON validations (advisor_id);
CREATE INDEX idx_advisors_auth     ON advisors (auth_user_id);

-- ─── updated_at trigger ───
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_advisors_updated      BEFORE UPDATE ON advisors      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_holdings_updated      BEFORE UPDATE ON holdings      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_plots_updated         BEFORE UPDATE ON plots         FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_products_updated      BEFORE UPDATE ON products      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_equipment_updated     BEFORE UPDATE ON equipment     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_interventions_updated BEFORE UPDATE ON interventions FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_validations_updated   BEFORE UPDATE ON validations   FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─── RLS ───
-- Enabled before any policy exists: with RLS on and no policies, nobody sees
-- anything — secure by default. Model: each advisor only sees their own data.
ALTER TABLE advisors      ENABLE ROW LEVEL SECURITY;
ALTER TABLE holdings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE plots         ENABLE ROW LEVEL SECURITY;
ALTER TABLE products      ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment     ENABLE ROW LEVEL SECURITY;
ALTER TABLE interventions ENABLE ROW LEVEL SECURITY;
ALTER TABLE validations   ENABLE ROW LEVEL SECURITY;

-- Advisor.id of the currently authenticated user.
-- SECURITY DEFINER avoids RLS recursion on the advisors table itself;
-- STABLE lets Postgres cache the result within a query.
CREATE OR REPLACE FUNCTION current_advisor_id()
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = ''
AS $$
  SELECT id FROM public.advisors
  WHERE auth_user_id = (SELECT auth.uid())
    AND deleted_at IS NULL
$$;

-- Advisors: each one sees and edits only their own row. INSERT (account
-- creation) is done from the backend with service_role — no self-signup.
CREATE POLICY "advisors_select_own" ON advisors
  FOR SELECT TO authenticated
  USING (auth_user_id = (SELECT auth.uid()));

CREATE POLICY "advisors_update_own" ON advisors
  FOR UPDATE TO authenticated
  USING (auth_user_id = (SELECT auth.uid()))
  WITH CHECK (auth_user_id = (SELECT auth.uid()));

CREATE POLICY "holdings_all_own" ON holdings
  FOR ALL TO authenticated
  USING (advisor_id = (SELECT current_advisor_id()))
  WITH CHECK (advisor_id = (SELECT current_advisor_id()));

-- Plots and equipment: ownership via holding → advisor.
CREATE POLICY "plots_all_own" ON plots
  FOR ALL TO authenticated
  USING (holding_id IN (
    SELECT id FROM holdings
    WHERE advisor_id = (SELECT current_advisor_id())
  ))
  WITH CHECK (holding_id IN (
    SELECT id FROM holdings
    WHERE advisor_id = (SELECT current_advisor_id())
  ));

CREATE POLICY "equipment_all_own" ON equipment
  FOR ALL TO authenticated
  USING (holding_id IN (
    SELECT id FROM holdings
    WHERE advisor_id = (SELECT current_advisor_id())
  ))
  WITH CHECK (holding_id IN (
    SELECT id FROM holdings
    WHERE advisor_id = (SELECT current_advisor_id())
  ));

CREATE POLICY "interventions_all_own" ON interventions
  FOR ALL TO authenticated
  USING (advisor_id = (SELECT current_advisor_id()))
  WITH CHECK (advisor_id = (SELECT current_advisor_id()));

CREATE POLICY "validations_all_own" ON validations
  FOR ALL TO authenticated
  USING (advisor_id = (SELECT current_advisor_id()))
  WITH CHECK (advisor_id = (SELECT current_advisor_id()));

-- Products: read-only catalog for authenticated users; loads/updates are
-- done with service_role (bypasses RLS).
CREATE POLICY "products_read_authenticated" ON products
  FOR SELECT TO authenticated
  USING (true);

-- ─── Grants ───
-- Needed because "Automatically expose new tables" is off; RLS still filters
-- rows. The "anon" role gets nothing: only logged-in users have access.
GRANT USAGE ON SCHEMA public TO authenticated;

GRANT SELECT, UPDATE                 ON advisors      TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON holdings      TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON plots         TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON equipment     TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON interventions TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON validations   TO authenticated;
GRANT SELECT                         ON products      TO authenticated;

-- No GRANT DELETE on purpose: soft-delete (deleted_at) everywhere, so real
-- deletion stays reserved to service_role.
