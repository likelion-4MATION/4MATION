# -*- coding: utf-8 -*-
"""실검색 기반 Q-Form 첨부 반환 스모크 검증.

기존 Q-Form 검증은 실제 ``attachments.collect()`` 를 사용하지만 검색 hits는 고정한다.
이 스크립트는 로컬 서비스 인덱스를 ``rag.Searcher`` 로 직접 검색한 뒤,
``chain.answer_in_scope()`` 의 첨부 반환까지 연결되는지 확인한다.

정답 파일명 목록은 사용하지 않는다. 대신 다음 파이프라인 불변조건만 검증한다.

* 생성 LLM은 스텁 1회만 호출하고 검색은 실제 ``Searcher`` 를 사용한다.
* chain 반환 첨부는 같은 hits에 ``attachments.collect(..., qform=slots)`` 를
  적용한 결과와 동일하다.
* Q-Form은 검색으로 얻은 baseline 첨부를 추가하지 않고 부분집합으로 좁힌다.
* 슬롯이 없거나 ``sub_task`` 가 없으면 baseline을 그대로 유지한다.
* 반환 파일은 중복이 없고 모두 로컬에서 다운로드 가능한 실파일이다.

실행: python chatbot/verify_qform_search_attachments.py
"""
from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
for path in (ROOT / "chatbot", ROOT / "crawler"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import attachments  # noqa: E402
import chain  # noqa: E402
import qform_state  # noqa: E402
from rag import Searcher  # noqa: E402


QUERY = "미성년자 자녀를 대신해서 착오송금 반환 신청할 때 필요한 서류"
BUSINESS_FUNCTION = "착오송금 반환 신청"
QFORM = {
    "party": "송금인",
    "sub_task": "반환신청",
    "qualification": "대리인",
    "subject": "미성년자",
    "method": None,
}
EMPTY_QFORM = {field: None for field in QFORM}
RETRIEVAL_QUERY = f"{QUERY}\n\n{qform_state.serialize(QFORM)}"


def attachment_key(item: dict) -> tuple[str | None, str | None]:
    return item.get("doc_id"), item.get("orig_filename")


class TrackingSearcher:
    """실제 Searcher 호출을 그대로 위임하고 검증에 필요한 hits만 보존한다."""

    def __init__(self, inner: Searcher):
        self.inner = inner
        self.calls: list[dict] = []

    def search(self, query: str, *args, **kwargs) -> list[dict]:
        hits = self.inner.search(query, *args, **kwargs)
        self.calls.append({"query": query, "args": args, "kwargs": dict(kwargs), "hits": hits})
        return hits


llm_calls = 0
llm_messages: list[list[dict]] = []


def stub_llm(messages: list[dict], req_id: str, params=None, **_kwargs):
    """외부 API를 호출하지 않고 chain의 생성 후단만 통과시킨다."""
    del req_id, params
    global llm_calls
    llm_calls += 1
    llm_messages.append(messages)
    return "검색 근거를 확인했습니다. [출처1]", {
        "provider": "stub",
        "model": "stub",
        "model_status": 200,
        "latency_ms": 0,
        "error": None,
    }


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []
    tracker = TrackingSearcher(
        Searcher(index_dir=str(ROOT / "crawler" / "data" / "index"))
    )

    # chain의 실제 검색 경로는 유지하고 외부 생성 호출만 차단한다.
    original_searcher, original_llm = chain._searcher, chain._llm
    chain._searcher, chain._llm = tracker, stub_llm
    try:
        result = chain.answer_in_scope(
            QUERY,
            k=10,
            qform=dict(QFORM),
            bf=BUSINESS_FUNCTION,
            retrieval_query=RETRIEVAL_QUERY,
        )
    finally:
        chain._searcher, chain._llm = original_searcher, original_llm

    retrieval_calls = [
        call for call in tracker.calls if call["kwargs"].get("mode") == "hybrid_bf"
    ]
    check(len(retrieval_calls) == 1, "hybrid_bf 검색이 정확히 1회여야 함", failures)
    check(llm_calls == 1, "생성 LLM 스텁이 정확히 1회 호출되어야 함", failures)
    if not retrieval_calls:
        print("실패 ⛔\n- " + "\n- ".join(failures))
        return 1

    hits = retrieval_calls[0]["hits"]
    baseline = attachments.collect(hits)
    expected = attachments.collect(hits, qform=QFORM)
    returned = result.get("attachments") or []

    base_keys = [attachment_key(item) for item in baseline]
    returned_keys = [attachment_key(item) for item in returned]

    check(bool(hits), "실검색 hits가 비어 있음", failures)
    check(retrieval_calls[0]["query"] == RETRIEVAL_QUERY,
          "실제 Searcher에 구조화된 검색 질의가 전달되지 않음", failures)
    check(bool(baseline), "실검색 결과에서 첨부 baseline을 찾지 못함", failures)
    check(bool(returned), "Q-Form 적용 후 반환 첨부가 비어 있음", failures)
    check(returned == expected, "chain 반환 첨부와 collect(hits, qform) 결과가 다름", failures)
    check(set(returned_keys) <= set(base_keys), "Q-Form이 baseline에 없는 첨부를 추가함", failures)
    check(len(returned) < len(baseline), "검증 시나리오에서 Q-Form이 첨부를 좁히지 못함", failures)
    check(len(returned_keys) == len(set(returned_keys)), "반환 첨부에 중복이 있음", failures)
    check(
        attachments.collect(hits, qform=None) == baseline
        and attachments.collect(hits, qform=EMPTY_QFORM) == baseline,
        "슬롯 없음/sub_task 없음 경로가 baseline을 보존하지 못함",
        failures,
    )
    check(
        all(
            item.get("available") is True
            and item.get("abs_path")
            and pathlib.Path(item["abs_path"]).is_file()
            for item in returned
        ),
        "반환 첨부 중 로컬에서 다운로드할 수 없는 파일이 있음",
        failures,
    )
    check(result.get("route") == "rag", "answer_in_scope 결과 route가 rag가 아님", failures)
    check(result.get("_meta", {}).get("qform") == QFORM, "chain 메타에 Q-Form 슬롯이 보존되지 않음", failures)
    check(result.get("_meta", {}).get("original_query") == QUERY,
          "chain 메타에 사용자 원문이 보존되지 않음", failures)
    check(result.get("_meta", {}).get("retrieval_query") == RETRIEVAL_QUERY,
          "chain 메타에 실제 검색 질의가 보존되지 않음", failures)
    check(bool(llm_messages) and llm_messages[0][1]["content"].endswith(f"[질문]\n{QUERY}"),
          "생성 프롬프트의 질문이 사용자 원문과 다름", failures)

    print("실검색 기반 Q-Form 첨부 반환 스모크")
    print(f"- Searcher hits: {len(hits)}청크")
    print(f"- baseline: {len(baseline)}파일")
    print(f"- Q-Form 적용 후: {len(returned)}파일")
    print(f"- 로컬 실파일: {sum(1 for item in returned if item.get('available'))}/{len(returned)}")
    if failures:
        print("실패 ⛔\n- " + "\n- ".join(failures))
        return 1
    print("전체 통과 ✅ (외부 LLM 호출 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
