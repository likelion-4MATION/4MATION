from __future__ import annotations

import copy
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "admin"), str(ROOT / "crawler")]

import answer_checks
import chain
import guards


def guard_row(**overrides):
    row = {
        "id": "guard-limit",
        "title": "예금보호한도 정정",
        "kind": "override",
        "triggers": ["보호한도", "5천만원"],
        "business": ["예금자보호제도"],
        "old_value": "5천만원",
        "new_value": "1억원",
        "statement": "예금보호한도는 1인당 1억원입니다.",
        "source": "예금자보호법 시행령 개정",
        "start": "2000-01-01",
        "end": "2999-12-31",
        "priority": 100,
        "status": "approved",
        "fired": 0,
    }
    row.update(overrides)
    return row


def hit():
    return {
        "chunk_id": "chunk-1",
        "parent_doc_id": "doc-1",
        "page_title": "보호한도 안내",
        "source_url": "https://example.test/limit",
        "text": "예금보호한도는 5천만원입니다.",
        "business_function": "예금자보호제도",
        "has_attachments": False,
        "attachments": [],
        "_score": 0.5,
    }


def test_match_requires_approved_effective_period_business_and_trigger(monkeypatch):
    rows = [
        guard_row(id="active", priority=10),
        guard_row(id="future", start="2999-01-01", priority=50),
        guard_row(id="expired", end="2001-01-01", priority=40),
        guard_row(id="draft", status="draft", priority=30),
        guard_row(id="other-business", business=["착오송금 반환 신청"], priority=20),
    ]
    monkeypatch.setattr(guards, "_load", lambda: copy.deepcopy(rows))

    matched = guards.match(
        "현재 기준이 궁금해요",
        "문서에는 보호한도 5천만원이라고 적혀 있습니다.",
        business={"예금자보호제도"},
    )

    assert [g["id"] for g in matched] == ["active"]


def test_guard_is_injected_and_forwarded_to_checks_and_counter(monkeypatch):
    active = guard_row()
    calls = {"match": [], "gate": [], "bump": []}

    class Searcher:
        def search(self, query, *, k, mode, bf_override=None, qform=None):
            if mode == "dense":
                return [{"_score": 0.75}]
            return [hit()]

    def match(query, context, business=None):
        calls["match"].append((query, context, business))
        return [active]

    def gate(messages, hits, req_id, **kwargs):
        calls["gate"].append((messages, hits, req_id, kwargs))
        return (
            "예금보호한도는 1인당 1억원입니다. [관리자 정정]",
            {"provider": "stub", "model": "stub", "latency_ms": 0, "error": None},
            {"ok": True, "flags": [], "gate": {"action": "passed"}},
        )

    monkeypatch.setattr(chain, "GUARDS_ENABLED", True)
    monkeypatch.setattr(chain, "_searcher", Searcher())
    monkeypatch.setattr(chain.guards, "match", match)
    monkeypatch.setattr(chain.guards, "bump_fired", lambda ids: calls["bump"].append(ids))
    monkeypatch.setattr(chain, "_generate_with_gate", gate)
    monkeypatch.setattr(chain.attachments, "collect", lambda *_args, **_kwargs: [])

    result = chain.answer_in_scope(
        "예금보호한도는 얼마인가요?", bf="예금자보호제도"
    )

    user_prompt = calls["gate"][0][0][1]["content"]
    gate_kwargs = calls["gate"][0][3]
    assert "[관리자 정정 사실]" in user_prompt
    assert "예금보호한도는 1인당 1억원입니다." in user_prompt
    assert user_prompt.endswith("[질문]\n예금보호한도는 얼마인가요?")
    assert gate_kwargs["allowed_numbers"] == {"1억원"}
    assert gate_kwargs["admin_correction_allowed"] is True
    assert calls["match"][0][2] == "예금자보호제도"
    assert calls["bump"] == [["guard-limit"]]
    assert result["_meta"]["guards"]["applied"] is True
    assert result["_meta"]["guards"]["matched"][0]["id"] == "guard-limit"


def test_guard_numbers_and_admin_marker_pass_answer_checks():
    answer = "예금보호한도는 1인당 1억원입니다. [관리자 정정]"

    without_guard = answer_checks.run_all(answer, [hit()])
    with_guard = answer_checks.run_all(
        answer,
        [hit()],
        allowed_numbers={"1억원"},
        admin_correction_allowed=True,
    )

    assert without_guard["ok"] is False
    assert with_guard["ok"] is True


def test_disabled_guard_does_not_read_or_inject_rules(monkeypatch):
    monkeypatch.setattr(chain, "GUARDS_ENABLED", False)
    monkeypatch.setattr(
        chain.guards,
        "match",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("호출되면 안 됨")),
    )

    messages, matched, whitelist, error = chain._generation_inputs(
        "예금보호한도는 얼마인가요?", [hit()], business="예금자보호제도"
    )

    assert "[관리자 정정 사실]" not in messages[1]["content"]
    assert matched == []
    assert whitelist == set()
    assert error is None
