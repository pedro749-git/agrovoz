-- ═══════════════════════════════════════════════════
-- Alias de equipo: ÚNICO POR FINCA (no por asesor)
-- ───────────────────────────────────────────────────
-- La búsqueda por voz resuelve el equipo dentro del holding de la
-- parcela dictada, así que dos fincas pueden tener cada una su
-- "tractor" sin problema. Lo que NO debe existir es dos "tractor"
-- en la MISMA finca: ahí el match por voz no podría distinguirlos.
--
-- Índice ÚNICO PARCIAL:
--   · lower(equipment_alias): "Tractor" y "tractor" cuentan igual,
--     como hace el match difuso (normaliza a minúsculas).
--   · WHERE deleted_at IS NULL: soft-delete (regla 1) — un equipo
--     borrado no bloquea dar de alta otro con el mismo alias.
-- ═══════════════════════════════════════════════════
CREATE UNIQUE INDEX equipment_alias_unique_per_holding
    ON equipment (holding_id, lower(equipment_alias))
    WHERE deleted_at IS NULL;
