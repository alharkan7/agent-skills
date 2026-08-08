"""Round-9 P1: the HARD gates (`measure` / `polish`) must FAIL-FAST when
the page never reaches network-idle, instead of measuring a partially
loaded poster (a blocked remote image/font could otherwise PASS).

Playwright is mocked via an injected fake `playwright.sync_api`, so these
run without a real Chromium. A MathJax-specific settle failure still
takes precedence over the generic nav-timeout message.
"""
from __future__ import annotations

import argparse
import sys
import types

import pytest

from _posterly import measure as _measure
from _posterly import polish as _polish


def _install_fake_playwright(monkeypatch):
    """Put a fake `playwright.sync_api` in sys.modules so the in-function
    `from playwright.sync_api import ...` resolves to it. Returns the fake
    TimeoutError class so the page mock can raise the exact type the gate
    catches."""

    class _Timeout(Exception):
        pass

    class _PW:  # context manager yielded by `with sync_playwright() as p`
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    mod = types.ModuleType("playwright.sync_api")
    mod.TimeoutError = _Timeout
    mod.sync_playwright = lambda: _PW()
    parent = types.ModuleType("playwright")
    parent.sync_api = mod
    monkeypatch.setitem(sys.modules, "playwright", parent)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", mod)
    return _Timeout


class _Browser:
    def close(self):
        pass


def _poster_html(tmp_path):
    # Needs @page (canvas resolution) AND poster/column/card roles so it
    # passes polish's static role pre-check and actually reaches the
    # Playwright/nav block under test.
    p = tmp_path / "poster.html"
    p.write_text(
        "<html><head><style>@page { size: 24in 36in }</style></head>"
        "<body><div data-measure-role=\"poster\">"
        "<div data-measure-role=\"column\">"
        "<div data-measure-role=\"card\"></div></div></div></body></html>",
        encoding="utf-8",
    )
    return p


def _arrange(monkeypatch, render, settle_problem):
    """Wire the render seams so goto() times out and settle reports
    `settle_problem` (None = clean, else a MathJax-style failure string).
    Returns the page mock so the test can assert evaluate() never ran."""
    timeout_cls = _install_fake_playwright(monkeypatch)

    class _Page:
        evaluated = False

        def goto(self, *a, **k):
            raise timeout_cls("nav timeout")

        def evaluate(self, *a, **k):
            self.evaluated = True
            return {}

    page = _Page()
    monkeypatch.setattr(
        render, "open_print_emulated_page",
        lambda p, vp: (_Browser(), None, page),
    )
    monkeypatch.setattr(render, "settle_page", lambda *a, **k: object())
    monkeypatch.setattr(
        render, "hard_fail_on_settle_problems",
        lambda *a, **k: settle_problem,
    )
    return page


def _args(html):
    return argparse.Namespace(
        html=str(html), canvas=None,
        mathjax_timeout_ms=15000, settle_ms=500,
    )


@pytest.mark.parametrize(
    "module, render",
    [(_measure, _measure._render), (_polish, _polish._render)],
)
def test_nav_timeout_fails_fast(tmp_path, monkeypatch, capsys, module, render):
    html = _poster_html(tmp_path)
    page = _arrange(monkeypatch, render, settle_problem=None)
    rc = module.cmd_measure(_args(html)) if module is _measure \
        else module.cmd_polish(_args(html))
    assert rc == 1
    assert page.evaluated is False  # never measured the partial page
    assert "network-idle" in capsys.readouterr().err


@pytest.mark.parametrize(
    "module, render",
    [(_measure, _measure._render), (_polish, _polish._render)],
)
def test_mathjax_problem_wins_over_nav_timeout(
    tmp_path, monkeypatch, capsys, module, render
):
    html = _poster_html(tmp_path)
    page = _arrange(
        monkeypatch, render, settle_problem="MathJax typeset timed out"
    )
    rc = module.cmd_measure(_args(html)) if module is _measure \
        else module.cmd_polish(_args(html))
    assert rc == 1
    assert page.evaluated is False
    assert "MathJax" in capsys.readouterr().err
