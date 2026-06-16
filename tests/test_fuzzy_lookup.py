"""Fuzzy lookup tests — the ASR mis-hears proper nouns.

Pure function, no env/DB needed. Run with:

    uv run python tests/test_fuzzy_lookup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.outbound._fuzzy import best_match, normalize


def main():
    # Accent/case normalization
    assert normalize("Finca de Pepé") == "finca de pepe"
    print("1 normalize ok")

    # "amavectina" (mis-heard) -> the real product "Abamectina"
    products = [{"trade_name": "Abamectina"}, {"trade_name": "Clorpirifos"}]
    assert best_match("amavectina", products, "trade_name")["trade_name"] == "Abamectina"
    print("2 product fuzzy ok")

    # "Finca de PP" -> "Finca de Pepe"
    plots = [{"voice_alias": "Finca de Pepe"}, {"voice_alias": "Parcela Norte"}]
    assert best_match("finca de pp", plots, "voice_alias")["voice_alias"] == "Finca de Pepe"
    print("3 plot fuzzy ok")

    # Nothing close enough -> None (the advisor gets told, we don't guess)
    assert best_match("zzzzzzzz", products, "trade_name") is None
    print("4 below-threshold -> None ok")

    # Ambiguous: two candidates equally close -> refuse to guess
    ambiguous = [{"n": "pato"}, {"n": "rato"}]
    assert best_match("gato", ambiguous, "n") is None
    print("5 ambiguity guard -> None ok")

    print("ALL FUZZY TESTS PASSED")


if __name__ == "__main__":
    main()
