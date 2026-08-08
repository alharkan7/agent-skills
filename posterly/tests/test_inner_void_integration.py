"""Chromium-gated integration test for the CARD/INNER-VOID geometry inside
``polish``'s ``_POLISH_JS``.

This is the void SPACE-BETWEEN and CARD/TRAILING both miss: an equal-height
row (``grid``/``flex`` + ``align-items: stretch``) of cards with unequal
content, where the short card pins its tail with ``margin-top: auto``. The
slack opens in the MIDDLE of the card -- below the last real block, above
the pinned tail -- so the trailing-below-last reads ~0 (CARD/TRAILING stays
quiet) and the cards carry only the ``.card`` class with no
``data-measure-role`` (a feature band), so CARD/TRAILING never even scans
them. CARD/INNER-VOID is geometry-driven over every ``.card``, so it catches
both gaps the older two gates leave open.

Three adversarial cards exercise the three branches:
  * a TALL filled card (sets the row height, no slack) -> must NOT flag;
  * a SHORT card with a ``margin-top: auto`` tail (the real void) -> flag;
  * a card with a tall inline-SVG figure beside a SHORT text on one row,
    then a caption below it -> must NOT flag (the running-max row merge
    sees the tall figure fill the span; the SVG child also exercises the
    getAttribute('class') path that a naive `.className.trim()` crashes on).

A fourth card -- a normal `data-measure-role="card"` body card, naturally
filled -- is added only to satisfy polish's "needs a tagged card" guard; it
must not flag either. So 4 cards are scanned for inner voids while only that
1 tagged card is sampled by CARD/TRAILING.

Skipped when Playwright/Chromium isn't installed.
"""
from __future__ import annotations

import argparse

import pytest

from _posterly import polish as _polish


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _chromium_available(),
    reason="playwright + chromium not available",
)


# An equal-height grid row of two .card.contrib blocks (a feature band:
# .card class only, NO data-measure-role -- so CARD/TRAILING never scans
# them). `align-items: stretch` makes both as tall as the taller (A). The
# `* { margin: 0 }` reset matches the shipped templates. Card C is a flex
# row whose children sit side by side with a wide horizontal gap.
_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page { size: 24in 36in; margin: 0; }
  * { margin: 0; box-sizing: border-box; }
  body { font-family: Georgia, serif; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
         align-items: stretch; margin-bottom: 40px; }
  .card { background: #fff; border: 2px solid #888; padding: 14px;
          font-size: 18px; line-height: 1.35; }
  .card.contrib { display: flex; flex-direction: column; }
  .card.contrib p { margin-bottom: 10px; }
  .why { margin-top: auto; background: #eee; padding: 10px; }
</style></head>
<body>
  <div data-measure-role="poster">
  <div data-measure-role="column">
    <div class="row">
      <!-- card A: tall, three paragraphs -> fills its own height, sets the
           row height. `.why` follows its content with only the normal
           margin -> NO inner void. -->
      <div class="card contrib filled">
        <p>Heading block for the filled card A goes on the first line here.</p>
        <p>First content paragraph that occupies several lines of vertical
           space so that card A is clearly the taller of the two cards and
           therefore sets the stretched height of the whole row for both.</p>
        <p>Second content paragraph adding still more height to card A so the
           difference against the short card B is unambiguous and stable.</p>
        <div class="why">Why it matters: card A is filled to the bottom.</div>
      </div>
      <!-- card B: one short paragraph + margin-top:auto tail. Stretched to
           A's height, the tail is pinned to the bottom and a large void
           opens between the paragraph and the tail -> MUST flag. -->
      <div class="card contrib short">
        <p>Heading block for the short card B goes here on one line.</p>
        <p>Only one short content paragraph in card B.</p>
        <div class="why">Why it matters: card B ran short.</div>
      </div>
    </div>
    <!-- card C: a tall inline SVG figure beside a SHORT text (same row),
         then a caption block BELOW the row. Without the running-max row
         merge this false-positives (caption.top - shortText.bottom is a
         huge "gap" even though the tall figure fills that span); the SVG
         direct child would also crash a naive `.className.trim()`. So this
         single card guards BOTH fixes -> MUST NOT flag. -->
    <div class="card">
      <svg width="100" height="260" style="vertical-align:top"><rect
        width="100" height="260" fill="#ccd"></rect></svg><span
        style="display:inline-block; width:160px; height:50px;
        vertical-align:top">Short text beside the tall figure.</span>
      <div>A caption line sitting below the figure-and-text row.</div>
    </div>
    <!-- a normal tagged body card: satisfies polish's data-measure-role
         requirement and is naturally filled (no stretch) -> MUST NOT flag.
         Its presence is what makes the band's UNtagged cards the realistic
         case CARD/TRAILING cannot see. -->
    <div class="card" data-measure-role="card">
      <p>A normal body card with two paragraphs of genuine content so it
         hugs its own natural height with no stretch applied to it at all.</p>
      <p>The second paragraph reaches the card bottom, so there is neither a
         trailing blank nor a mid-card void anywhere inside this card.</p>
    </div>
  </div>
  </div>
</body></html>
"""


def _args(html) -> argparse.Namespace:
    return argparse.Namespace(
        html=str(html), canvas=None, settle_ms=200,
        mathjax_timeout_ms=5000, wide_min_ratio=0.65,
        tall_max_ratio=0.70, tall_min_ratio=0.36, square_min_ratio=0.55,
        max_space_between_fill=0.05, max_card_trailing=0.10,
        max_card_inner_void=_polish.DEFAULT_CARD_INNER_VOID,
        min_card_inner_void_px=_polish.DEFAULT_CARD_INNER_VOID_PX,
        strict=False,
    )


def test_inner_void_geometry_end_to_end(tmp_path, capsys) -> None:
    poster = tmp_path / "poster.html"
    poster.write_text(_HTML, encoding="utf-8")

    rc = _polish.cmd_polish(_args(poster))
    combined = "".join(capsys.readouterr())

    assert rc == 0                                   # warn-only, not --strict
    # All four cards with >=2 stacked children are scanned (A, B, C, and the
    # tagged body card); only the one tagged card is sampled by CARD/TRAILING.
    assert "inner-void cards    : 4" in combined
    assert "cards checked       : 1" in combined
    # Exactly one inner-void warning -- the short card B.
    assert combined.count("CARD/INNER-VOID") == 1
    assert "CARD/INNER-VOID: a <card contrib short>" in combined
    # The filled card A must NOT be flagged; card C (tall figure + short
    # text row + caption below) must NOT flag thanks to the row merge -- if
    # either slipped, the count above would be 2, not 1.
    assert "card contrib filled" not in combined
    # The untagged band .card blocks have no data-measure-role, so the older
    # CARD/TRAILING gate never sampled them, and the one tagged body card is
    # filled -- INNER-VOID is what closes the gap on a feature band.
    assert "CARD/TRAILING" not in combined
