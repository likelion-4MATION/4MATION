from __future__ import annotations

import pathlib
import sys
import types


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "admin"), str(ROOT / "crawler")]

import answer_checks
import chain
import metrics
import registry
import settings
from web.service import RuntimeBackend


HITS = [{
    "chunk_id": "chunk-1",
    "parent_doc_id": "doc-1",
    "page_title": "보호한도 안내",
    "source_url": "https://example.test/source",
    "text": "예금 보호한도는 1억원입니다. 자세한 내용은 https://example.test/context 에 있습니다.",
    "_score": 0.5,
}]
MESSAGES = [
    {"role": "system", "content": "근거로만 답하세요."},
    {"role": "user", "content": "보호한도는 얼마인가요?"},
]


def configure(monkeypatch, *, enabled=True, mode="warn", retries=1):
    monkeypatch.setattr(chain, "ANSWER_CHECKS_ENABLED", enabled)
    monkeypatch.setattr(chain, "ANSWER_GATE_MODE", mode)
    monkeypatch.setattr(chain, "ANSWER_GATE_MAX_RETRIES", retries)
    monkeypatch.setattr(chain, "CHECK_URLS_ENABLED", True)
    monkeypatch.setattr(chain, "CHECK_CITATIONS_ENABLED", True)
    monkeypatch.setattr(chain, "CHECK_NUMBERS_ENABLED", True)
    monkeypatch.setattr(chain, "STRICT_URL", True)


def llm_meta():
    return {
        "provider": "stub",
        "model": "stub",
        "model_status": 200,
        "latency_ms": 3,
        "error": None,
    }


def test_answer_checks_can_toggle_each_rule_independently():
    answer = "근거 없는 2억원과 https://bad.test 를 안내합니다."
    all_checks = answer_checks.run_all(answer, HITS)
    no_checks = answer_checks.run_all(
        answer,
        HITS,
        check_urls_enabled=False,
        check_citations_enabled=False,
        check_numbers_enabled=False,
    )

    assert all_checks["ok"] is False
    assert set(all_checks["results"]) == {"check_urls", "check_citations", "check_numbers"}
    assert no_checks == {"ok": True, "flags": [], "results": {}}


def test_warn_mode_preserves_failed_answer(monkeypatch):
    configure(monkeypatch, mode="warn")
    calls = []

    def llm(messages, req_id, params=chain.GEN_PARAMS, **_kwargs):
        calls.append((messages, req_id, params))
        return "근거 없는 2억원입니다.", llm_meta()

    monkeypatch.setattr(chain, "_llm", llm)
    text, meta, checks = chain._generate_with_gate(MESSAGES, HITS, "test")

    assert text == "근거 없는 2억원입니다."
    assert checks["ok"] is False
    assert checks["gate"]["action"] == "warned"
    assert checks["gate"]["generation_attempts"] == 1
    assert meta["answer_gate_action"] == "warned"
    assert len(calls) == 1


def test_block_mode_replaces_failed_answer(monkeypatch):
    configure(monkeypatch, mode="block")
    monkeypatch.setattr(
        chain,
        "_llm",
        lambda *_args, **_kwargs: ("근거 없는 답변입니다.", llm_meta()),
    )

    text, meta, checks = chain._generate_with_gate(MESSAGES, HITS, "test")

    assert text == chain.ANSWER_GATE_BLOCK_TEXT
    assert checks["ok"] is False
    assert checks["gate"]["action"] == "blocked"
    assert meta["answer_gate_action"] == "blocked"


def test_regenerate_mode_rechecks_and_returns_corrected_answer(monkeypatch):
    configure(monkeypatch, mode="regenerate", retries=1)
    responses = iter([
        "보호한도는 2억원입니다.",
        "예금 보호한도는 1억원입니다. [출처1]",
    ])
    calls = []

    def llm(messages, req_id, params=chain.GEN_PARAMS, **_kwargs):
        calls.append((messages, req_id, params))
        return next(responses), llm_meta()

    monkeypatch.setattr(chain, "_llm", llm)
    text, meta, checks = chain._generate_with_gate(MESSAGES, HITS, "test")

    assert text == "예금 보호한도는 1억원입니다. [출처1]"
    assert checks["ok"] is True
    assert checks["gate"]["action"] == "regenerated"
    assert checks["gate"]["retries"] == 1
    assert meta["generation_attempts"] == 2
    assert meta["latency_ms"] == 6
    assert "[자동 검증 결과]" in calls[1][0][-1]["content"]


def test_regenerate_exhaustion_returns_last_answer_with_flags(monkeypatch):
    configure(monkeypatch, mode="regenerate", retries=1)
    responses = iter(["첫 번째 근거 없는 답변", "두 번째도 근거 없는 답변"])
    monkeypatch.setattr(
        chain,
        "_llm",
        lambda *_args, **_kwargs: (next(responses), llm_meta()),
    )

    text, _meta, checks = chain._generate_with_gate(MESSAGES, HITS, "test")

    assert text == "두 번째도 근거 없는 답변"
    assert checks["ok"] is False
    assert checks["gate"]["action"] == "regenerate_exhausted"


def test_disabled_gate_skips_rules_without_extra_generation(monkeypatch):
    configure(monkeypatch, enabled=False, mode="block")
    calls = []

    def llm(*_args, **_kwargs):
        calls.append(True)
        return "검증하지 않을 답변", llm_meta()

    monkeypatch.setattr(chain, "_llm", llm)
    text, _meta, checks = chain._generate_with_gate(MESSAGES, HITS, "test")

    assert text == "검증하지 않을 답변"
    assert checks["ok"] is True
    assert checks["skipped"] == "관리자 설정으로 비활성화"
    assert checks["gate"]["action"] == "disabled"
    assert len(calls) == 1


def test_admin_registry_exposes_validated_gate_settings():
    expected = {
        "answerChecksEnabled", "answerGateMode", "answerGateMaxRetries",
        "checkUrls", "checkCitations", "checkNumbers", "strictUrl",
    }

    assert expected <= registry.BY_KEY.keys()
    assert registry.DEFAULTS["answerGateMode"] == "warn"
    assert registry.validate({"answerGateMode": "unknown"})
    assert registry.validate({"answerGateMaxRetries": 3})
    assert not registry.validate({"answerGateMode": "block", "answerGateMaxRetries": 2})


def test_admin_projection_uses_regeneration_worst_case_upper_bound():
    warn = {**registry.DEFAULTS, "answerGateMode": "warn"}
    regenerate = {
        **registry.DEFAULTS,
        "answerGateMode": "regenerate",
        "answerGateMaxRetries": 2,
    }

    warn_ops = metrics._ops(warn)
    retry_ops = metrics._ops(regenerate)
    projected = metrics.projection(regenerate, ["answerGateMode"], saved=warn)

    assert retry_ops["calls"] > warn_ops["calls"]
    assert retry_ops["latency"] > warn_ops["latency"]
    assert retry_ops["cost"] > warn_ops["cost"]
    assert projected["calls"]["grade"] == "estimated"
    assert "상한" in projected["calls"]["src"]


def test_admin_runtime_injects_gate_settings(monkeypatch):
    cfg = {
        **registry.DEFAULTS,
        "answerChecksEnabled": False,
        "answerGateMode": "block",
        "answerGateMaxRetries": 2,
        "checkUrls": False,
        "checkCitations": False,
        "checkNumbers": True,
        "strictUrl": False,
        "guardsEnabled": False,
    }
    monkeypatch.setattr(settings, "current", lambda: cfg)
    monkeypatch.setitem(sys.modules, "rag", types.ModuleType("rag"))
    for name in (
        "ANSWER_CHECKS_ENABLED", "ANSWER_GATE_MODE", "ANSWER_GATE_MAX_RETRIES",
        "CHECK_URLS_ENABLED", "CHECK_CITATIONS_ENABLED", "CHECK_NUMBERS_ENABLED", "STRICT_URL",
        "GUARDS_ENABLED",
    ):
        monkeypatch.setattr(chain, name, getattr(chain, name))

    settings.apply_runtime()

    assert chain.ANSWER_CHECKS_ENABLED is False
    assert chain.ANSWER_GATE_MODE == "block"
    assert chain.ANSWER_GATE_MAX_RETRIES == 2
    assert chain.CHECK_URLS_ENABLED is False
    assert chain.CHECK_CITATIONS_ENABLED is False
    assert chain.CHECK_NUMBERS_ENABLED is True
    assert chain.STRICT_URL is False
    assert chain.GUARDS_ENABLED is False


def test_runtime_backend_refreshes_changed_admin_config_once(monkeypatch):
    backend = RuntimeBackend.__new__(RuntimeBackend)
    calls = []
    backend.settings_store = types.SimpleNamespace(apply_runtime=lambda: calls.append(True))
    backend._settings_revision = (1, 1, 1)
    monkeypatch.setattr(backend, "_config_revision", lambda: (2, 2, 2))

    backend.refresh_runtime()
    backend.refresh_runtime()

    assert calls == [True]
    assert backend._settings_revision == (2, 2, 2)
