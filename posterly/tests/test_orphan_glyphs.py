"""Polish Gate B: orphan glyph detection logic. The full Playwright
roundtrip is integration territory; here we cover the constant table
and the trailing-glyph regex behaviour the JS / Python combo relies on."""
from __future__ import annotations

from _posterly import polish


def test_orphan_glyphs_includes_common_offenders() -> None:
    for ch in "↑↓×":  # the prior-session failure cases
        assert ch in polish.ORPHAN_GLYPHS, (
            f"{ch!r} dropped from ORPHAN_GLYPHS; the original "
            "co-consideration-arrow regression would slip through."
        )


def test_orphan_glyphs_includes_footnote_markers() -> None:
    for ch in "*§†‡":
        assert ch in polish.ORPHAN_GLYPHS
