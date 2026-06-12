# MVP — Asesor GIP con PWA (v3.1 — alineada con CLAUDE.md: código en inglés, hitos M1-M7)

**Referencia definitiva de principio a fin.**
Todo lo que no está aquí no existe todavía. Todo lo que está aquí es necesario para que funcione algo real.

> **Qué cambia en v3.1 (sobre la v3):** sin cambios de concepto — solo
> alineación con las decisiones del CLAUDE.md para eliminar incongruencias:
> 1. **Todo identificador de código, tabla, columna, estado, error, archivo y
>    endpoint pasa a inglés.** Los acrónimos regulatorios (ROPO, ROMA, SIGPAC,
>    REA/REGEPA, ITEAF) no se traducen: son nombres propios.
> 2. **El texto de cara al usuario sigue en español** (UI, mensajes de error,
>    PDFs legales, audios de demo): son documentos legales españoles para
>    asesores españoles. By design, no limitación.
> 3. **El plan pasa de "3 semanas día a día" a hitos M1-M7** (los del
>    CLAUDE.md): M1 es un spike desechable de un archivo; el repo real con
>    esqueleto hexagonal arranca en M2.
> 4. La narrativa de dominio y normativa de este documento sigue en español
>    (es la lengua del dominio); la tabla de equivalencias §1bis es el puente.
>
> **Regla ante discrepancias:** si este documento y CLAUDE.md difieren en algo
> técnico, manda CLAUDE.md y se corrige aquí.

---

## 0. El ciclo de vida del asesor — y qué problema le resolvemos en cada paso

Cada fase del trabajo real del asesor (según la documentación oficial del MAPA
aprobada por el Comité Fitosanitario Nacional en desarrollo del art. 11 del
RD 1311/2012) tiene un dolor concreto, y el MVP ataca los que ocurren **en el
campo**, que es donde el papel duele.

```
FASE 0 · CONTRATO + DESCRIPCIÓN DE EXPLOTACIÓN (oficina, 1 vez/año)
  Documentos: Contrato de asesoramiento (Anexo I doc. MAPA)
              Descripción de la explotación asesorada (Anexo II doc. MAPA)
  Dolor:      papeleo de arranque de campaña, 1-2 h por cliente
  MVP:        ❌ FUERA (los datos ya viven en advisors/holdings/plots →
              generar estos 2 PDFs con un botón es el roadmap post-MVP nº1)

FASE 1 · VIGILANCIA (campo, todo el año — el 80% de sus visitas)
  Documento:  el asesoramiento "debe quedar reflejado documentalmente"
              (art. 11.2 RD 1311/2012); la mayoría de visitas terminan en
              "NO tratar" y hoy eso no se documenta en ningún sitio
  MVP:        ✅ AUDIO TIPO OBSERVACIÓN (30 seg, sin producto)
              → documenta la vigilancia GIP y se convierte automáticamente
                en las "alternativas previas" de la siguiente prescripción

FASE 2 · PRESCRIPCIÓN (campo, al superarse el umbral)
  Documento:  prescripción del asesor → Registro de Actuaciones
              Fitosanitarias (Anexo III RD 1311/2012) → AL AGRICULTOR
  MVP:        ✅ AUDIO TIPO PRESCRIPCIÓN → PDF firmado con su ROPO en 10 seg
              + bloqueo de producto no autorizado / dosis ilegal /
                superficie > recinto ANTES de llegar al papel

FASE 3 · EJECUCIÓN (la hace el AGRICULTOR, no el asesor)
  Documento:  anotación de la actuación real (= futura anotación CUE/SIEX,
              Reglamento UE 2023/564)
  MVP:        ✅ CONFIRMACIÓN DE EJECUCIÓN (botón o audio de 10 seg):
              fecha real, dosis real, aplicador real (con su carné)
              → clima AEMET de LA FECHA REAL de aplicación
              → fecha mínima de cosecha (PHI, plazo de seguridad)

FASE 4 · SEGUIMIENTO (campo, días después)
  MVP:        ✅ Pantalla detalle: eficacia [Buena/Regular/Mala] + nº albarán

FASE 5 · VALIDACIÓN (mínimo 2 por ciclo de cultivo — OBLIGATORIO)
  Documento:  validación del Registro de Actuaciones: el asesor manifiesta
              su conformidad, una DURANTE el ciclo y otra AL FINAL
              (instrucciones oficiales del documento MAPA)
  MVP:        ✅ BOTÓN "VALIDAR CAMPAÑA": PDF con el listado de actuaciones
              del periodo + declaración de conformidad + firma (nombre + ROPO)

FASE 6 · CONSERVACIÓN (3 años, Reglamento UE 2023/564)
  MVP:        ✅ soft-delete + PDFs en OSS + auditoría
```

**El problema, en una frase:** el asesor pasa más tiempo siendo administrativo
que agrónomo. El MVP convierte cada obligación documental de campo en ≤30
segundos de voz, con la legalidad validada antes de tocar papel.

---

## 0bis. Contexto normativo

| Norma | Qué regula | URL |
|---|---|---|
| RD 1311/2012 (consolidado, últ. mod. 11/2025) | Marco GIP. Arts. 10-15: asesoramiento. Art. 16 + Anexo III: registro y cuaderno | boe.es/buscar/act.php?id=BOE-A-2012-11605 |
| Documento MAPA de asesoramiento GIP | Contrato (Anexo I), descripción de explotación (Anexo II), registro de actuaciones (Anexo III) + 2 validaciones por ciclo | mapa.gob.es → sanidad vegetal → GIP |
| Reglamento (UE) 2023/564 | Contenido y formato electrónico del registro. Conservación 3 años | boe.es/buscar/doc.php?id=DOUE-L-2023-80367 |
| Reglamento (UE) 2025/2203 | Papel válido hasta 31/12/2026; electrónico desde 1/1/2027 | eur-lex.europa.eu |
| RD 34/2025 | CUE voluntario durante el periodo PAC actual | boe.es/buscar/act.php?id=BOE-A-2025-998 |
| RD 1039/2025 | Aplaza a 1/1/2027 el registro electrónico obligatorio en España | boe.es |
| RD 1054/2022 / RD 9/2015 | SIEX, REA, CUE / REGEPA | boe.es |
| RD 1702/2011 | Inspecciones ITEAF de equipos de aplicación | boe.es/buscar/act.php?id=BOE-A-2011-19296 |

```
HOY (jun 2026) → Papel todavía válido (hasta 31/12/2026). Ventana de venta.
1 ENE 2027    → Registro electrónico de fitosanitarios OBLIGATORIO
1 ENE 2028    → CUE completo: >30 ha permanentes+tierras de cultivo ·
                >5 ha regadío · invernadero >0,1 ha · ganaderas (RD 1054/2022)
```

> ⚠️ **Claves legales del diseño:** (1) el registro pertenece a la
> **explotación** (`holding`: titular, NIF, REA/REGEPA), no al asesor —
> cadena `advisors → holdings → plots`; (2) **prescribir ≠ ejecutar ≠
> validar**: máquina de estados, no foto única; (3) la documentación del
> asesoramiento bien cumplimentada **ya cumple** el registro del art. 16.

---

## 1. Estructura del proyecto (= CLAUDE.md, fuente de verdad)

```
gip-advisor/
├── core/
│   ├── domain/
│   │   ├── models.py        ← Advisor, Holding, Plot, Product, Equipment,
│   │   │                      Intervention, Validation, WeatherData
│   │   ├── schemas.py       ← ExtractedFields (Pydantic V2)
│   │   ├── states.py        ← Máquina de estados de la intervención
│   │   └── errors.py        ← 7 errores de dominio + 3 de infraestructura
│   ├── ports/               ← ABCs, se añaden BAJO DEMANDA por hito
│   │   ├── transcriber.py   · extractor.py · repository.py · notifier.py
│   │   ├── storage.py       · weather.py   · pdf_generator.py
│   └── services/
│       ├── registration_pipeline.py   ← FLUJO A: audio → obs/presc/ejec
│       ├── execution_service.py       ← FLUJO B: confirmar ejecución
│       └── validation_service.py      ← FLUJO C: validación de campaña
├── adapters/
│   ├── inbound/   api.py (FastAPI)
│   └── outbound/  qwen_audio.py · qwen_instruct.py · supabase_repo.py
│                  oss_storage.py · aemet_weather.py · reportlab_pdf.py
├── pwa/           (M4+) React + Vite + Tailwind + vite-plugin-pwa
│   └── src/pages/ Login.jsx · Home.jsx · Plots.jsx ·
│                  InterventionDetail.jsx · Validation.jsx
│   └── src/hooks/ useRecording.js · useOfflineQueue.js · useSupabase.js
├── config/        settings.py · container.py · .env(.example)
├── prompts/       extraction_v1.md (few-shot EN ESPAÑOL: es lo que oye Qwen)
├── spike/         main.py (M1, desechable, nunca importado por el paquete)
└── docs/          mvp_asesor_gip_v3.1.md · decisions.md
```

Stack sin cambios: FastAPI + Pydantic V2 · Supabase (PostgreSQL + magic link) ·
Qwen-Audio + Qwen Instruct (DashScope) · Alibaba OSS · AEMET OpenData ·
ReportLab · React PWA · despliegue en Alibaba ECS. Variables de entorno: las
de v2.

## 1bis. Tabla de equivalencias (dominio español ↔ código inglés)

| Dominio (este doc) | Código/BD | Dominio | Código/BD |
|---|---|---|---|
| técnico/asesor | `advisor` | actuación | `intervention` |
| explotación | `holding` | validación | `validation` |
| parcela / recinto | `plot` / `enclosure` | aplicador | `operator` |
| producto | `product` | dosis | `dose` |
| maquinaria | `equipment` | plaga objetivo | `target_pest` |
| plazo de seguridad | `pre_harvest_interval_days` (PHI) | fecha mín. cosecha | `earliest_harvest_date` |
| OBSERVACIÓN/PRESCRITA/EJECUTADA/VALORADA | `OBSERVATION`/`PRESCRIBED`/`EXECUTED`/`ASSESSED` | albarán | `delivery_note_number` |

Acrónimos intactos en identificadores: `ropo_number`, `roma_number`,
`sigpac_province`, `rea_regepa_number`, `iteaf_inspection_date`.

---

## 2. La máquina de estados — el corazón del diseño

Una **intervention** nace de un audio y avanza por estados que reflejan el
ciclo legal real:

```
                  audio "no tratar"
                 ┌──────────────────→  OBSERVATION  (terminal)
                 │                     · documenta la vigilancia GIP (Fase 1)
                 │                     · alimenta previous_alternatives futuras
  AUDIO ─────────┤
                 │  audio "prescribo"
                 ├──────────────────→  PRESCRIBED
                 │                     · PDF de prescripción → al agricultor
                 │                     · planned_date, prescribed_dose
                 │                            │ confirmar ejecución
                 │                            ▼ (botón o audio corto, Fase 3)
                 │  audio "ya aplicado"   EXECUTED
                 └──────────────────→     · treatment_date REAL
                    (asesor llega con     · dosis/superficie/operator REALES
                     el tratamiento ya    · clima AEMET de la fecha REAL
                     hecho: crea          · earliest_harvest_date (PHI)
                     PRESCRIBED+EXECUTED  · es la anotación CUE/SIEX
                     en un solo paso)            │ seguimiento (Fase 4)
                                                 ▼
                                             ASSESSED
                                             · eficacia + delivery_note_number
```

En paralelo, **por holding y campaña**, la validación del asesor (Fase 5):
`MID_CYCLE` (durante el ciclo) + `FINAL` (al cierre) → PDF firmado de
conformidad.

Reglas (`core/domain/states.py`):
- `OBSERVATION` es terminal: sin producto ni dosis.
- `PRESCRIBED → EXECUTED` es el único avance de una prescripción.
- Nada retrocede (registro legal): correcciones = nueva intervention +
  soft-delete de la anterior.
- `ASSESSED` requiere `EXECUTED` previa.
- El clima se captura **al confirmar la ejecución** (fecha real; histórico
  AEMET si es diferida), no al grabar la prescripción.

---

## 3. Base de datos — 7 tablas (identificadores en inglés) IGNORAR IR ABAJO DEL DOCUMENTO PARA VER TABLAS ACTUALIZADAS

```sql
-- ═══════════════════════════════════════════════════
-- TABLE 1: ADVISORS — el asesor GIP (prescribe y valida)
-- ═══════════════════════════════════════════════════
CREATE TABLE advisors (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_user_id   UUID REFERENCES auth.users(id) UNIQUE,
    full_name      VARCHAR(100) NOT NULL,
    dni            VARCHAR(15) UNIQUE NOT NULL,
    ropo_number    VARCHAR(50) NOT NULL,   -- ROPO sector "asesoramiento"
    account_status VARCHAR(20) CHECK (account_status IN
                       ('PENDING','ACTIVE','SUSPENDED')) DEFAULT 'PENDING',
    deleted_at     TIMESTAMP WITH TIME ZONE
);

-- ═══════════════════════════════════════════════════
-- TABLE 2: HOLDINGS — la explotación, titular legal del registro/CUE
-- FEGA agrupa por nº REA/REGEPA + NIF del titular.
-- ═══════════════════════════════════════════════════
CREATE TABLE holdings (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advisor_id             UUID REFERENCES advisors(id),
    owner_name             VARCHAR(100) NOT NULL,
    owner_nif              VARCHAR(15) NOT NULL,
    rea_regepa_number      VARCHAR(50) NOT NULL,
    -- Aplicador por defecto: si nadie dice quién aplica, aplica el titular
    default_operator_name  VARCHAR(100),
    default_operator_ropo  VARCHAR(50),
    deleted_at             TIMESTAMP WITH TIME ZONE
);

-- ═══════════════════════════════════════════════════
-- TABLE 3: PLOTS — el dónde (recinto SIGPAC)
-- ═══════════════════════════════════════════════════
CREATE TABLE plots (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    holding_id         UUID REFERENCES holdings(id),
    voice_alias        VARCHAR(100) NOT NULL,   -- "Finca de Pepe" (en español)
    crop               VARCHAR(50) NOT NULL,    -- "Limonero"
    variety            VARCHAR(50),             -- "Fino"
    enclosure_area_ha  DECIMAL(10,2) NOT NULL,  -- límite legal de sup. tratada
    sigpac_province    VARCHAR(2) NOT NULL,
    sigpac_municipality VARCHAR(3) NOT NULL,
    sigpac_polygon     VARCHAR(3) NOT NULL,
    sigpac_parcel      VARCHAR(5) NOT NULL,
    sigpac_enclosure   VARCHAR(5) NOT NULL,
    lat                DECIMAL(9,6),            -- centroide: fallback AEMET
    lon                DECIMAL(9,6),
    deleted_at         TIMESTAMP WITH TIME ZONE
);

-- ═══════════════════════════════════════════════════
-- TABLE 4: PRODUCTS — vademécum oficial MAPA (precargada)
-- ═══════════════════════════════════════════════════
CREATE TABLE products (
    registration_number       VARCHAR(20) PRIMARY KEY,  -- nº registro MAPA
    trade_name                VARCHAR(150) NOT NULL,    -- lo que dicta el asesor
    active_substance          VARCHAR(150) NOT NULL,
    authorized                BOOLEAN DEFAULT TRUE,
    max_allowed_dose          DECIMAL(10,2),
    dose_unit                 VARCHAR(10),              -- 'L/ha', 'Kg/ha'
    pre_harvest_interval_days INTEGER                   -- PHI (plazo seguridad)
);

-- ═══════════════════════════════════════════════════
-- TABLE 5: EQUIPMENT — el con qué (ROMA ≠ ROPO: máquina vs persona)
-- ═══════════════════════════════════════════════════
CREATE TABLE equipment (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    holding_id            UUID REFERENCES holdings(id),
    equipment_alias       VARCHAR(100) NOT NULL,   -- "tractor" (en español)
    equipment_type        VARCHAR(20) CHECK (equipment_type IN
                              ('TRACTOR','ATOMIZER','BACKPACK','DRONE')),
    roma_number           VARCHAR(50),
    aesa_registration     VARCHAR(50),             -- solo drones
    iteaf_inspection_date DATE,                    -- RD 1702/2011
    deleted_at            TIMESTAMP WITH TIME ZONE
);

-- ═══════════════════════════════════════════════════
-- TABLE 6: INTERVENTIONS — el evento central
-- Máquina de estados: OBSERVATION | PRESCRIBED | EXECUTED | ASSESSED
-- ═══════════════════════════════════════════════════
CREATE TABLE interventions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id  UUID UNIQUE NOT NULL,    -- idempotencia (UUID de la PWA)

    lifecycle_state VARCHAR(15) NOT NULL CHECK (lifecycle_state IN
                        ('OBSERVATION','PRESCRIBED','EXECUTED','ASSESSED')),

    advisor_id                  UUID REFERENCES advisors(id),
    holding_id                  UUID REFERENCES holdings(id),
    plot_id                     UUID REFERENCES plots(id),
    product_registration_number VARCHAR(20) REFERENCES products(registration_number),
                                             -- NULL si OBSERVATION
    equipment_id                UUID REFERENCES equipment(id),  -- NULL si OBSERVATION

    -- ── BLOQUE OBSERVACIÓN (Fase 1 — vigilancia GIP) ────────────────────────
    observation           TEXT,              -- "3 capturas, bajo umbral"

    -- ── BLOQUE PRESCRIPCIÓN (Fase 2 — el asesor indica) ─────────────────────
    prescription_date     TIMESTAMP WITH TIME ZONE,  -- timestamp del audio
    planned_date          DATE,
    prescribed_dose       DECIMAL(10,2),
    target_pest           VARCHAR(100),
    justification         TEXT,              -- "superación umbral daño económico"
    previous_alternatives TEXT,              -- autocompletado con OBSERVATIONs
                                             -- de la plot (≤60 días)
    prescription_pdf_key  VARCHAR(255),

    -- ── BLOQUE EJECUCIÓN (Fase 3 — anotación CUE) ───────────────────────────
    treatment_date        TIMESTAMP WITH TIME ZONE,  -- REAL, de la confirmación
    treated_area_ha       DECIMAL(10,2),     -- ≤ enclosure_area_ha
    applied_dose          DECIMAL(10,2),     -- real (default: prescribed_dose)
    dose_unit             VARCHAR(10),
    spray_volume_l_ha     DECIMAL(8,2),
    operator_name         VARCHAR(100),      -- quién se sube al tractor
    operator_ropo         VARCHAR(50),       -- su carné (básico/cualificado)
    delivery_note_number  VARCHAR(100),      -- nº albarán/factura (FEGA)
    earliest_harvest_date DATE,              -- treatment_date + PHI
    iteaf_warning         BOOLEAN DEFAULT FALSE,  -- inspección caducada

    -- ── BLOQUE CLIMA (AEMET, fecha REAL de ejecución) ───────────────────────
    temperature_c         DECIMAL(4,1),
    relative_humidity_pct DECIMAL(5,2),
    wind_speed_kmh        DECIMAL(5,2),
    wind_direction        VARCHAR(10),
    gps_lat               DECIMAL(9,6),
    gps_lon               DECIMAL(9,6),

    -- ── BLOQUE RESULTADO (Fase 4) ───────────────────────────────────────────
    effectiveness         VARCHAR(10) CHECK (effectiveness IN
                              ('GOOD','FAIR','POOR')),
                          -- UI en español: Buena/Regular/Mala

    -- ── BLOQUE TRAZABILIDAD (interno) ───────────────────────────────────────
    audio_storage_key     VARCHAR(255),
    execution_audio_key   VARCHAR(255),      -- audio corto de confirmación
    raw_transcription     TEXT,
    prompt_version        VARCHAR(10),
    audit_state           VARCHAR(20) CHECK (audit_state IN
                              ('VALID','WEATHER_PENDING','DOSE_ERROR',
                               'PRODUCT_ERROR','AREA_ERROR','FIELD_ERROR')),
    deleted_at            TIMESTAMP WITH TIME ZONE
);

-- ═══════════════════════════════════════════════════
-- TABLE 7: VALIDATIONS — Fase 5, obligación del asesor
-- "validado por el asesor al menos dos veces, una durante el ciclo
--  de cultivo y otra al final" (instrucciones oficiales doc. MAPA)
-- ═══════════════════════════════════════════════════
CREATE TABLE validations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advisor_id          UUID REFERENCES advisors(id),
    holding_id          UUID REFERENCES holdings(id),
    campaign            VARCHAR(9) NOT NULL,         -- '2026' o '2026-2027'
    type                VARCHAR(10) NOT NULL CHECK (type IN ('MID_CYCLE','FINAL')),
    validation_date     TIMESTAMP WITH TIME ZONE NOT NULL,
    conformity          BOOLEAN NOT NULL,
    remarks             TEXT,                        -- obligatorio si NO conforme
    period_start        DATE NOT NULL,
    period_end          DATE NOT NULL,
    intervention_count  INTEGER NOT NULL,
    validation_pdf_key  VARCHAR(255),
    deleted_at          TIMESTAMP WITH TIME ZONE,
    UNIQUE (holding_id, campaign, type)
);

-- ═══════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════
CREATE UNIQUE INDEX idx_tx ON interventions (transaction_id);
CREATE INDEX idx_interv_advisor    ON interventions (advisor_id);
CREATE INDEX idx_interv_holding    ON interventions (holding_id);
CREATE INDEX idx_interv_plot_date  ON interventions (plot_id, prescription_date);
CREATE INDEX idx_interv_state      ON interventions (advisor_id, lifecycle_state);
CREATE INDEX idx_holdings_advisor  ON holdings (advisor_id);
CREATE INDEX idx_plots_holding     ON plots (holding_id);
CREATE INDEX idx_plots_alias       ON plots (holding_id, voice_alias);
CREATE INDEX idx_equipment_holding ON equipment (holding_id, equipment_alias);
CREATE INDEX idx_valid_holding     ON validations (holding_id, campaign);
```

> Lookup por voz: el alias se busca en todas las plots de todos los holdings
> del asesor (`JOIN holdings ON holdings.advisor_id = ...`). Aliases únicos
> por asesor; el dashboard rechaza colisiones al dar de alta.

---

## 4. Checklist de campos oficiales — auditoría de cobertura

| Campo oficial | Exigido por | Quién lo aporta | Dónde vive |
|---|---|---|---|
| Titular (nombre, NIF) | Cuaderno Parte I / Regl. 2023/564 | Alta dashboard | `holdings.owner_*` |
| Nº REA/REGEPA | RD 1054/2022 / RD 9/2015 | Alta dashboard | `holdings.rea_regepa_number` |
| Asesor (nombre, nº ROPO) | Doc. MAPA / art. 12 RD 1311/2012 | Alta cuenta | `advisors` |
| Referencia SIGPAC completa | Anexo III / cuaderno modelo | Alta dashboard | `plots.sigpac_*` |
| Cultivo y variedad | Anexo III / Regl. 2023/564 | Alta dashboard | `plots.crop`, `variety` |
| Superficie tratada (≤ recinto) | Anexo III / Regl. 2023/564 | Voz o confirmación | `treated_area_ha` |
| Fecha (y hora) de aplicación | Regl. 2023/564 | Confirmación ejecución | `treatment_date` |
| Producto: nombre + nº registro | Anexo III / Regl. 2023/564 | Voz → lookup | `products.registration_number` |
| Dosis aplicada | Regl. 2023/564 | Voz / confirmación | `applied_dose` |
| Plaga/motivo | Anexo III | Voz | `target_pest` |
| Justificación GIP + alternativas | Anexo I / doc. MAPA | Voz + observaciones previas | `justification`, `previous_alternatives` |
| Aplicador: identidad + carné | Anexo III / cuaderno §1.2 | Voz o defecto holding | `operator_name`, `operator_ropo` |
| Equipo + nº ROMA | Anexo III / cuaderno | Voz → lookup | `equipment.roma_number` |
| Inspección ITEAF | RD 1702/2011 / cuaderno | Alta dashboard | `iteaf_inspection_date` + `iteaf_warning` |
| PHI → fecha mínima cosecha | Etiqueta oficial (Regl. 1107/2009) | Sistema | `earliest_harvest_date` |
| Nº albarán/factura | FEGA | Seguimiento (Fase 4) | `delivery_note_number` |
| Eficacia | Cuaderno / buenas prácticas GIP | Seguimiento (Fase 4) | `effectiveness` |
| Validación ×2 por ciclo | Doc. MAPA (instrucciones) | Botón Validar (Fase 5) | `validations` |
| Conservación 3 años | Regl. 2023/564 | Sistema | soft-delete + OSS |
| Clima en la aplicación | Buena práctica (no obligatorio) | AEMET automático | bloque clima |

Fuera de alcance: semillas tratadas, poscosecha, locales de almacenamiento,
y los documentos de Fase 0 (sus datos ya viven en advisors/holdings/plots).

---

## 5. Dominio — errors.py, states.py, schemas.py

```python
# core/domain/errors.py
class DoseError(Exception):
    """Applied/prescribed dose exceeds the product's legal maximum."""

class ProductError(Exception):
    """Product not authorized or expired."""

class AreaError(Exception):
    """Treated area exceeds the SIGPAC enclosure area."""

class MissingFieldError(Exception):
    """LLM failed to extract a mandatory field from the audio."""

class PlotNotFoundError(Exception):
    """voice_alias does not exist for this advisor."""

class EquipmentNotFoundError(Exception):
    """equipment_alias does not exist for this advisor."""

class StateTransitionError(Exception):
    """Illegal lifecycle transition (e.g. assess before execute)."""

# Infrastructure — nombres por PORT, no por proveedor (un cambio de
# proveedor no debe tocar el core; el adapter traduce en la frontera)
class TranscriptionError(Exception): ...
class ExtractionError(Exception): ...
class WeatherError(Exception): ...
class StorageError(Exception): ...
```

```python
# core/domain/states.py
VALID_TRANSITIONS = {
    None:          {'OBSERVATION', 'PRESCRIBED', 'EXECUTED'},  # EXECUTED directa:
                                                               # el asesor llega con
                                                               # el tratamiento hecho
    'PRESCRIBED':  {'EXECUTED'},
    'EXECUTED':    {'ASSESSED'},
    'OBSERVATION': set(),   # terminal
    'ASSESSED':    set(),   # terminal
}

def validate_transition(current: str | None, new: str) -> None:
    if new not in VALID_TRANSITIONS.get(current, set()):
        raise StateTransitionError(f"{current} → {new} not allowed")
```

```python
# core/domain/schemas.py — Pydantic V2, optionals with explicit = None
from typing import Literal, Optional
from pydantic import BaseModel

class ExtractedFields(BaseModel):
    """What Qwen Instruct extracts from the audio. The LLM classifies the type."""
    record_type: Literal['OBSERVATION', 'PRESCRIPTION', 'EXECUTION']
    plot_alias: str                                # mandatory ALWAYS

    # Mandatory if PRESCRIPTION or EXECUTION (enforced in the pipeline):
    product_name: Optional[str] = None
    dose: Optional[float] = None
    dose_unit: Optional[str] = None
    target_pest: Optional[str] = None
    equipment_alias: Optional[str] = None

    # Always optional:
    observation: Optional[str] = None              # if OBSERVATION
    spray_volume_l_ha: Optional[float] = None
    treated_area_ha: Optional[float] = None
    justification: Optional[str] = None
    previous_alternatives: Optional[str] = None
    operator_name: Optional[str] = None
    operator_ropo: Optional[str] = None
    planned_date: Optional[str] = None             # "el viernes", "pasado mañana"
```

`models.py`: dataclasses `Advisor`, `Holding`, `Plot`, `Product`, `Equipment`,
`WeatherData`, `Intervention` (con `lifecycle_state`, los dos bloques de
fechas/dosis, `earliest_harvest_date`, `iteaf_warning`) y `Validation`.

---

## 6. Los 3 flujos del backend

### FLUJO A — Audio entrante (`registration_pipeline.py`)

```
PWA → POST /api/records
  { transaction_id, audio, timestamp, gps_lat, gps_lon }
 │
 ├── 1. Auth JWT → 2. advisor ACTIVE → 3. idempotencia por transaction_id
 ├── 4. Audio a OSS → 5. Transcribir (Qwen-Audio)
 ├── 6. Extraer ExtractedFields (Qwen Instruct + Pydantic)
 │      El LLM clasifica record_type por el contenido (en español):
 │        "no tratar / bajo umbral / revisión"      → OBSERVATION
 │        "prescribo / recomiendo / hay que tratar" → PRESCRIPTION
 │        "hemos aplicado / tratado esta mañana"    → EXECUTION
 │
 ├── 7. Lookups: plot (JOIN holding) · product · equipment · operator
 │      → autocompletar previous_alternatives con las OBSERVATIONs de esa
 │        plot de los últimos 60 días si el audio no las menciona
 │      → MissingFieldError / PlotNotFoundError / EquipmentNotFoundError
 │        → HTTP 422/404 con "mensaje" EN ESPAÑOL para el asesor
 │
 ├── 8. SEGÚN record_type:
 │   ┌─ OBSERVATION ──────────────────────────────────────────────────────┐
 │   │ Sin validación legal de producto. INSERT lifecycle=OBSERVATION.    │
 │   │ → "👁️ Observación registrada en Finca de Pepe"                     │
 │   └────────────────────────────────────────────────────────────────────┘
 │   ┌─ PRESCRIPTION ─────────────────────────────────────────────────────┐
 │   │ Legal: authorized · dose ≤ max_allowed_dose ·                      │
 │   │ treated_area ≤ enclosure_area · iteaf_warning si caducada.         │
 │   │ INSERT lifecycle=PRESCRIBED (prescribed_dose, planned_date).       │
 │   │ PDF de prescripción (en español) → OSS → pdf_url.                  │
 │   │ SIN clima todavía (no se sabe cuándo se tratará).                  │
 │   └────────────────────────────────────────────────────────────────────┘
 │   ┌─ EXECUTION (directa: ya se trató) ─────────────────────────────────┐
 │   │ Validación legal completa + INSERT lifecycle=EXECUTED con          │
 │   │ treatment_date = timestamp del audio + clima AEMET +               │
 │   │ earliest_harvest_date = treatment_date + PHI del producto.         │
 │   └────────────────────────────────────────────────────────────────────┘
 └── 9. Responder con lifecycle_state y pdf_url si aplica
```

### FLUJO B — Confirmar ejecución (`execution_service.py`)

```
PWA → PATCH /api/interventions/{id}/execution
  { treatment_date, applied_dose?, treated_area_ha?,
    operator_name?, operator_ropo?, spray_volume_l_ha? }   // null = defaults
 │
 ├── validate_transition('PRESCRIBED' → 'EXECUTED')
 ├── Revalidar legalidad con los datos REALES
 ├── Clima AEMET para la FECHA REAL (histórico si pasada) + gps/centroide
 │   → si falla: audit_state = WEATHER_PENDING, worker reintenta
 ├── earliest_harvest_date = treatment_date + pre_harvest_interval_days
 ├── iteaf_warning = (iteaf_inspection_date caducada)
 └── UPDATE → EXECUTED. "✅ Ejecución registrada. No cosechar antes del 26/06."
```

### FLUJO C — Validación de campaña (`validation_service.py`)

```
PWA → POST /api/holdings/{id}/validations
  { campaign: "2026", type: "MID_CYCLE"|"FINAL",
    conformity: true|false, remarks: "..." }
 │
 ├── Verificar que el asesor gestiona ese holding (JWT)
 ├── UNIQUE (holding, campaign, type) · conformity=false → remarks obligatorio
 ├── Recopilar las interventions del periodo (desde la validación anterior
 │   o inicio de campaña, hasta hoy)
 ├── PDF DE VALIDACIÓN (en español):
 │     · Encabezado: titular, NIF, REA/REGEPA + campaña + periodo
 │     · Tabla: fecha · plot SIGPAC · plaga · producto (nº reg.) · dosis ·
 │       superficie · aplicador (carné) · equipo (ROMA) · estado
 │     · "El asesor abajo firmante manifiesta su CONFORMIDAD [/ NO
 │       CONFORMIDAD] con las intervenciones reflejadas..."
 │     · Firma: nombre, DNI y nº ROPO + fecha
 └── OSS + INSERT → "📋 Validación intermedia de la campaña 2026 firmada.
     Queda pendiente la validación final al cierre del ciclo."
```

---

## 7. Endpoints — los 7 del MVP

```
POST   /api/records                            ← FLUJO A: audio → obs/presc/ejec
PATCH  /api/interventions/{id}/execution       ← FLUJO B: confirmar ejecución
PATCH  /api/interventions/{id}/effectiveness   ← Fase 4: eficacia + albarán
POST   /api/holdings/{id}/validations          ← FLUJO C: validar campaña
GET    /api/interventions?state=&holding=      ← lista con filtros
GET    /api/plots                              ← agrupadas por holding
GET    /api/holdings                           ← con contador validaciones (0/2..2/2)
```

Errores: `{"error": "DOSE_ERROR", "mensaje": "La dosis 2.5 L/ha supera el
máximo legal de 1.5 L/ha"}` — código en inglés, mensaje en español.

---

## 8. PWA — 5 pantallas (UI en español)

**1 · Login.jsx** — magic link Supabase.

**2 · Home.jsx** — un solo botón GRABAR (el LLM clasifica); lista del día con
estados (👁️ observación · 📋 prescrita · ✅ ejecutada · ⛔ error) y bloque
**PENDIENTES**: prescripciones sin confirmar, ejecutadas sin valorar,
validaciones de campaña incompletas. Offline: `useOfflineQueue` (IndexedDB)
persiste audio + `transaction_id` y reenvía al reconectar.

**3 · Plots.jsx** — solo lectura, agrupado por explotación (titular, NIF, REA).

**4 · InterventionDetail.jsx** — según estado:
PRESCRIBED → botón [✅ Confirmar ejecución] (fecha=hoy, todo prellenado) + PDF;
EXECUTED → eficacia [Buena/Regular/Mala] + nº albarán + fecha mínima de
cosecha destacada + aviso ITEAF; ASSESSED/OBSERVATION → solo lectura.

**5 · Validation.jsx** — por explotación: validaciones 1/2, listado de
actuaciones del periodo, [Conforme / No conforme] + observaciones +
[🖊️ FIRMAR VALIDACIÓN].

---

## 9. Qué viene de cada origen

```
🎙️ VOZ (en español — el prompt few-shot vive en prompts/extraction_v1.md)
├── record_type (clasificado) · plot_alias → lookup SIGPAC+holding
├── product → lookup nº registro + max_dose + PHI · dose · target_pest
├── equipment → ROMA + ITEAF · treated_area (opc.) · justification (opc.)
└── operator (opc. → default del holding)

📱 PWA: transaction_id (crypto.randomUUID) · timestamp · gps · JWT
⚙️ SISTEMA: holding_id (lookup) · previous_alternatives (observations ≤60d)
            · earliest_harvest_date · iteaf_warning · prompt_version
🌦️ AEMET: al CONFIRMAR EJECUCIÓN, para la fecha real (histórico si diferida)
✋ DESPUÉS: confirmación (F3) · eficacia+albarán (F4) · validaciones ×2 (F5)
🖥️ DASHBOARD: altas de holdings (+operator defecto), plots, equipment (+ITEAF)
```

---

## 10. Decisiones de diseño

**Implementar (sin cambios de fondo respecto a v3):** máquina de estados con
`StateTransitionError` · un botón de grabar y el LLM clasifica (duda → 
PRESCRIPTION, el estado más reversible) · clima en la ejecución, no en la
prescripción · observaciones como seguro documental del asesor · validación
de campaña con UNIQUE(holding, campaign, type) · ejecución directa permitida ·
idempotencia por `transaction_id` · timestamp del dispositivo · cadena
advisors→holdings→plots · operator siempre registrado · area ≤ enclosure ·
soft-deletes · UTC en BD, Europe/Madrid en PDF · magic link · AEMET por GPS
con fallback a centroide y WEATHER_PENDING · Pydantic V2 con `= None`.

**Convención de idiomas (nueva en v3.1):** código/BD/commits en inglés;
acrónimos regulatorios intactos; UI, mensajes de error al usuario, PDFs y
prompts few-shot en español.

**No implementar todavía:** Fase 0 (contrato + descripción) → post-MVP nº1 ·
export SIEX/SgaCex → post-MVP nº2 · RLS/RBAC · Celery · caché vademécum ·
structlog · migraciones · suite de tests completa · panel cooperativa ·
validación GPS-en-parcela · push de fecha de cosecha.

---

## 11. Datos de prueba

```sql
INSERT INTO advisors (full_name, dni, ropo_number, account_status)
VALUES ('Pedro García', '12345678A', 'ROPO-30-00001', 'ACTIVE');

INSERT INTO holdings (advisor_id, owner_name, owner_nif, rea_regepa_number,
    default_operator_name, default_operator_ropo)
VALUES ('<ADVISOR_ID>', 'Pepe Martínez', '87654321Z', 'REA-30-12345',
        'Pepe Martínez', 'ROPO-30-A-55555');

INSERT INTO plots (holding_id, voice_alias, crop, variety, enclosure_area_ha,
    sigpac_province, sigpac_municipality, sigpac_polygon, sigpac_parcel,
    sigpac_enclosure, lat, lon)
VALUES ('<HOLDING_ID>', 'Finca de Pepe', 'Limonero', 'Fino', 3.50,
        '30','015','012','00045','00002', 37.983800, -1.128500);

INSERT INTO equipment (holding_id, equipment_alias, equipment_type,
    roma_number, iteaf_inspection_date)
VALUES ('<HOLDING_ID>', 'tractor', 'TRACTOR', 'ROMA-30-00001', '2025-03-10');

INSERT INTO products (registration_number, trade_name, active_substance,
    authorized, max_allowed_dose, dose_unit, pre_harvest_interval_days)
VALUES
  ('ES-00001', 'Abamectina',  'abamectina',  TRUE,  1.5, 'L/ha', 14),
  ('ES-00002', 'Clorpirifos', 'clorpirifos', FALSE, 2.0, 'L/ha', NULL);
```

Audios de demo (en español, uno por flujo): los 4 de la v3 sin cambios
(observación · prescripción · ejecución directa · error de producto).

---

## 12. Plan por hitos (= checklist del CLAUDE.md, fuente de verdad)

```
M1 · SPIKE (2-3 días, desechable — spike/main.py, un archivo, sin arquitectura)
     Audio entra → ExtractedFields impreso en consola.
     Valida LA hipótesis: ¿entiende Qwen a un asesor murciano?
     Entregable extra: prompts/extraction_v1.md con 6 ejemplos few-shot
     y sus JSON esperados (futuros casos de test).

M2 · Repo real con esqueleto hexagonal (carpetas completas, ABCs bajo demanda).
     JSON → Supabase: advisors, holdings, plots, products, equipment,
     interventions (sin clima, sin estados avanzados). POST /api/records.

M3 · PDF de prescripción (ReportLab, plantilla en español) + OSS + pdf_url.

M4 · PWA mínima: Login + Home (grabar + lista del día). Offline queue.

M5 · Máquina de estados completa + FLUJO B (confirmar ejecución) +
     AEMET (lat/lon + histórico) + earliest_harvest_date + iteaf_warning.

M6 · Eficacia + delivery_note_number (Fase 4) + InterventionDetail completo.

M7 · Validaciones de campaña (tabla + FLUJO C + Validation.jsx + PDF firmado).

HACKATHON (cuando toque): congela el hito en curso 5 días antes →
     set de demo (1 asesor, 2 holdings) · vídeo 3 min (observación →
     prescripción con bloqueo de dosis → confirmación con fecha de cosecha →
     validación firmada) · README en inglés · despliegue Alibaba ECS ·
     repo público.
```

---

## 13. Fuentes oficiales

Las de v2/v3 sin cambios: BOE (RD 1311/2012, RD 1054/2022, RD 34/2025,
RD 1039/2025, RD 9/2015, RD 1702/2011), Reglamentos UE 2023/564 y 2025/2203,
documento MAPA de asesoramiento GIP, vademécum MAPA (incluye PHI por uso),
visor SIGPAC, FEGA/SIEX/SgaCex, guías GIP por cultivo, AEMET OpenData.

---

## Apéndice — Qué problema resolvemos (sin cambios respecto a v3)

El asesor GIP medio lleva 30-60 explotaciones: lunes-jueves de campo,
viernes reconstruyendo de memoria. El MVP convierte sus 4-6 horas
administrativas semanales en ~10 minutos de voz: (1) su vigilancia invisible
se vuelve defendible, (2) sus números legales no pueden estar mal, (3) sus
2 validaciones por ciclo se firman con un botón, y (4) cuando el CUE
electrónico sea obligatorio (1/1/2027), el export a SIEX es una
transformación, no una migración.


## ACT TABLAS
-- ╔══════════════════════════════════════════════════════════════════╗
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
