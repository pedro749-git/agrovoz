[?25l[90m│[39m
[?25h-- ╔══════════════════════════════════════════════════════════════════╗
-- ║  ESQUEMA COMPLETO — ejecutar en este orden (todo en una query    ║
-- ║  vale, el SQL Editor lo ejecuta secuencialmente)                 ║
-- ║                                                                  ║
-- ║  PASO 1: Tablas (orden por dependencias FK)                      ║
-- ║  PASO 2: Índices                                                 ║
-- ║  PASO 3: Trigger updated_at                                      ║
-- ║  PASO 4: Activar RLS en todas las tablas                         ║
-- ║  PASO 5: Función helper + políticas RLS                          ║
-- ║  PASO 6: Grants (necesarios si desactivaste                      ║
-- ║          "Automatically expose new tables")                      ║
-- ╚══════════════════════════════════════════════════════════════════╝

-- ═══════════════════════════════════════════════════
-- PASO 1 · TABLAS
-- Cambios vs. original:
--   · gen_random_uuid() en vez de uuid_generate_v4() (nativa, sin extensión)
--   · created_at / updated_at en todas las tablas
--   · NOT NULL en FKs estructurales (advisor_id, holding_id)
--   · TIMESTAMPTZ (alias de TIMESTAMP WITH TIME ZONE, idéntico)
-- ═══════════════════════════════════════════════════

-- ─── TABLE 1: ADVISORS — el asesor GIP (prescribe y valida) ───
CREATE TABLE advisors (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id   UUID REFERENCES auth.users(id) UNIQUE,
    full_name      VARCHAR(100) NOT NULL,
    dni            VARCHAR(15) UNIQUE NOT NULL,
    ropo_number    VARCHAR(50) NOT NULL,   -- ROPO sector "asesoramiento"
    account_status VARCHAR(20) CHECK (account_status IN
                       ('PENDING','ACTIVE','SUSPENDED')) DEFAULT 'PENDING',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ
);

-- ─── TABLE 2: HOLDINGS — la explotación (REA/REGEPA + NIF) ───
CREATE TABLE holdings (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advisor_id             UUID NOT NULL REFERENCES advisors(id),
    owner_name             VARCHAR(100) NOT NULL,
    owner_nif              VARCHAR(15) NOT NULL,
    rea_regepa_number      VARCHAR(50) NOT NULL,
    -- Aplicador por defecto: si nadie dice quién aplica, aplica el titular
    default_operator_name  VARCHAR(100),
    default_operator_ropo  VARCHAR(50),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ
);

-- ─── TABLE 3: PLOTS — el dónde (recinto SIGPAC) ───
CREATE TABLE plots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    holding_id          UUID NOT NULL REFERENCES holdings(id),
    voice_alias         VARCHAR(100) NOT NULL,   -- "Finca de Pepe"
    crop                VARCHAR(50) NOT NULL,    -- "Limonero"
    variety             VARCHAR(50),             -- "Fino"
    enclosure_area_ha   DECIMAL(10,2) NOT NULL,  -- límite legal sup. tratada
    sigpac_province     VARCHAR(2) NOT NULL,
    sigpac_municipality VARCHAR(3) NOT NULL,
    sigpac_polygon      VARCHAR(3) NOT NULL,
    sigpac_parcel       VARCHAR(5) NOT NULL,
    sigpac_enclosure    VARCHAR(5) NOT NULL,
    lat                 DECIMAL(9,6),            -- centroide: fallback AEMET
    lon                 DECIMAL(9,6),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

-- ─── TABLE 4: PRODUCTS — vademécum oficial MAPA (precargada) ───
CREATE TABLE products (
    registration_number       VARCHAR(20) PRIMARY KEY,  -- nº registro MAPA
    trade_name                VARCHAR(150) NOT NULL,
    active_substance          VARCHAR(150) NOT NULL,
    authorized                BOOLEAN DEFAULT TRUE,
    max_allowed_dose          DECIMAL(10,2),
    dose_unit                 VARCHAR(10),              -- 'L/ha', 'Kg/ha'
    pre_harvest_interval_days INTEGER,                  -- PHI (plazo seguridad)
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── TABLE 5: EQUIPMENT — el con qué (ROMA = máquina, ROPO = persona) ───
CREATE TABLE equipment (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    holding_id            UUID NOT NULL REFERENCES holdings(id),
    equipment_alias       VARCHAR(100) NOT NULL,   -- "tractor"
    equipment_type        VARCHAR(20) CHECK (equipment_type IN
                              ('TRACTOR','ATOMIZER','BACKPACK','DRONE')),
    roma_number           VARCHAR(50),
    aesa_registration     VARCHAR(50),             -- solo drones
    iteaf_inspection_date DATE,                    -- RD 1702/2011
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ
);

-- ─── TABLE 6: INTERVENTIONS — el evento central ───
-- Máquina de estados: OBSERVATION | PRESCRIBED | EXECUTED | ASSESSED
CREATE TABLE interventions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID UNIQUE NOT NULL,    -- idempotencia (UUID de la PWA)
                                             -- UNIQUE ya crea su índice

    lifecycle_state VARCHAR(15) NOT NULL CHECK (lifecycle_state IN
                        ('OBSERVATION','PRESCRIBED','EXECUTED','ASSESSED')),

    advisor_id                  UUID NOT NULL REFERENCES advisors(id),
    holding_id                  UUID NOT NULL REFERENCES holdings(id),
    plot_id                     UUID NOT NULL REFERENCES plots(id),
    product_registration_number VARCHAR(20) REFERENCES products(registration_number),
                                             -- NULL si OBSERVATION
    equipment_id                UUID REFERENCES equipment(id),  -- NULL si OBSERVATION

    -- ── BLOQUE OBSERVACIÓN (Fase 1 — vigilancia GIP) ──
    observation           TEXT,              -- "3 capturas, bajo umbral"

    -- ── BLOQUE PRESCRIPCIÓN (Fase 2 — el asesor indica) ──
    prescription_date     TIMESTAMPTZ,       -- timestamp del audio
    planned_date          DATE,
    prescribed_dose       DECIMAL(10,2),
    target_pest           VARCHAR(100),
    justification         TEXT,              -- "superación umbral daño económico"
    previous_alternatives TEXT,              -- autocompletado con OBSERVATIONs
                                             -- de la plot (≤60 días)
    prescription_pdf_key  VARCHAR(255),

    -- ── BLOQUE EJECUCIÓN (Fase 3 — anotación CUE) ──
    treatment_date        TIMESTAMPTZ,       -- REAL, de la confirmación
    treated_area_ha       DECIMAL(10,2),     -- ≤ enclosure_area_ha
    applied_dose          DECIMAL(10,2),     -- real (default: prescribed_dose)
    dose_unit             VARCHAR(10),
    spray_volume_l_ha     DECIMAL(8,2),
    operator_name         VARCHAR(100),      -- quién se sube al tractor
    operator_ropo         VARCHAR(50),       -- su carné (básico/cualificado)
    delivery_note_number  VARCHAR(100),      -- nº albarán/factura (FEGA)
    earliest_harvest_date DATE,              -- treatment_date + PHI
    iteaf_warning         BOOLEAN DEFAULT FALSE,  -- inspección caducada

    -- ── BLOQUE CLIMA (AEMET, fecha REAL de ejecución) ──
    temperature_c         DECIMAL(4,1),
    relative_humidity_pct DECIMAL(5,2),
    wind_speed_kmh        DECIMAL(5,2),
    wind_direction        VARCHAR(10),
    gps_lat               DECIMAL(9,6),
    gps_lon               DECIMAL(9,6),

    -- ── BLOQUE RESULTADO (Fase 4) ──
    effectiveness         VARCHAR(10) CHECK (effectiveness IN
                              ('GOOD','FAIR','POOR')),
                          -- UI en español: Buena/Regular/Mala

    -- ── BLOQUE TRAZABILIDAD (interno) ──
    audio_storage_key     VARCHAR(255),
    execution_audio_key   VARCHAR(255),      -- audio corto de confirmación
    raw_transcription     TEXT,
    prompt_version        VARCHAR(10),
    audit_state           VARCHAR(20) CHECK (audit_state IN
                              ('VALID','WEATHER_PENDING','DOSE_ERROR',
                               'PRODUCT_ERROR','AREA_ERROR','FIELD_ERROR')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ
);

-- ─── TABLE 7: VALIDATIONS — Fase 5, obligación del asesor ───
-- "validado por el asesor al menos dos veces, una durante el ciclo
--  de cultivo y otra al final" (instrucciones oficiales doc. MAPA)
CREATE TABLE validations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advisor_id          UUID NOT NULL REFERENCES advisors(id),
    holding_id          UUID NOT NULL REFERENCES holdings(id),
    campaign            VARCHAR(9) NOT NULL,         -- '2026' o '2026-2027'
    type                VARCHAR(10) NOT NULL CHECK (type IN ('MID_CYCLE','FINAL')),
    validation_date     TIMESTAMPTZ NOT NULL,
    conformity          BOOLEAN NOT NULL,
    remarks             TEXT,                        -- obligatorio si NO conforme
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    intervention_count  INTEGER NOT NULL,
    validation_pdf_key  VARCHAR(255),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE (holding_id, campaign, type)
);

-- ═══════════════════════════════════════════════════
-- PASO 2 · ÍNDICES
-- (eliminado idx_tx: el UNIQUE de transaction_id ya crea ese índice)
-- ═══════════════════════════════════════════════════
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

-- ═══════════════════════════════════════════════════
-- PASO 3 · TRIGGER updated_at
-- Mantiene updated_at al día automáticamente en cada UPDATE
-- ═══════════════════════════════════════════════════
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

-- ═══════════════════════════════════════════════════
-- PASO 4 · ACTIVAR RLS (imprescindible ANTES de exponer nada)
-- Con RLS activo y sin políticas, nadie ve nada: seguro por defecto
-- ═══════════════════════════════════════════════════
ALTER TABLE advisors      ENABLE ROW LEVEL SECURITY;
ALTER TABLE holdings      ENABLE ROW LEVEL SECURITY;
ALTER TABLE plots         ENABLE ROW LEVEL SECURITY;
ALTER TABLE products      ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment     ENABLE ROW LEVEL SECURITY;
ALTER TABLE interventions ENABLE ROW LEVEL SECURITY;
ALTER TABLE validations   ENABLE ROW LEVEL SECURITY;

-- ═══════════════════════════════════════════════════
-- PASO 5 · FUNCIÓN HELPER + POLÍTICAS RLS
-- Modelo: cada asesor solo ve/gestiona sus propios datos
-- ═══════════════════════════════════════════════════

-- Devuelve el advisor.id del usuario autenticado actual.
-- SECURITY DEFINER: se ejecuta con permisos del creador, evitando
-- recursión RLS sobre la propia tabla advisors. STABLE permite a
-- Postgres cachear el resultado dentro de la query (rendimiento).
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

-- ── ADVISORS: cada uno ve y edita solo su fila ──
CREATE POLICY "advisors_select_own" ON advisors
  FOR SELECT TO authenticated
  USING (auth_user_id = (SELECT auth.uid()));

CREATE POLICY "advisors_update_own" ON advisors
  FOR UPDATE TO authenticated
  USING (auth_user_id = (SELECT auth.uid()))
  WITH CHECK (auth_user_id = (SELECT auth.uid()));

-- Nota: el INSERT en advisors (alta de cuenta) hazlo desde backend
-- con service_role, o añade aquí una política de INSERT si el
-- registro es self-service.

-- ── HOLDINGS ──
CREATE POLICY "holdings_all_own" ON holdings
  FOR ALL TO authenticated
  USING (advisor_id = (SELECT current_advisor_id()))
  WITH CHECK (advisor_id = (SELECT current_advisor_id()));

-- ── PLOTS (vía holding → advisor) ──
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

-- ── EQUIPMENT (vía holding → advisor) ──
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

-- ── INTERVENTIONS ──
CREATE POLICY "interventions_all_own" ON interventions
  FOR ALL TO authenticated
  USING (advisor_id = (SELECT current_advisor_id()))
  WITH CHECK (advisor_id = (SELECT current_advisor_id()));

-- ── VALIDATIONS ──
CREATE POLICY "validations_all_own" ON validations
  FOR ALL TO authenticated
  USING (advisor_id = (SELECT current_advisor_id()))
  WITH CHECK (advisor_id = (SELECT current_advisor_id()));

-- ── PRODUCTS: vademécum de solo lectura para autenticados ──
-- Las cargas/actualizaciones se hacen con service_role (salta RLS)
CREATE POLICY "products_read_authenticated" ON products
  FOR SELECT TO authenticated
  USING (true);

-- ═══════════════════════════════════════════════════
-- PASO 6 · GRANTS
-- Si desactivaste "Automatically expose new tables" al crear el
-- proyecto, las tablas nuevas NO tienen privilegios para los roles
-- de la API. Estos grants las exponen; RLS sigue filtrando filas.
-- El rol "anon" NO recibe nada: solo usuarios logueados acceden.
-- ═══════════════════════════════════════════════════
GRANT USAGE ON SCHEMA public TO authenticated;

GRANT SELECT, UPDATE                 ON advisors      TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON holdings      TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON plots         TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON equipment     TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON interventions TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON validations   TO authenticated;
GRANT SELECT                         ON products      TO authenticated;

-- Sin GRANT DELETE a propósito: usas soft-delete (deleted_at),
-- así que el borrado real queda reservado a service_role.
