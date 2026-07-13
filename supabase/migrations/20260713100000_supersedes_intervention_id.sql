-- M8.2 — correction by supersede (hard rules 1/7): a correction NEVER edits a
-- legal record in place; it inserts a replacement row and soft-deletes the old
-- one. This column is the link that makes that distinguishable in the data from
-- a plain deletion: the replacement points at the record it corrects, so an
-- audit can follow the correction chain. NULL for every record that is not a
-- correction. Not in the official Anexo III checklist — it is a need of the
-- correction pipeline (see docs/decisions.md 2026-07-13).
ALTER TABLE interventions
    ADD COLUMN supersedes_intervention_id UUID REFERENCES interventions(id);
