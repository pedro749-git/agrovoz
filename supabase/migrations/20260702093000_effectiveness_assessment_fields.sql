-- M6 — effectiveness assessment (Phase 4): the advisor rates how well the
-- treatment worked, days after the execution, moving EXECUTED -> ASSESSED.
--
-- `effectiveness` (GOOD/FAIR/POOR) already exists. These two add the WHEN and
-- the WHY the advisor asked for: the assessment date and a short reason the
-- advisor dictates by voice (transcribed to text). Neither is in the official
-- Anexo III checklist — they document good GIP practice, kept because the
-- assessment screen needs them.
ALTER TABLE interventions
    ADD COLUMN effectiveness_date  DATE,   -- when the effectiveness was assessed
    ADD COLUMN effectiveness_notes TEXT;   -- dictated reason (why that rating)
