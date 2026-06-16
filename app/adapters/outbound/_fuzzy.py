"""Fuzzy resolution of dictated names to catalog rows.

The ASR mis-hears proper nouns ("Abamectina" -> "amavectina", "Finca de Pepe"
-> "Finca de PP"). We match the dictated text against REAL rows only, so we can
never invent a value (hard rule 4): below the similarity threshold we return
None, and the service tells the advisor instead of guessing. If the two best
candidates are equally close (ambiguous), we also refuse to guess.

Doses/quantities are NEVER fuzzy-matched — only the *identity* (which plot /
product / equipment). M2 matches in Python over small row sets; at vademecum
scale, move product matching to a pg_trgm similarity query (DB-side, GIN index).
"""

import unicodedata
from difflib import SequenceMatcher

DEFAULT_THRESHOLD = 0.7   # below this similarity, too risky to assume a match
_AMBIGUITY_MARGIN = 0.05  # if runner-up is this close, don't guess


def normalize(text: str) -> str:
    """Lowercase + strip accents so 'Pepé' and 'pepe' compare equal."""
    stripped = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return stripped.casefold().strip()


def best_match(
    query: str,
    rows: list[dict],
    key: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict | None:
    """Return the row whose ``row[key]`` is closest to ``query``.

    Returns None when the best score is below ``threshold`` OR when the top two
    candidates are within ``_AMBIGUITY_MARGIN`` of each other (ambiguous).
    """
    query_norm = normalize(query)
    scored = sorted(
        (SequenceMatcher(None, query_norm, normalize(row[key])).ratio(), i)
        for i, row in enumerate(rows)
    )
    if not scored:
        return None
    top_score, top_i = scored[-1]
    if top_score < threshold:
        return None
    if len(scored) > 1:
        runner_up = scored[-2][0]
        if runner_up >= threshold and top_score - runner_up < _AMBIGUITY_MARGIN:
            return None
    return rows[top_i]
