"""Fuzzy lookup tests — the ASR mis-hears proper nouns.

Pure function, no env/DB needed. Run: uv run pytest tests/test_fuzzy_lookup.py
"""

from app.adapters.outbound._fuzzy import best_match, normalize


def test_normalize_strips_accents_and_case():
    assert normalize("Finca de Pepé") == "finca de pepe"


def test_mis_heard_product_matches_real_row():
    # "amavectina" (mis-heard) -> the real product "Abamectina"
    products = [{"trade_name": "Abamectina"}, {"trade_name": "Clorpirifos"}]
    assert best_match("amavectina", products, "trade_name")["trade_name"] == "Abamectina"


def test_mis_heard_plot_matches_real_row():
    # "Finca de PP" -> "Finca de Pepe"
    plots = [{"voice_alias": "Finca de Pepe"}, {"voice_alias": "Parcela Norte"}]
    assert best_match("finca de pp", plots, "voice_alias")["voice_alias"] == "Finca de Pepe"


def test_below_threshold_returns_none():
    # Nothing close enough -> None (the advisor gets told, we never guess).
    products = [{"trade_name": "Abamectina"}, {"trade_name": "Clorpirifos"}]
    assert best_match("zzzzzzzz", products, "trade_name") is None


def test_ambiguous_match_returns_none():
    # Two candidates equally close -> refuse to guess.
    ambiguous = [{"n": "pato"}, {"n": "rato"}]
    assert best_match("gato", ambiguous, "n") is None
