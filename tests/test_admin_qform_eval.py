from __future__ import annotations

import json
import pathlib
import sys
import types


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "admin"), str(ROOT / "chatbot"), str(ROOT / "crawler")]

import metrics
import registry
import runner


QUERY = "법인 대리인이 착오송금 반환을 방문 신청할 때 서류 알려줘"
BF = "착오송금 반환 신청"


def test_qform_eval_request_distinguishes_all_four_modes():
    got = {}
    for mode in ("off", "field_value", "metadata_soft", "field_value_soft"):
        request = runner._qform_search_request(QUERY, BF, mode=mode, scope="msdr")
        got[mode] = {
            "expanded": request["query"] != QUERY,
            "metadata": "qform" in request["kwargs"],
            "active": request["active"],
        }

    assert got == {
        "off": {"expanded": False, "metadata": False, "active": True},
        "field_value": {"expanded": True, "metadata": False, "active": True},
        "metadata_soft": {"expanded": False, "metadata": True, "active": True},
        "field_value_soft": {"expanded": True, "metadata": True, "active": True},
    }


def test_qform_mode_projection_requires_matching_measurement(monkeypatch):
    cfg = registry.resolve({"QFORM_RETRIEVAL_MODE": "metadata_soft"})
    monkeypatch.setattr(metrics.settings, "measured_history", lambda: [])

    missing = metrics.accuracy_for(cfg, ["QFORM_RETRIEVAL_MODE"])

    assert missing["value"] is None
    assert missing["grade"] == "unmeasured"

    snapshot = {key: cfg[key] for key in metrics.MEASURE_MATCH_KEYS}
    snapshot["QFORM_META_BOOST"] = cfg["QFORM_META_BOOST"]
    rec = {
        "qform_eval_version": metrics.QFORM_EVAL_VERSION,
        "qform_mode": "metadata_soft",
        "qform_scope": cfg["QFORM_SCOPE"],
        "hit@5": 0.875,
        "n_evaluated": 430,
        "chunks": 181,
        "at": "2026-09-01T00:00:00+09:00",
        "cfg": snapshot,
    }
    monkeypatch.setattr(metrics.settings, "measured_history", lambda: [rec])

    measured = metrics.accuracy_for(cfg, ["QFORM_RETRIEVAL_MODE"])

    assert measured["value"] == 0.875
    assert measured["grade"] == "measured"


def test_run_eval_uses_predicted_business_function_and_same_population_in_all_modes(tmp_path, monkeypatch):
    # 정답 업무를 일부러 뒤집는다. 평가 라벨이 슬롯 게이트나 검색으로 새면 실패해야 한다.
    gt = [
        {"id": "q1", "question": QUERY, "answerable": True,
         "business_function": "예금자보호제도", "gt_chunk_ids": ["c1"], "gt_anchor_span": "근거"},
        {"id": "q2", "question": "예금자 보호 한도는?", "answerable": True,
         "business_function": BF, "gt_chunk_ids": ["c1"],
         "gt_anchor_span": "근거"},
    ]
    (tmp_path / "gt.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in gt), encoding="utf-8"
    )
    index = tmp_path / "index"
    index.mkdir()
    (index / "chunk_meta.jsonl").write_text(
        json.dumps({"chunk_id": "c1", "parent_doc_id": "d1", "text": "근거"}),
        encoding="utf-8",
    )

    calls, classified = [], []

    class Searcher:
        def __init__(self, index_dir):
            self.index_dir = index_dir

        def search(self, query, *, k, mode, **kwargs):
            calls.append({"query": query, "kwargs": kwargs})
            return [{"chunk_id": "c1"}]

    fake_rag = types.ModuleType("rag")
    fake_rag.Searcher = Searcher

    def classify(question):
        classified.append(question)
        assert question in (QUERY, "예금자 보호 한도는?")  # 확장문으로 재분류하지 않는다.
        return BF if question == QUERY else "예금자보호제도"

    fake_rag.classify_query_bf = classify

    fake_eval = types.ModuleType("eval")
    fake_eval._load_jsonl = lambda path: [
        json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    def evaluate(rows, retrieved, chunk_meta, **kwargs):
        n = len(rows)
        anchor = {"n_scored": n, "n_missing_span": 0, "hit@1": 1.0,
                  "hit@3": 1.0, "hit@5": 1.0, "hit@10": 1.0, "mrr": 1.0}
        return {"chunk_level": {"hit@5": 1.0, "n_evaluated": n,
                                "macro_recall@50": 1.0},
                "anchor_level": anchor}

    fake_eval.evaluate_retrieval = evaluate
    monkeypatch.setattr(runner, "CRAWLER", tmp_path)
    monkeypatch.setitem(sys.modules, "rag", fake_rag)
    monkeypatch.setitem(sys.modules, "eval", fake_eval)

    for mode in ("off", "field_value", "metadata_soft", "field_value_soft"):
        calls.clear()
        classified.clear()
        result = runner.run_eval(
            str(index), gt_name="gt.jsonl",
            qform={"mode": mode, "scope": "msdr", "boost": 0.05},
        )
        expanded = mode in ("field_value", "field_value_soft")
        metadata = mode in ("metadata_soft", "field_value_soft")

        assert classified == [QUERY, "예금자 보호 한도는?"]
        assert len(calls) == (2 if mode == "off" else 3)
        assert (calls[0]["query"] != QUERY) is expanded
        assert ("qform" in calls[0]["kwargs"]) is metadata
        assert calls[0]["kwargs"]["bf_override"] == BF
        assert calls[1] == {"query": "예금자 보호 한도는?",
                            "kwargs": {"bf_override": "예금자보호제도"}}
        if mode != "off":
            assert calls[2] == {"query": QUERY, "kwargs": {"bf_override": BF}}
            assert result["qform"]["applied"]["n"] == 1
            assert result["qform"]["applied"]["delta"]["hit@5"] == 0.0
        else:
            assert result["qform"]["applied"] is None
        assert result["qform_mode"] == result["qform"]["mode"] == mode
        assert result["qform_eval_version"] == runner.QFORM_EVAL_VERSION
        assert result["qform_n_total"] == result["qform"]["n_with_slots"] == 1
        assert result["qform_hit@5"] == 1.0
        assert result["qform_expanded_queries"] == int(expanded)
        assert result["qform_metadata_queries"] == int(metadata)
