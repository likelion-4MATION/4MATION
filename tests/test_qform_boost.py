from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "crawler")]

import chain
import orchestrator
import qform_flow
import qform_state
from web.sessions import SessionRecord


ORIGINAL = "미성년자 대신 착오송금 반환을 신청하려면?"
SLOTS = {
    "party": "송금인",
    "sub_task": "반환신청",
    "qualification": "대리인",
    "subject": "미성년자",
    "method": None,
}
EXPANSION = (
    "[QFORM]\n"
    "party: 송금인\n"
    "sub_task: 반환신청\n"
    "qualification: 대리인\n"
    "subject: 미성년자"
)
RETRIEVAL = f"{ORIGINAL}\n\n{EXPANSION}"


def test_serialize_uses_fixed_field_value_lines_and_omits_empty_values():
    slots = {**SLOTS, "subject": "미성년자\n  자녀", "method": ""}
    assert qform_state.serialize(slots) == EXPANSION.replace("미성년자", "미성년자 자녀")
    assert qform_state.serialize({field: None for field in qform_state.SLOT_FIELDS}) == ""


def test_qform_flow_separates_original_and_retrieval_queries():
    received = {}

    def answer(query, slots, *, retrieval_query=None):
        received.update(query=query, slots=slots, retrieval_query=retrieval_query)
        return {"text": "stub"}

    state = qform_flow.new_state()
    state["base_q"] = ORIGINAL
    state["qform"] = dict(SLOTS)
    event = qform_flow._finalize(state, boost=True, answer_fn=answer)

    assert received == {"query": ORIGINAL, "slots": SLOTS, "retrieval_query": RETRIEVAL}
    assert event["query"] == ORIGINAL
    assert event["search_q"] == RETRIEVAL
    assert event["boosted"] == RETRIEVAL


def test_qform_flow_off_path_and_legacy_callback_are_unchanged():
    received = []
    state = qform_flow.new_state()
    state["base_q"] = ORIGINAL
    state["qform"] = dict(SLOTS)

    event = qform_flow._finalize(
        state,
        boost=False,
        answer_fn=lambda query, slots: received.append((query, slots)) or {"text": "stub"},
    )

    assert received == [(ORIGINAL, SLOTS)]
    assert event["query"] == ORIGINAL
    assert event["search_q"] == ORIGINAL
    assert event["boosted"] is None


class RecordingSearcher:
    def __init__(self):
        self.calls = []

    def search(self, query, *, k, mode, bf_override=None):
        self.calls.append({"query": query, "k": k, "mode": mode, "bf": bf_override})
        if mode == "dense":
            return [{"_score": 0.75}]
        return [{
            "chunk_id": "chunk-1",
            "parent_doc_id": "doc-1",
            "page_title": "테스트 문서",
            "source_url": "https://example.test/doc-1",
            "text": "착오송금 반환 신청에 필요한 서류 안내",
            "business_function": "착오송금 반환 신청",
            "sub_category": "신청 안내",
            "has_attachments": False,
            "attachments": [],
            "_score": 0.5,
        }]


def test_chain_searches_expanded_query_but_prompts_with_original_query():
    searcher = RecordingSearcher()
    prompts = []

    def llm(messages, req_id, params=chain.GEN_PARAMS, **_kwargs):
        prompts.append({"messages": messages, "req_id": req_id, "params": params})
        return "안내입니다. [출처1]", {
            "provider": "stub", "model": "stub", "model_status": 200,
            "latency_ms": 0, "error": None,
        }

    original_searcher, original_llm = chain._searcher, chain._llm
    chain._searcher, chain._llm = searcher, llm
    try:
        result = chain.answer_in_scope(
            ORIGINAL,
            qform=SLOTS,
            bf="착오송금 반환 신청",
            retrieval_query=RETRIEVAL,
        )
    finally:
        chain._searcher, chain._llm = original_searcher, original_llm

    assert searcher.calls[0] == {
        "query": RETRIEVAL, "k": 5, "mode": "hybrid_bf", "bf": "착오송금 반환 신청"
    }
    assert searcher.calls[1] == {"query": RETRIEVAL, "k": 1, "mode": "dense", "bf": None}
    user_prompt = prompts[0]["messages"][1]["content"]
    assert user_prompt.endswith(f"[질문]\n{ORIGINAL}")
    assert f"[질문]\n{RETRIEVAL}" not in user_prompt
    assert result["_meta"]["original_query"] == ORIGINAL
    assert result["_meta"]["retrieval_query"] == RETRIEVAL
    assert result["_meta"]["retrieval_boosted"] is True


def test_orchestrator_forwards_expanded_query_to_scoped_chain():
    query = "착오송금 반환 신청을 철회하고 싶어요"
    received = {}

    def answer_in_scope(original_query, k=None, qform=None, bf=None, *, retrieval_query=None):
        received.update(
            original_query=original_query,
            k=k,
            qform=qform,
            bf=bf,
            retrieval_query=retrieval_query,
        )
        return {
            "text": "stub", "sources": [], "confidence": 0.0, "route": "rag",
            "checks": {"ok": True, "flags": []}, "attachments": [], "_meta": {},
        }

    original_answer = chain.answer_in_scope
    chain.answer_in_scope = answer_in_scope
    try:
        event = orchestrator.start_turn(
            qform_flow.new_state(),
            query,
            boost=True,
            route_fn=lambda _text: {
                "triggered": True,
                "bf": "착오송금 반환 신청",
                "scores": {},
                "source": "test",
                "error": None,
            },
        )
    finally:
        chain.answer_in_scope = original_answer

    assert event["kind"] == "answer"
    assert received["original_query"] == query
    assert received["bf"] == "착오송금 반환 신청"
    assert received["retrieval_query"] == event["search_q"]
    assert event["search_q"].startswith(f"{query}\n\n[QFORM]\n")
    assert "sub_task: 신청철회" in event["search_q"]


def test_multiturn_carryover_values_are_included_in_retrieval_query():
    calls = []

    def answer(query, slots, *, retrieval_query=None):
        calls.append({"query": query, "slots": dict(slots), "retrieval_query": retrieval_query})
        return {"text": "stub", "attachments": []}

    def classify(_query):
        return "착오송금 반환 신청"

    state = qform_flow.new_state()
    event = qform_flow.start(
        state,
        "착오송금 반환 신청하려는데 필요한 서류 알려주세요",
        classify_fn=classify,
        answer_fn=answer,
        boost=True,
        detect_multi=False,
    )
    assert event["kind"] == "ask"
    event = qform_flow.reply(state, "대리인이 신청해요", answer_fn=answer, boost=True)
    assert event["kind"] == "ask"
    event = qform_flow.reply(state, "법인이요", answer_fn=answer, boost=True)
    assert event["kind"] == "answer"

    event = qform_flow.start(
        state,
        "준비물도 알려줘",
        classify_fn=classify,
        answer_fn=answer,
        boost=True,
        detect_multi=False,
    )

    assert event["kind"] == "answer"
    assert calls[-1]["query"] == "준비물도 알려줘"
    assert state["slot_origin"]["qualification"] == qform_flow.SRC_CARRY
    assert state["slot_origin"]["subject"] == qform_flow.SRC_CARRY
    assert "qualification: 대리인" in calls[-1]["retrieval_query"]
    assert "subject: 법인" in calls[-1]["retrieval_query"]


def test_new_web_sessions_enable_qform_retrieval_boost_by_default():
    record = SessionRecord(session_id="test", flow={})
    assert record.settings["boost"] is True
