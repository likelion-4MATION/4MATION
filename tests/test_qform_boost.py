from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "crawler"), str(ROOT / "admin")]

import chain
import orchestrator
import qform_flow
import qform_metadata
import qform_state
import rag
import registry
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


def test_qform_flow_metadata_mode_keeps_original_query_and_forwards_mode():
    received = {}

    def answer(query, slots, *, retrieval_query=None, qform_retrieval_mode=None):
        received.update(query=query, slots=slots, retrieval_query=retrieval_query,
                        mode=qform_retrieval_mode)
        return {"text": "stub"}

    state = qform_flow.new_state()
    state["base_q"] = ORIGINAL
    state["qform"] = dict(SLOTS)
    event = qform_flow._finalize(
        state, boost=True, answer_fn=answer,
        config={"QFORM_RETRIEVAL_MODE": "metadata_soft"},
    )

    assert received == {
        "query": ORIGINAL, "slots": SLOTS, "retrieval_query": ORIGINAL,
        "mode": "metadata_soft",
    }
    assert event["search_q"] == ORIGINAL
    assert event["boosted"] is None
    assert event["qform_retrieval_mode"] == "metadata_soft"


def test_crawled_chunk_metadata_extracts_only_values_allowed_for_business():
    meta = qform_metadata.tag(
        "미성년자 자녀를 대신해 대리인이 착오송금 반환 신청 서류를 방문 제출합니다.",
        "착오송금 반환 신청",
    )

    assert "반환신청" in meta["sub_task"]
    assert meta["qualification"] == ["대리인"]
    assert meta["subject"] == ["미성년자", "대리인"]
    assert meta["method"] == ["방문"]
    assert qform_metadata.tag("미성년자 대리 신청", "채무조정 안내") == {}


def test_qform_metadata_soft_boost_scales_by_matching_field_ratio():
    searcher = object.__new__(rag.Searcher)
    searcher.chunks = [
        {"qform_meta": {"sub_task": ["반환신청"], "qualification": ["대리인"],
                         "subject": ["미성년자"]}},
        {"qform_meta": {"sub_task": ["반환신청"]}},
        {"qform_meta": {}},
    ]
    scores = {0: 0.5, 1: 0.5, 2: 0.5}
    applied = searcher._apply_qform_meta_boost(
        scores,
        {"sub_task": "반환신청", "qualification": "대리인", "subject": "미성년자"},
        boost=0.09,
    )

    assert scores[0] == 0.59
    assert scores[1] == 0.53
    assert scores[2] == 0.5
    assert applied[0]["matches"] == ["sub_task", "qualification", "subject"]


def test_admin_exposes_qform_retrieval_mode_and_metadata_weight():
    assert registry.DEFAULTS["QFORM_RETRIEVAL_MODE"] == "field_value"
    assert registry.DEFAULTS["QFORM_META_BOOST"] == 0.05
    assert not registry.validate({"QFORM_RETRIEVAL_MODE": "metadata_soft",
                                  "QFORM_META_BOOST": 0.08})
    assert registry.validate({"QFORM_RETRIEVAL_MODE": "unknown"})
    assert registry.validate({"QFORM_META_BOOST": 1.0})


class RecordingSearcher:
    def __init__(self):
        self.calls = []

    def search(self, query, *, k, mode, bf_override=None, qform=None):
        call = {"query": query, "k": k, "mode": mode, "bf": bf_override}
        if qform is not None:
            call["qform"] = qform
        self.calls.append(call)
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


def test_chain_passes_slots_to_searcher_only_for_metadata_mode():
    searcher = RecordingSearcher()
    original_searcher, original_gate = chain._searcher, chain._generate_with_gate
    chain._searcher = searcher
    chain._generate_with_gate = lambda *_args, **_kwargs: (
        "안내입니다. [출처1]",
        {"provider": "stub", "model": "stub", "latency_ms": 0, "error": None},
        {"ok": True, "flags": [], "gate": {"action": "passed"}},
    )
    try:
        result = chain.answer_in_scope(
            ORIGINAL, qform=SLOTS, bf="착오송금 반환 신청",
            qform_retrieval_mode="metadata_soft",
        )
    finally:
        chain._searcher, chain._generate_with_gate = original_searcher, original_gate

    assert searcher.calls[0]["query"] == ORIGINAL
    assert searcher.calls[0]["qform"] == SLOTS
    assert result["_meta"]["qform_retrieval_mode"] == "metadata_soft"
    assert result["_meta"]["qform_metadata_applied"] is True


def test_orchestrator_forwards_expanded_query_to_scoped_chain():
    query = "착오송금 반환 신청을 철회하고 싶어요"
    received = {}

    def answer_in_scope(original_query, k=None, qform=None, bf=None, *, retrieval_query=None,
                        qform_retrieval_mode="off"):
        received.update(
            original_query=original_query,
            k=k,
            qform=qform,
            bf=bf,
            retrieval_query=retrieval_query,
            qform_retrieval_mode=qform_retrieval_mode,
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
    assert received["qform_retrieval_mode"] == "field_value"
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
