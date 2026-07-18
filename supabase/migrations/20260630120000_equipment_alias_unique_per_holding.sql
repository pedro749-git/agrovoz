-- Equipment alias: UNIQUE PER HOLDING (not per advisor). The voice lookup
-- resolves equipment within the dictated plot's holding, so two holdings may
-- each have their own "tractor" — but two "tractor" in the SAME holding would
-- be indistinguishable to the voice match.
--
-- Partial unique index:
--   · lower(equipment_alias): "Tractor" and "tractor" count as the same,
--     matching the fuzzy lookup (which normalizes to lowercase).
--   · WHERE deleted_at IS NULL: soft-delete (hard rule 1) — a deleted machine
--     does not block registering another one with the same alias.
CREATE UNIQUE INDEX equipment_alias_unique_per_holding
    ON equipment (holding_id, lower(equipment_alias))
    WHERE deleted_at IS NULL;
