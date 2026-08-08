"""Polish: role-validation hard-fail. (Threshold / Playwright tests
live in a separate, slower integration test we don't run by default.)"""
from __future__ import annotations

import argparse

from _posterly import polish


def test_polish_hard_fails_on_no_roles(tmp_path) -> None:
    """A poster with NO data-measure-role markup must hard-fail polish
    rather than silently pass with ``figures: 0, columns: 0``. The
    polish PASS would otherwise read as "everything fine" on a file
    the tool can't actually reason about."""
    p = tmp_path / "noroles.html"
    p.write_text(
        "<html><head><style>@page { size: 36in 47in; }</style>"
        "</head><body><div>just a div</div></body></html>",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        html=str(p),
        canvas=None,
        settle_ms=500,
        mathjax_timeout_ms=15000,
        wide_min_ratio=0.65,
        tall_max_ratio=0.70,
        square_min_ratio=0.55,
        max_space_between_fill=0.05,
        strict=False,
    )
    rc = polish.cmd_polish(args)
    assert rc == 2, "polish must hard-fail (exit 2) on a role-less HTML"


def test_polish_hard_fails_on_partial_roles(tmp_path) -> None:
    """A poster with poster role but no cards / columns is also a
    role-less situation as far as polish is concerned — fail rather
    than silently sample 0 figures."""
    p = tmp_path / "partial.html"
    p.write_text(
        '<html><head><style>@page { size: 36in 47in; }</style>'
        '</head><body><div data-measure-role="poster">'
        '<div data-measure-role="header"></div></div></body></html>',
        encoding="utf-8",
    )
    args = argparse.Namespace(
        html=str(p),
        canvas=None,
        settle_ms=500,
        mathjax_timeout_ms=15000,
        wide_min_ratio=0.65,
        tall_max_ratio=0.70,
        square_min_ratio=0.55,
        max_space_between_fill=0.05,
        strict=False,
    )
    rc = polish.cmd_polish(args)
    assert rc == 2
