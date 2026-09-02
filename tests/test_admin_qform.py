"""관리자 콘솔 ↔ Q-Form 연결 회귀.

콘솔의 재검증·재청킹이 챗봇과 **같은 Q-Form 경로**를 타는지 본다. 이 연결이 끊기면
`QFORM_RETRIEVAL_MODE` 도 `QFORM_META_BOOST` 도 지표를 한 자리도 못 움직이는데,
화면에는 값이 저장된 것으로 보여서 관리자가 효과 없는 값을 계속 만지게 된다.
"""
from __future__ import annotations

import json
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "chatbot"), str(ROOT / "crawler"), str(ROOT / "admin")]

import jobs
import metrics
import qform_state
import runner

QUESTION = "미성년자 대신 착오송금 반환을 신청하려면?"
SLOTS = {"party": "송금인", "sub_task": "반환신청",
         "qualification": "대리인", "subject": "미성년자"}
EXPANDED = f"{QUESTION}\n\n{qform_state.serialize(SLOTS)}"
# 이 질문에서 결정론 추출기가 실제로 잡아내는 슬롯. 규칙에 없는 값은 만들지 않는다 —
# `반환을 신청` 은 sub_task 규칙에 걸리지 않고 송금인/수취인 어휘도 문장에 없다.
EXTRACTED = {"qualification": "대리인", "subject": "미성년자"}


def test_qform_query_follows_the_same_rules_as_the_chatbot_flow():
    assert runner.qform_query(QUESTION, SLOTS, "off") == (QUESTION, {})
    assert runner.qform_query(QUESTION, SLOTS, "field_value") == (EXPANDED, {})
    assert runner.qform_query(QUESTION, SLOTS, "metadata_soft") == (QUESTION, {"qform": SLOTS})
    assert runner.qform_query(QUESTION, SLOTS, "field_value_soft") == (EXPANDED, {"qform": SLOTS})


def test_qform_query_is_a_no_op_without_slots():
    for mode in ("off", "field_value", "metadata_soft", "field_value_soft"):
        assert runner.qform_query(QUESTION, {}, mode) == (QUESTION, {})


def test_qform_slots_use_the_evaluation_business_function_not_the_router():
    slots = runner.qform_slots(QUESTION, "착오송금 반환 신청", "msdr")
    assert slots == EXTRACTED                        # 못 잡은 슬롯은 키째 담지 않는다
    # 스코프 밖 업무는 슬롯을 만들지 않는다 — 착오송금 어휘가 그대로 있어도 마찬가지다.
    assert runner.qform_slots(QUESTION, "채무조정 안내", "msdr") == {}


def test_qform_warnings_catch_settings_that_are_on_but_do_nothing():
    keyed = {"available": True, "chunks": 10, "keyed": 10, "tagged": 4}
    assert runner.qform_warnings({"mode": "metadata_soft", "boost": 0.05}, keyed) == []
    # 태깅 이전에 만들어진 인덱스 — 다시 자르면 해결된다
    legacy = {"available": True, "chunks": 10, "keyed": 0, "tagged": 0}
    assert any("재청킹" in w for w in
               runner.qform_warnings({"mode": "metadata_soft", "boost": 0.05}, legacy))
    # 필드는 있는데 값이 없다 — 재청킹해도 그대로다(조합표 문제)
    empty = {"available": True, "chunks": 10, "keyed": 10, "tagged": 0}
    assert any("qform_combos" in w for w in
               runner.qform_warnings({"mode": "metadata_soft", "boost": 0.05}, empty))
    assert any("QFORM_META_BOOST" in w for w in
               runner.qform_warnings({"mode": "metadata_soft", "boost": 0.0}, keyed))
    # 검색문 확장만 쓰는 모드는 청크 메타가 없어도 정상 동작한다
    assert runner.qform_warnings({"mode": "field_value", "boost": 0.0}, legacy) == []


def test_meta_coverage_separates_a_missing_field_from_an_empty_value(tmp_path):
    path = tmp_path / "chunk_meta.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in [
        {"chunk_id": "c1", "qform_meta": {"sub_task": ["반환신청"], "method": ["방문"]}},
        {"chunk_id": "c2", "qform_meta": {}},
        {"chunk_id": "c3"},
    ]), encoding="utf-8")

    cov = metrics.qform_meta_coverage(path)
    assert (cov["chunks"], cov["keyed"], cov["tagged"]) == (3, 2, 1)
    assert cov["fields"]["sub_task"] == 1 and cov["fields"]["party"] == 0
    assert metrics.qform_meta_coverage(tmp_path / "없음.jsonl")["available"] is False


def test_dashboard_verdict_is_the_wiring_not_the_setting(tmp_path, monkeypatch):
    """`effective` 는 저장된 값이 아니라 **실제로 순위를 바꾸는가**를 말해야 한다."""
    index = tmp_path / "data" / "index"
    index.mkdir(parents=True)
    monkeypatch.setattr(metrics, "CRAWLER", tmp_path)

    def verdict(mode, boost, row):
        (index / "chunk_meta.jsonl").write_text(
            json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
        monkeypatch.setattr(metrics.settings, "effective", lambda: {
            "QFORM_RETRIEVAL_MODE": mode, "QFORM_META_BOOST": boost, "QFORM_SCOPE": "msdr"})
        return metrics.qform()

    tagged = {"chunk_id": "c1", "qform_meta": {"sub_task": ["반환신청"]}}
    legacy = {"chunk_id": "c1"}                     # 태깅 이전에 만들어진 인덱스

    assert verdict("metadata_soft", 0.05, tagged)["effective"] is True
    # 값은 켜져 있는데 청크에 메타가 없다 — 검색은 순수 hybrid 와 같다
    stale = verdict("metadata_soft", 0.05, legacy)
    assert stale["effective"] is False and any("재청킹" in r for r in stale["reasons"])
    # 가산치가 0이면 태깅이 아무리 많아도 순위는 안 바뀐다
    assert verdict("metadata_soft", 0.0, tagged)["effective"] is False
    # 검색문 확장 모드는 청크 메타와 무관하게 동작한다
    assert verdict("field_value", 0.0, legacy)["effective"] is True
    assert verdict("off", 0.05, tagged)["effective"] is False


def test_runner_step_name_matches_the_step_list_jobs_renders(tmp_path, capsys):
    """러너가 내보내는 `__STEP__` 문자열과 콘솔 단계 목록은 한 글자도 달라지면 안 된다."""
    out: dict = {}
    runner.check_qform(str(tmp_path), out)
    assert f"__STEP__ {jobs.QF}" in capsys.readouterr().out
    assert out["qform_meta"]["available"] is False
    for kind in ("eval", "rebuild", "rebuild_recrawl", "verify"):
        assert jobs.QF in jobs.STEPS[kind]


class StubSearcher:
    """`qform` 인자를 받았을 때만 정답 청크를 1위로 올리는 검색기."""

    def __init__(self, index_dir=None):
        self.calls = []

    def search(self, query, k=5, mode="hybrid", bf_override=None, qform=None):
        self.calls.append({"query": query, "qform": qform})
        order = ["c1", "c2"] if qform else ["c2", "c1"]
        return [{"chunk_id": c, "_qform_boost": 0.05 if (qform and c == "c1") else 0.0}
                for c in order]


def _eval_fixture(tmp_path, monkeypatch):
    (tmp_path / "idx").mkdir()
    (tmp_path / "idx" / "chunk_meta.jsonl").write_text("".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in [
            {"chunk_id": "c1", "parent_doc_id": "d1", "qform_meta": {"sub_task": ["반환신청"]},
             "text": "착오송금 반환 신청은 송금인이 합니다."},
            {"chunk_id": "c2", "parent_doc_id": "d1", "qform_meta": {},
             "text": "예금자보호 한도 안내입니다."},
        ]), encoding="utf-8")
    (tmp_path / "gt.jsonl").write_text(json.dumps({
        "id": "q1", "question": QUESTION, "business_function": "착오송금 반환 신청",
        "answerable": True, "chunk_relation": "single",
        "gt_chunk_ids": ["c1"], "gt_chunk_id": "c1",
        "gt_anchor_span": "착오송금 반환 신청은 송금인이 합니다.",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    searcher = StubSearcher()
    monkeypatch.setattr(runner, "CRAWLER", tmp_path)
    monkeypatch.setitem(sys.modules, "rag",
                        types.SimpleNamespace(Searcher=lambda index_dir: searcher))
    return searcher


def test_run_eval_drives_the_qform_path_and_measures_a_control_group(tmp_path, monkeypatch):
    searcher = _eval_fixture(tmp_path, monkeypatch)

    res = runner.run_eval(str(tmp_path / "idx"), gt_name="gt.jsonl",
                          qform={"mode": "metadata_soft", "boost": 0.05, "scope": "msdr"})

    assert searcher.calls[0]["qform"] == EXTRACTED
    assert searcher.calls[0]["query"] == QUESTION      # metadata 모드는 질문을 늘리지 않는다
    assert searcher.calls[1]["qform"] is None          # 대조군 — 같은 문항을 Q-Form 없이
    qf = res["qform"]
    assert (qf["mode"], qf["n_with_slots"], qf["boosted_hits"]) == ("metadata_soft", 1, 1)
    assert qf["slot_fields"] == {**{f: 0 for f in runner.QFORM_FIELDS},
                                 "qualification": 1, "subject": 1}
    assert qf["applied"]["on"]["hit@1"] == 1.0
    assert qf["applied"]["off"]["hit@1"] == 0.0
    assert qf["applied"]["delta"]["hit@1"] == 1.0
    assert res["hit@1"] == 1.0                          # 본 지표도 Q-Form 경로로 잰 값이다


def test_run_eval_without_qform_settings_keeps_the_old_behaviour(tmp_path, monkeypatch):
    searcher = _eval_fixture(tmp_path, monkeypatch)

    res = runner.run_eval(str(tmp_path / "idx"), gt_name="gt.jsonl")

    assert searcher.calls == [{"query": QUESTION, "qform": None}]   # 대조군도 돌지 않는다
    assert res["qform"] == {"mode": "off", "scope": "msdr", "boost": 0.0,
                            "n_questions": 1, "n_with_slots": 0,
                            "slot_fields": {f: 0 for f in runner.QFORM_FIELDS},
                            "boosted_hits": 0, "applied": None}
    assert res["hit@1"] == 0.0
