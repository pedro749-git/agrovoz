FUNCIONALIDAD — USUARIO (Técnico / Asesor GIP)
1. ALTA (onboarding)
PASO 1 — TÚ validas al técnico (fuera del sistema)
├── El técnico te contacta y te da su DNI, nº ROPO y email
├── Entras en la consulta pública del ROPO del MAPA
│   → mapa.gob.es/.../productos-fitosanitarios/ropo
├── Metes su DNI y compruebas:
│   ├── Que está ACTIVO
│   └── Que tiene categoría "Asesor" (no vale "Básico")
└── Si todo cuadra, procedes al alta

PASO 2 — TÚ creas el perfil en Supabase (tabla advisors)
└── INSERT con account_status = 'ACTIVE' y email, sin auth_user_id todavía

PASO 3 — TÚ creas su explotación, parcelas y maquinaria
├── INSERT en holdings (titular, NIF, nº REA/REGEPA, aplicador por defecto)
├── INSERT de cada parcela en plots (SIGPAC + voice_alias + centroide lat/lon)
└── INSERT de cada máquina en equipment (num_roma + equipment_alias)
    (El técnico nunca teclea esto. Tú lo configuras.)

PASO 4 — EL TÉCNICO inicia sesión en la PWA  →  PANTALLA 1 (LOGIN)
(No hay autorregistro: tú le das de alta en auth.users; el login usa
 shouldCreateUser:false, así que solo entran emails ya registrados.)
├── Abre la PWA, mete su email
├── Supabase le manda un código de acceso (6 dígitos) al email
├── Introduce el código → entra con su auth_user_id ya existente
└── Tiene un auth_user_id, pero aún no está vinculado a su perfil

PASO 5 — VINCULAR las dos capas (automático)
├── El backend busca su perfil por email
├── Si existe: vincula auth_user_id con su fila en advisors
└── Si no existe: HTTP 403 "No tienes perfil. Contacta con el administrador."
2. ACCESO (login en cada sesión) → PANTALLA 1
├── El técnico abre la PWA
├── Si tiene sesión guardada → entra directo a HOME (Pantalla 2)
└── Si no tiene sesión:
    ├── Mete su email
    ├── Recibe un código de acceso de Supabase
    ├── Introduce el código → entra
    └── La sesión persiste para futuras aperturas
Método principal: código al email (el "usuario" es el email). Opcionalmente el
técnico puede fijar una contraseña en Ajustes y entrar con email + contraseña.
3. REGISTRAR UNA INTERVENCIÓN (la función principal) → PANTALLA 2 (HOME)
Esto es el 90% de lo que hace el usuario. La novedad clave de la nueva interfaz: el mismo botón sirve para los dos tipos de registro de campo, y el sistema decide cuál es según el contenido del audio.
ESTANDO EN EL CAMPO:
│
├── 1. Abre la PWA → pantalla HOME
│
├── 2. Pulsa el botón grande 🎙️ REGISTRAR
│      (o escribe en la barra inferior si no puede hablar)
│
├── 3. Dicta una nota de voz natural. Dos casos posibles:
│
│   CASO A — OBSERVACIÓN (vigilancia, sin producto)
│   "Finca Antonio, araña roja, tres capturas, bajo umbral, no tratar"
│      → El sistema NO detecta producto → lifecycle_state = OBSERVATION
│      → No genera PDF. Documenta la vigilancia GIP.
│
│   CASO B — PRESCRIPCIÓN (con producto)
│   "Parcela Pepe, Abamectina 1.5 litros por hectárea, araña roja,
│    atomizador, umbral superado, puse trampas sin éxito"
│      → El sistema detecta producto → lifecycle_state = PRESCRIBED
│      → Valida legalidad + genera PDF de prescripción
│
├── 4. Pulsa ⏹ PARAR
│
└── 5. Según haya conexión:
       │
       ├── CON INTERNET (~10 segundos):
       │   ├── ✅ VÁLIDO → aparece en el historial + (si prescripción) link al PDF
       │   ├── 👁 OBSERVACIÓN → registrada como vigilancia, badge azul
       │   ├── ⛔ DOSE_ERROR → "Dosis 2.5 supera máximo legal 1.5"
       │   ├── ⛔ PRODUCT_ERROR → "Abamectina no autorizado"
       │   ├── ⛔ AREA_ERROR → "Superficie tratada mayor que el recinto"
       │   ├── ⛔ PARCELA_NO_ENCONTRADA → "Parcela Pepe no registrada"
       │   └── ⏳ WEATHER_PENDING → "Registrado, falta el clima (reintentando)"
       │
       └── SIN INTERNET:
           ├── El audio se guarda en IndexedDB (local en el móvil)
           ├── Mensaje: "📥 Guardado. Se enviará al reconectar."
           └── Al volver la cobertura → se envía solo, en orden cronológico
Lo importante: la fecha de la intervención es la del momento en que grabó (prescription_date = timestamp del dispositivo), no la del envío. Aunque dicte sin cobertura y el audio llegue 2 horas después, el registro refleja la hora real.
4. CONFIRMAR LA EJECUCIÓN (nuevo — Fase 3) → desde DETALLE PRESCRIPCIÓN (Pantalla 6)
Una prescripción no es un tratamiento ejecutado. El producto se aplica después, y eso hay que confirmarlo. Esta fase no existía en la versión anterior.
CUANDO EL TRATAMIENTO YA SE HA APLICADO:
│
├── El técnico abre la prescripción → Pantalla 6
├── En la sección "Ejecución" pulsa [Confirmar ejecución]
├── Confirma:
│   ├── ✅ "Igual a la prescripción" (un toque, hereda todos los datos)
│   └── ✏️ "Hubo cambios" → audio corto de 10 seg:
│         fecha real, dosis real, aplicador real (con su carné/ROPO)
│
└── El sistema:
    ├── Pasa lifecycle_state de PRESCRIBED → EXECUTED
    ├── Pide a AEMET el clima de la FECHA REAL de aplicación (no la prevista)
    ├── Calcula earliest_harvest_date = fecha real + PHI (plazo de seguridad)
    └── Avisa si la inspección ITEAF de la máquina está caducada
El resultado es la anotación válida para el CUE/SIEX.
5. VER SUS INTERVENCIONES → PANTALLA 4 (HISTORIAL)
EN EL HISTORIAL:
├── Lista cronológica de todas sus intervenciones
├── Cada fila tiene DOS señales visuales:
│   ├── ICONO = qué tipo es:
│   │   👁 Observación · 📄 Prescripción · ✅ Ejecución · ★ Validación
│   └── BADGE = cómo está:
│       Válido (verde) · Fallido (rojo) · Sin clima (ámbar) · Vigilancia (azul)
├── Buscador para filtrar
└── Toca cualquier fila → abre su pantalla de detalle
El técnico solo ve sus propias intervenciones (en el MVP por lógica de backend + RLS de Supabase ya activo).
6. VER EL DETALLE DE CADA INTERVENCIÓN → PANTALLAS 5, 6, 7
Una sola plantilla que muestra secciones distintas según el lifecycle_state:
DETALLE OBSERVACIÓN (Pantalla 5) — estado OBSERVATION
├── Plaga vigilada + nota dictada (cita textual)
├── Audio original reproducible
├── Clima de AEMET del momento
└── Aviso: "Quedará como antecedente si esta parcela requiere tratamiento"
    (NO tiene PDF ni dosis — no es un documento legal)

DETALLE PRESCRIPCIÓN (Pantalla 6) — estado PRESCRIBED
├── Producto, nº registro MAPA, dosis, plaga, superficie, fecha prevista
├── Justificación GIP + alternativas previas (heredadas de observaciones)
├── [Ver PDF de prescripción] + [Enviar al agricultor]
└── Zona "Ejecución" → [Confirmar ejecución]

DETALLE EJECUCIÓN (Pantalla 7) — estado EXECUTED / ASSESSED
├── Aplicación real (dosis, caldo, superficie, maquinaria, aplicador)
├── 🌾 Fecha mínima de cosecha (calculada por PHI)
├── Clima de la fecha REAL de aplicación
├── Valoración de eficacia (ver punto 8)
└── [Ver justificante de aplicación]
7. DESCARGAR / REENVIAR EL PDF DE PRESCRIPCIÓN → desde PANTALLA 6
├── Solo las prescripciones generan PDF (las observaciones no)
├── El técnico lo abre desde el detalle de la prescripción
└── Lo reenvía al agricultor (WhatsApp, email, imprimir)
Es el documento legal que el agricultor necesita. El output que justifica todo el producto para el Cliente 1.
8. VALORAR LA EFICACIA (días después — Fase 4) → desde PANTALLA 7
DÍAS DESPUÉS, EN LA VISITA DE SEGUIMIENTO:
│
├── El técnico vuelve a la finca y comprueba el resultado
├── Abre la ejecución → Pantalla 7
├── En "Valoración del resultado":
│   ├── Pulsa: [ Buena ] [ Regular ] [ Mala ]   → effectiveness
│   └── (Opcional) Mete el nº de albarán/factura → delivery_note_number
└── Guarda → lifecycle_state pasa de EXECUTED → ASSESSED
Sin esta valoración, el registro está incompleto según el Anexo III del RD 1311/2012.
9. CONSULTAR SUS PARCELAS → PANTALLA 8 (PARCELAS)
EN LA LISTA DE PARCELAS:
├── Cada parcela: alias_voz, cultivo, variedad, superficie
├── Buscador para encontrarla rápido
├── [🗺️ Ver en el mapa] → Pantalla 9
└── Toca una parcela → su detalle (Pantalla 10)
10. VER EL MAPA (nuevo) → PANTALLA 9 (MAPA)
├── Su ubicación GPS actual (punto rojo)
├── Los recintos SIGPAC de sus parcelas dibujados sobre el mapa
├── Buscador de parcela
└── Toca un recinto → detalle de esa parcela
Le sirve para orientarse en el campo y confirmar que está en la finca correcta.
11. VER EL DETALLE DE UNA PARCELA (nuevo) → PANTALLA 10
├── Datos: SIGPAC, titular, explotación (REA)
├── CAMPAÑAS de esa parcela (cada una con su estado de validación)
├── Intervenciones recientes de la parcela (todas las fases)
└── Botón [🎙️ Registrar aquí] → graba con la parcela ya preseleccionada
12. VALIDAR LA CAMPAÑA (nuevo — Fase 5, OBLIGATORIO) → PANTALLA 11
La obligación legal del asesor que antes no estaba contemplada. Mínimo dos validaciones por ciclo.
EN EL DETALLE DE CAMPAÑA:
├── Recuento: nº intervenciones, prescripciones, observaciones
├── Las dos validaciones del ciclo:
  │──── Intermedia (durante el cultivo)
       ├── ✅ CONFORME → conformity = true
       └── ⚠️ NO CONFORME → conformity = false + remarks OBLIGATORIO
         (debe explicar qué no está bien)
   └── Final (al cerrar la campaña)
      ├── ✅ CONFORME → conformity = true
       └── ⚠️ NO CONFORME → conformity = false + remarks OBLIGATORIO
         (debe explicar qué no está bien)
├── Aviso si falta alguna validación obligatoria
└── [★ Validar y firmar campaña]
    → Genera PDF con el listado de actuaciones del periodo
      + declaración de conformidad + firma (nombre + ROPO)
Lo que el usuario NO puede hacer (en el MVP)
❌ Dar de alta parcelas, maquinaria o explotaciones
   → Lo haces tú en Supabase. Garantiza SIGPAC, ROMA y REA correctos.

❌ Editar sus datos profesionales (DNI, ROPO)
   → Datos legales validados. Cambiarlos requiere re-validación.

❌ Borrar intervenciones
   → Registros legales. Solo soft delete (deleted_at), nunca desde la PWA.

❌ Ver intervenciones de otros técnicos
   → Cada asesor aislado por RLS (política current_advisor_id ya activa).

❌ Exportar el JSON masivo al Gobierno
   → Función del administrador de cooperativa (Cliente 2), no del asesor.

❌ Auto-registrarse sin validación
   → Tener email válido no basta. Tú validas el ROPO antes del alta.
Mapa resumen de toda la funcionalidad
USUARIO (Técnico / Asesor GIP)
│
├── ALTA  →  Pantalla 1
│   └── Semi-manual: tú validas ROPO + creas perfil/parcelas, él conecta email
│
├── ACCESO  →  Pantalla 1
│   └── Código al email (o contraseña opcional fijada en Ajustes), sesión persistente
│
├── REGISTRAR INTERVENCIÓN  ←  función principal  →  Pantalla 2
│   ├── 👁 Observación (vigilancia, sin producto, sin PDF)
│   └── 📄 Prescripción (con producto, validación legal, genera PDF)
│
├── CONFIRMAR EJECUCIÓN  →  Pantalla 6 → 7
│   └── Pasa prescripción a ejecutada + clima real + fecha de cosecha (PHI)
│
├── VER HISTORIAL  →  Pantalla 4
│   └── Icono = tipo · Badge = estado
│
├── VER DETALLE  →  Pantallas 5 / 6 / 7
│   └── Misma plantilla, secciones según lifecycle_state
│
├── DESCARGAR PDF  →  Pantalla 6
│   └── Reenviar prescripción al agricultor
│
├── VALORAR EFICACIA  →  Pantalla 7
│   └── Días después: Buena/Regular/Mala + nº albarán → estado ASSESSED
│
├── CONSULTAR PARCELAS  →  Pantalla 8
│   ├── Lista (solo lectura)
│   ├── Mapa con recintos SIGPAC  →  Pantalla 9
│   └── Detalle parcela + campañas  →  Pantalla 10
│
└── VALIDAR CAMPAÑA  ←  obligatorio legal  →  Pantalla 11
    └── Mín. 2 por ciclo: intermedia + final, con PDF firmado


TIPOS DE PDF
Documento A — PDF de Prescripción (Registro de Actuaciones Fitosanitarias)
QUIÉN LO GENERA:  el asesor, al dictar una prescripción
PARA QUIÉN:       el AGRICULTOR (se lo reenvía)
BASE LEGAL:       Anexo III Parte I, RD 1311/2012
CAMPOS:
├── prescription_number          (nº receta legible)
├── advisors.full_name + dni + ropo_number     (firma del asesor)
├── plots.sigpac_* + crop + variety            (parcela y cultivo)
├── enclosure_area_ha                          (superficie)
├── target_pest                                (plaga)
├── justification                              (motivo GIP)
├── previous_alternatives                      (vigilancia previa)
├── products.trade_name + registration_number  (producto)
├── prescribed_dose + dose_unit                (dosis)
├── planned_date                               (fecha prevista)
└── products.pre_harvest_interval_days         (plazo de seguridad)
Documento B — Anotación CUE/SIEX (registro de la ejecución)
QUIÉN LO GENERA:  el sistema, al confirmar ejecución
PARA QUIÉN:       el GOBIERNO (Ministerio vía SIEX/FEGA) — en Cliente 1 se prepara, no se vuelca aún
BASE LEGAL:       Anexo III Parte II + Reglamento UE 2023/564
CAMPOS:
├── plots.sigpac_* + crop + variety            (dónde y qué cultivo)
├── treated_area_ha                            (superficie tratada)
├── treatment_date                             (fecha REAL de aplicación)
├── products.trade_name + active_substance     (producto + materia activa)
├── products.registration_number              (nº registro MAPA)
├── applied_dose + dose_unit                   (dosis real)
├── target_pest                                (plaga)
├── justification                              (justificación)
├── operator_name + operator_ropo              (aplicador + carné)
├── equipment.equipment_type + roma_number     (maquinaria + ROMA)
├── temperature_c / humidity / wind_*          (condiciones meteo)
├── delivery_note_number                       (nº albarán)
└── exported_at                                ⚠️ (control plazo 1 mes — a añadir)
Documento C — PDF de Validación de Campaña
QUIÉN LO GENERA:  el asesor, al validar (intermedia o final)
PARA QUIÉN:       expediente legal (lo conserva el asesor, disponible para inspección)
BASE LEGAL:       instrucciones oficiales doc. MAPA (mín. 2 validaciones/ciclo)
CAMPOS:
├── advisors.full_name + ropo_number           (firma)
├── holdings.owner_name + rea_regepa_number     (explotación)
├── validations.campaign + type                (qué campaña, intermedia/final)
├── validations.period_start / period_end       (periodo cubierto)
├── validations.conformity + remarks           (conforme o no + motivo)
├── validations.intervention_count             (nº actuaciones)
└── listado de cada intervención del periodo    ← interventions WHERE campaign = X
                                                   ⚠️ requiere el campo campaign
