from __future__ import annotations

import pathlib
import sys
import types

import pytest


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "admin"), str(ROOT / "crawler")]

import chain
import metrics
import registry
import settings


def test_chain_switches_provider_and_display_model_together(monkeypatch):
    monkeypatch.setattr(chain, "LLM_PROVIDER", "hcx")
    monkeypatch.setattr(chain, "MODEL_NAME", "hcx-test")
    monkeypatch.setattr(chain, "DEEPSEEK_MODEL", "deepseek-test")
    monkeypatch.setattr(chain, "UPSTAGE_MODEL", "solar-test")

    selected = chain.set_llm_provider("deepseek")

    assert selected == "deepseek-test"
    assert chain.LLM_PROVIDER == "deepseek"
    assert chain.MODEL_NAME == "deepseek-test"
    assert chain.set_llm_provider("upstage") == "solar-test"
    assert chain.LLM_PROVIDER == "upstage"
    assert chain.MODEL_NAME == "solar-test"
    with pytest.raises(ValueError):
        chain.set_llm_provider("unknown")


def test_provider_request_uses_its_configured_model(monkeypatch):
    monkeypatch.setattr(chain, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(chain, "DEEPSEEK_MODEL", "deepseek-test")

    headers, payload = chain._request_parts(
        "deepseek", [{"role": "user", "content": "test"}], "req", chain.GEN_PARAMS, 1
    )

    assert headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "deepseek-test"
    assert payload["messages"][0]["content"] == "test"

    monkeypatch.setattr(chain, "UPSTAGE_API_KEY", "upstage-test-key")
    monkeypatch.setattr(chain, "UPSTAGE_MODEL", "solar-test")
    headers, payload = chain._request_parts(
        "upstage", [{"role": "user", "content": "test"}], "req", chain.CLS_PARAMS, 1
    )

    assert headers["Authorization"] == "Bearer upstage-test-key"
    assert payload["model"] == "solar-test"
    assert "thinking" not in payload
    assert "response_format" not in payload


def test_admin_model_selection_is_validated_and_injected(monkeypatch):
    cfg = {**registry.DEFAULTS, "llmProvider": "deepseek"}
    monkeypatch.setattr(settings, "current", lambda: cfg)
    monkeypatch.setitem(sys.modules, "rag", types.ModuleType("rag"))
    monkeypatch.setattr(chain, "LLM_PROVIDER", "hcx")
    monkeypatch.setattr(chain, "MODEL_NAME", "hcx-test")
    monkeypatch.setattr(chain, "DEEPSEEK_MODEL", "deepseek-test")

    touched = settings.apply_runtime()

    assert registry.DEFAULTS["llmProvider"] == "hcx"
    assert registry.validate({"llmProvider": "unknown"})
    assert not registry.validate({"llmProvider": "deepseek"})
    assert not registry.validate({"llmProvider": "upstage"})
    assert chain.LLM_PROVIDER == "deepseek"
    assert chain.MODEL_NAME == "deepseek-test"
    assert "chain.LLM_PROVIDER" in touched


@pytest.mark.parametrize("provider", ["deepseek", "upstage"])
def test_non_hcx_projection_does_not_reuse_hcx_latency_or_cost(provider):
    cfg = {**registry.DEFAULTS, "llmProvider": provider}

    projected = metrics.projection(cfg, ["llmProvider"], saved=registry.DEFAULTS)

    assert projected["calls"]["value"] is not None
    assert projected["latency"]["value"] is None
    assert projected["latency"]["grade"] == "unmeasured"
    assert projected["cost"]["value"] is None
    assert projected["cost"]["grade"] == "unmeasured"


def test_upstage_missing_key_stops_before_http(monkeypatch):
    monkeypatch.setattr(chain, "UPSTAGE_API_KEY", "")
    monkeypatch.setattr(chain, "UPSTAGE_API_URL", "https://api.upstage.ai/v1/chat/completions")
    monkeypatch.setattr(
        chain.requests,
        "post",
        lambda *_args, **_kwargs: pytest.fail("설정 누락이면 HTTP 호출 전에 중단해야 합니다."),
    )

    text, meta = chain._llm(
        [{"role": "user", "content": "test"}], "test", provider="upstage"
    )

    assert text is None
    assert meta["provider"] == "upstage"
    assert meta["error"] == "missing_upstage_configuration"
