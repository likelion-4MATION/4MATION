from __future__ import annotations

import pathlib
import sys
import types


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "admin"), str(ROOT / "crawler")]

import chain
import qform_trace
import registry
import settings


def test_context_k_default_and_explicit_override(monkeypatch):
    monkeypatch.setattr(chain, "CONTEXT_K", 4)

    assert chain._resolve_k(None) == 4
    assert chain._resolve_k(10) == 10


def test_qform_trace_uses_current_chain_k_when_result_has_no_k(monkeypatch):
    monkeypatch.setattr(chain, "CONTEXT_K", 4)

    assert qform_trace._runtime_k({}) == 4
    assert qform_trace._runtime_k({"k": 2}) == 2


def test_admin_k_defaults_to_five_and_is_injected_at_runtime(monkeypatch):
    cfg = {**registry.DEFAULTS, "k": 4}
    monkeypatch.setattr(settings, "current", lambda: cfg)
    monkeypatch.setitem(sys.modules, "rag", types.ModuleType("rag"))
    monkeypatch.setattr(chain, "CONTEXT_K", 99)

    touched = settings.apply_runtime()

    assert registry.DEFAULTS["k"] == 5
    assert chain.CONTEXT_K == 4
    assert "chain.CONTEXT_K" in touched
