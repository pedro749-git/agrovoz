# extraction_v2

Prompt de extracción de campos para Qwen Instruct. La transcripción de entrada
es lo que dicta un asesor GIP en campo (español de campo, coloquial). La salida
es JSON estricto que el backend valida contra `ExtractedFields` (Pydantic).

Cambios sobre v1: vocabulario canónico de unidades de dosis + prohibición
explícita de convertir magnitudes (la conversión es del backend, no del modelo).

Reglas para el modelo:

- Devuelve SOLO un objeto JSON, sin markdown ni texto alrededor.
- Si un campo no aparece en el audio, devuelve `null` (NUNCA inventes valores).
- `record_type` lo decides tú clasificando el audio:
  - `OBSERVATION`: el asesor solo describe lo que ve (capturas, umbral, estado),
    no indica tratamiento. No lleva producto ni dosis.
  - `PRESCRIPTION`: el asesor indica qué aplicar (producto + dosis + plaga),
    normalmente a futuro ("hay que aplicar", "que echen").
  - `EXECUTION`: el tratamiento YA se ha hecho ("hemos aplicado", "se ha echado").
- `plot_alias` es OBLIGATORIO siempre: el nombre de la finca/parcela tal cual lo
  dice el asesor ("Finca de Pepe", "la parcela de arriba").
- `dose` es solo el número (1.5), y `dose_unit` la unidad en forma compacta.
  Unidades canónicas: "L/ha", "Kg/ha", "ml/ha", "g/ha", "hl/ha", "cc/hl", "g/hl".
  - Escribe la unidad dictada en su forma compacta: "litros por hectárea" →
    "L/ha", "medio hectolitro por hectárea" → "hl/ha".
  - NUNCA conviertas la magnitud: el número se transcribe tal como se dictó
    ("medio hectolitro por hectárea" → dose 0.5 y dose_unit "hl/ha";
    NUNCA dose 50 y "L/ha").
  - Si la unidad dictada no está en la lista, escríbela literal tal como se
    oyó ("litros por árbol" → "litros por árbol"); no la aproximes a otra.

Esquema de salida:

```json
{
  "record_type": "OBSERVATION | PRESCRIPTION | EXECUTION",
  "plot_alias": "string",
  "product_name": "string | null",
  "dose": "number | null",
  "dose_unit": "string | null",
  "target_pest": "string | null",
  "equipment_alias": "string | null",
  "observation": "string | null",
  "spray_volume_l_ha": "number | null",
  "treated_area_ha": "number | null",
  "justification": "string | null",
  "previous_alternatives": "string | null",
  "operator_name": "string | null",
  "operator_ropo": "string | null",
  "planned_date": "string | null"
}
```

## Ejemplos

Input: "Finca de Pepe, hay que aplicar Abamectina a uno con cinco litros por
hectárea contra araña roja con el tractor"
Output: {"record_type":"PRESCRIPTION","plot_alias":"Finca de Pepe","product_name":"Abamectina","dose":1.5,"dose_unit":"L/ha","target_pest":"araña roja","equipment_alias":"tractor","observation":null,"spray_volume_l_ha":null,"treated_area_ha":null,"justification":null,"previous_alternatives":null,"operator_name":null,"operator_ropo":null,"planned_date":null}

Input: "En la parcela norte he contado tres capturas en la trampa, está por
debajo del umbral, de momento no hace falta tratar"
Output: {"record_type":"OBSERVATION","plot_alias":"parcela norte","product_name":null,"dose":null,"dose_unit":null,"target_pest":null,"equipment_alias":null,"observation":"3 capturas en trampa, por debajo del umbral, no requiere tratamiento","spray_volume_l_ha":null,"treated_area_ha":null,"justification":null,"previous_alternatives":null,"operator_name":null,"operator_ropo":null,"planned_date":null}

Input: "En la finca grande hemos echado esta mañana Clorpirifos dos kilos por
hectárea contra trips, dos hectáreas tratadas con el atomizador, lo aplicó Juan"
Output: {"record_type":"EXECUTION","plot_alias":"finca grande","product_name":"Clorpirifos","dose":2,"dose_unit":"Kg/ha","target_pest":"trips","equipment_alias":"atomizador","observation":null,"spray_volume_l_ha":null,"treated_area_ha":2,"justification":null,"previous_alternatives":null,"operator_name":"Juan","operator_ropo":null,"planned_date":null}

Input: "Parcela del río, prescribo medio hectolitro por hectárea de Aceite de
parafina para cochinilla, con el atomizador"
Output: {"record_type":"PRESCRIPTION","plot_alias":"parcela del río","product_name":"Aceite de parafina","dose":0.5,"dose_unit":"hl/ha","target_pest":"cochinilla","equipment_alias":"atomizador","observation":null,"spray_volume_l_ha":null,"treated_area_ha":null,"justification":null,"previous_alternatives":null,"operator_name":null,"operator_ropo":null,"planned_date":null}
