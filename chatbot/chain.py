"""chain.py — answer() 4필드 + LLM 질문 분류 라우팅 (07-22 route 세션).

계약(임시 동결, DECISIONS.md 07-22): answer(query) -> {text, sources, confidence, route}
  - 4필드 축소 금지 · 부가(checks/_meta/attachments)만 추가 가능. route 내부 구현만 교체 가능.
  - attachments(부가): 근거 문서 첨부 목록(청크 태깅 우선 + 문서 폴백, attachments.collect).
    검색 hits만 소비 → LLM 추가 콜 0. reject 경로는 []. 스키마는 attachments.py._fmt 참조.
  - 새 흐름: **분류(1콜) → [소관밖] 고정 거절 문구 즉시 반환(검색·생성·검증 생략)
    / [정상·모호] 검색 → 생성(1콜) → 검증**. 분류 라벨·사유는 _meta에 기록.
  - confidence: 표시용 dense 코사인 top1("관련 문서 유사도" — 정책 분기 금지, Q12).
    reject 경로는 검색 생략이므로 0.0 고정.
  - 분류 JSON 파싱 실패 시 1회 재시도, 재실패는 안전 기본값 "정상"(과차단 방지) + _meta 기록.
  - CALL_BUDGET=70 (07-22 route 세션, 재시도 포함) — 소진 시 즉시 중단.

프롬프트 v2(생성) 근거: 전야 Q3 근거 이탈·URL 날조 → 규칙 1·2·3, Q1 롤렛 '과거' 한정
탈락 → 규칙 4, Q6 백만원 단위 오환산 → 규칙 5. (밤1 관통 실측 유지)

사용:
  python3 chatbot/chain.py               # 관통 3문항(정상·트랩·롤렛) — 새 흐름 데모
  python3 chatbot/chain.py cls "질문"    # 분류만 1건 (1~2콜)
  python3 chatbot/chain.py smoke        # T1 분류 스모크 3문항 (3콜)
  python3 chatbot/chain.py e2e          # T3 트랩셋 20문항 E2E → exp/route_e2e_results.jsonl
  python3 chatbot/chain.py clsdemo      # T4 정상 6문항 분류만 (6콜)
"""
import json
import os
import pathlib
import re
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
sys.dont_write_bytecode = True

import requests
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "crawler"))
sys.path.insert(0, str(ROOT / "chatbot"))
if str(ROOT / "admin") not in sys.path:
    sys.path.append(str(ROOT / "admin"))
load_dotenv(ROOT / ".env")  # 키 값은 어떤 로그·에러에도 싣지 않는다

import answer_checks
import attachments  # 근거 문서 첨부 조회(청크 태깅 우선 + 문서 폴백) — 순수 로컬, 계약 부가 필드
import guards  # 승인된 최신성 정정 규칙 — 검색 뒤 조건부 프롬프트 주입

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "hcx").strip().lower()
SUPPORTED_LLM_PROVIDERS = {"hcx", "deepseek", "upstage"}
if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
    raise ValueError("LLM_PROVIDER는 'hcx', 'deepseek', 'upstage' 중 하나여야 합니다.")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_URL = os.environ.get(
    "DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"
).strip()
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "").strip()
UPSTAGE_API_URL = os.environ.get(
    "UPSTAGE_API_URL", "https://api.upstage.ai/v1/chat/completions"
).strip()
UPSTAGE_MODEL = os.environ.get("UPSTAGE_MODEL", "solar-pro3").strip()
HCX_API_KEY = os.environ.get("CLOVA_API_KEY", "").strip()
HCX_API_URL = os.environ.get("CLOVA_API_URL", "").strip()
HCX_MODEL = os.environ.get("CLOVA_MODEL", "HCX-003").strip()
MODEL_NAME = {"hcx": HCX_MODEL, "deepseek": DEEPSEEK_MODEL,
              "upstage": UPSTAGE_MODEL}[LLM_PROVIDER]

GEN_PARAMS = {
    "temperature": 0.2, "top_p": 0.8, "max_tokens": 512,
    "thinking": {"type": "disabled"},
}  # 짧은 RAG 답변 — 지연과 재현성을 위해 비사고 모드
CLS_PARAMS = {
    "temperature": 0.1, "top_p": 0.8, "max_tokens": 128,
    "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"},
}  # 분류 — DeepSeek JSON Output 사용
CALL_BUDGET = 70  # 07-22 route 세션 예산(재시도 포함) — chatbot/CLAUDE.md v3 금지 5항
CONTEXT_K = 5  # 답변에 넣는 검색 청크 수 — 관리자 설정에서 다음 질의부터 변경 가능

# 답변 검증 게이트 — 관리자 설정이 ``admin/settings.py``를 통해 런타임에 주입한다.
# 규칙 판정 자체는 LLM 0콜이며, regenerate 모드만 실패 시 답변 생성 콜을 추가한다.
ANSWER_CHECKS_ENABLED = True
ANSWER_GATE_MODE = "warn"              # warn | regenerate | block
ANSWER_GATE_MAX_RETRIES = 1
CHECK_URLS_ENABLED = True
CHECK_CITATIONS_ENABLED = True
CHECK_NUMBERS_ENABLED = True
STRICT_URL = True
GUARDS_ENABLED = True
ANSWER_GATE_BLOCK_TEXT = (
    "죄송합니다. 생성된 답변이 근거 검증을 통과하지 못해 표시하지 않았습니다. "
    "질문을 조금 더 구체적으로 바꾸거나 공식 안내 문서를 확인해 주세요."
)
_calls = 0

SYS_PROMPT_V2 = (
    "너는 예금보험공사(KDIC) 안내 챗봇이다. 아래 [참고문서]와, 제공된 경우 "
    "[관리자 정정 사실]에만 근거해서 답하라.\n"
    "규칙:\n"
    "1. 참고문서와 관리자 정정 사실에 없는 내용은 답하지 말고 "
    "\"안내 문서에서 확인되지 않는 내용입니다\"라고 말하라. "
    "알고 있는 지식으로 보충하지 마라.\n"
    "2. URL·전화번호는 참고문서에 적힌 것만 그대로 옮겨라. 새 URL을 만들지 마라.\n"
    "3. 참고문서에 근거한 문장은 [출처N], 관리자 정정에 근거한 문장은 [관리자 정정]을 "
    "문장 끝에 표기하라. 근거 표시 없이 서술하지 마라.\n"
    "4. 참고문서의 서술이 과거형(\"과거에는\")이거나 조건부(\"~인 경우\")면 그 한정을 그대로 유지하라. "
    "현재 사실로 바꾸지 마라.\n"
    "5. 금액·수치는 근거 자료의 표기 그대로 적어라. 단위 환산을 하지 마라.\n"
    "6. [관리자 정정 사실]이 참고문서와 충돌하면 관리자 정정을 우선하고 해당 문장 끝에 "
    "[관리자 정정]을 붙여라. (답변 보류) 항목은 그 안내만 전달하고 충돌하는 문서 내용은 답하지 마라."
)

# 분류 프롬프트 — 트랩셋 문항 원문 인용 금지(과적합 방지), 소관 업무의 일반 서술만 사용.
# 수정 이력: v1 초안 (07-22 route 세션 — 수정권 1회 미사용)
CLS_PROMPT = (
    "너는 예금보험공사(KDIC) 안내 챗봇의 질문 분류기다. 사용자 질문 1건을 아래 3분류 중 하나로 판정한다.\n\n"
    "[정상] — 예금보험공사 소관 업무에 대한 질문. 소관 업무: 예금자보호제도(국내 부보금융회사 예금의 "
    "보호 대상·보호한도), 예금보험금·개산지급금·가지급금의 지급과 신청, 고객 미수령금 조회·신청, "
    "착오송금 반환지원, 부실관련자 은닉재산 신고와 포상금, 부실 금융회사 관련 채무조정·신용회복지원.\n\n"
    "[모호] — 소관 업무와 관련돼 보이나 판단이 어려운 질문. 두 업무를 섞어 물었거나, 업무 경계가 "
    "불분명하거나, 특정 수치·규정이 지금도 맞는지 확인하는 질문.\n\n"
    "[소관밖] — 예금보험공사 소관이 아닌 질문. 외국의 예금보호 제도나 외국 소재 금융기관의 예금, "
    "국내은행 해외지점에 맡긴 예금, 타기관 소관 업무(세금·환급은 국세청, 보이스피싱 피해구제는 "
    "금융감독원·경찰, 투자 손실 보상은 해당 없음, 전세보증금 보증은 HUG 등, 휴면예금은 서민금융진흥원), "
    "금융과 무관한 일반 질문.\n\n"
    "판단이 서지 않으면 \"모호\"를 택한다(\"소관밖\" 단정은 확실할 때만).\n\n"
    "출력 규칙: 아래 형식의 JSON 한 개만 출력한다. 백틱·코드블록·설명·머리말을 붙이지 마라.\n"
    "{\"label\": \"정상\" 또는 \"모호\" 또는 \"소관밖\", \"reason\": \"판정 사유 한 줄\"}"
)

# 고정 거절 문구 — answer_checks._is_rejection() 매칭 필수(T2에서 0콜 검증). URL·전화번호 금지.
REJECT_TEXT = "죄송합니다. 해당 내용은 예금보험공사 소관이 아니거나 안내 문서에서 확인되지 않는 내용입니다."

_searcher = None


def get_searcher():
    global _searcher
    if _searcher is None:
        from rag import Searcher
        _searcher = Searcher(index_dir=str(ROOT / "crawler" / "data" / "index"))
    return _searcher


def _provider_settings(provider: str) -> tuple[str, str, str]:
    """provider -> (api_key, api_url, model). 비밀값은 호출부 밖으로 기록하지 않는다."""
    if provider == "deepseek":
        return DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
    if provider == "upstage":
        return UPSTAGE_API_KEY, UPSTAGE_API_URL, UPSTAGE_MODEL
    if provider == "hcx":
        return HCX_API_KEY, HCX_API_URL, HCX_MODEL
    raise ValueError(f"지원하지 않는 LLM provider: {provider!r}")


def set_llm_provider(provider: str) -> str:
    """관리자 런타임 설정으로 기본 LLM과 표시 모델명을 함께 전환한다."""
    global LLM_PROVIDER, MODEL_NAME
    selected = str(provider).strip().lower()
    if selected not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(f"지원하지 않는 LLM provider: {selected!r}")
    LLM_PROVIDER = selected
    MODEL_NAME = _provider_settings(selected)[2]
    return MODEL_NAME


def _request_parts(provider: str, messages: list[dict], req_id: str,
                   params: dict, attempt: int) -> tuple[dict, dict]:
    """공통 파라미터를 각 공급자의 요청 스키마로 변환한다."""
    api_key, _api_url, model = _provider_settings(provider)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if provider in {"deepseek", "upstage"}:
        compatible = dict(params)
        if provider == "upstage":
            # 공식 Chat Completions 예시 범위만 보낸다. DeepSeek 전용 thinking과
            # 분류용 response_format은 프롬프트 기반 JSON 파싱으로 대체한다.
            compatible.pop("thinking", None)
            compatible.pop("response_format", None)
        return headers, {"model": model, "messages": messages,
                         "stream": False, **compatible}

    # CLOVA Studio는 모델명이 URL에 포함되고 파라미터가 camelCase다.
    headers["X-NCP-CLOVASTUDIO-REQUEST-ID"] = f"{req_id}-t{attempt}"
    payload = {"messages": messages}
    key_map = {"max_tokens": "maxTokens", "top_p": "topP"}
    for key, value in params.items():
        if key in {"thinking", "response_format", "stream"}:
            continue
        payload[key_map.get(key, key)] = value
    return headers, payload


def _response_content(provider: str, data: dict) -> str:
    if provider in {"deepseek", "upstage"}:
        return data["choices"][0]["message"]["content"]
    return data["result"]["message"]["content"]


def _llm(messages: list[dict], req_id: str, params: dict = GEN_PARAMS, *,
         provider: str | None = None) -> tuple[str | None, dict]:
    """선택한 LLM을 호출한다. 실패 시 1회 재시도하며 비밀값은 기록하지 않는다."""
    global _calls
    provider = (provider or LLM_PROVIDER).strip().lower()
    api_key, api_url, model = _provider_settings(provider)
    meta = {"provider": provider, "model": model, "model_status": None,
            "latency_ms": None, "error": None}
    if not api_key or not api_url:
        meta["error"] = f"missing_{provider}_configuration"
        return None, meta
    for attempt in (1, 2):
        if _calls >= CALL_BUDGET:
            meta["error"] = "call_budget_exhausted"
            return None, meta
        _calls += 1
        t0 = time.time()
        try:
            headers, payload = _request_parts(provider, messages, req_id, params, attempt)
            r = requests.post(api_url, json=payload, timeout=30, headers=headers)
            meta["latency_ms"] = int((time.time() - t0) * 1000)
            meta["model_status"] = r.status_code
            if r.status_code == 200:
                return _response_content(provider, r.json()), meta
            meta["error"] = f"http_{r.status_code}:" + r.text[:200].replace("\n", " ")
        except Exception as e:
            meta["latency_ms"] = int((time.time() - t0) * 1000)
            meta["error"] = f"exception:{type(e).__name__}"
        time.sleep(5 if meta["model_status"] == 429 else 2)
    return None, meta


def _deepseek(messages: list[dict], req_id: str,
              params: dict = GEN_PARAMS) -> tuple[str | None, dict]:
    """실험·호환용 명시적 DeepSeek 호출."""
    return _llm(messages, req_id, params, provider="deepseek")


def _hcx(messages: list[dict], req_id: str,
         params: dict = GEN_PARAMS) -> tuple[str | None, dict]:
    """실험·호환용 명시적 HCX 호출."""
    return _llm(messages, req_id, params, provider="hcx")


def _upstage(messages: list[dict], req_id: str,
             params: dict = GEN_PARAMS) -> tuple[str | None, dict]:
    """실험·호환용 명시적 Upstage 호출."""
    return _llm(messages, req_id, params, provider="upstage")


def _parse_cls(text: str | None) -> dict | None:
    """분류 응답에서 JSON 1개 추출. 라벨 3값 검증 실패 시 None."""
    if not text:
        return None
    m = re.search(r"\{.*?\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError):
        return None
    if d.get("label") in ("정상", "모호", "소관밖"):
        return {"label": d["label"], "reason": str(d.get("reason", ""))[:200]}
    return None


def classify(query: str) -> tuple[str, str, dict]:
    """LLM 질문 분류 (기본 1콜). JSON 파싱 실패 시 1회 재시도, 재실패는 안전 기본값 '정상'.

    반환: (label, reason, meta) — meta에 콜 수·파싱 실패 횟수·지연 기록.
    """
    global _calls
    messages = [{"role": "system", "content": CLS_PROMPT}, {"role": "user", "content": query}]
    meta = {"cls_calls": 0, "cls_parse_fail": 0, "cls_latency_ms": 0, "cls_error": None}
    for _ in (1, 2):  # 파싱 실패 재시도 1회(HTTP 재시도는 _llm 내부에서 별도)
        c0 = _calls
        text, m = _llm(messages, req_id="cls", params=CLS_PARAMS)
        meta["cls_calls"] += _calls - c0
        meta["cls_latency_ms"] += m["latency_ms"] or 0
        meta["cls_error"] = m["error"]
        parsed = _parse_cls(text)
        if parsed:
            return parsed["label"], parsed["reason"], meta
        if text is not None:
            meta["cls_parse_fail"] += 1
        if m["error"] == "call_budget_exhausted":
            break
    return "정상", "분류 실패 — 안전 기본값(과차단 방지)", meta


def _route(label: str) -> str:
    """분류 라벨 → 라우트 매핑 (07-22 확정: 소관밖→reject, 정상·모호→rag).

    "link"는 미구현 훅 유지 — 타기관 안내 URL 목록 확보 후 소관밖 세분화 예정.
    """
    return "reject" if label == "소관밖" else "rag"


def _run_answer_checks(text: str | None, hits: list[dict], *, allowed_numbers=None,
                       admin_correction_allowed: bool = False) -> dict:
    """현재 런타임 설정으로 규칙 검증. 이 함수 자체는 답변을 바꾸지 않는다."""
    if text is None:
        return {"ok": False, "flags": ["생성 실패 — 검증 생략"], "results": {}}
    if not ANSWER_CHECKS_ENABLED:
        return {"ok": True, "flags": [], "results": {}, "skipped": "관리자 설정으로 비활성화"}
    return answer_checks.run_all(
        text,
        hits,
        allow_context_urls=not STRICT_URL,
        check_urls_enabled=CHECK_URLS_ENABLED,
        check_citations_enabled=CHECK_CITATIONS_ENABLED,
        check_numbers_enabled=CHECK_NUMBERS_ENABLED,
        allowed_numbers=allowed_numbers,
        admin_correction_allowed=admin_correction_allowed,
    )


def _set_gate(checks: dict, *, action: str, attempts: int, mode: str,
              retry_error: str | None = None) -> dict:
    checks = dict(checks)
    checks["gate"] = {
        "enabled": bool(ANSWER_CHECKS_ENABLED),
        "mode": mode,
        "action": action,
        "generation_attempts": attempts,
        "retries": max(0, attempts - 1),
        "retry_error": retry_error,
    }
    return checks


def _generate_with_gate(messages: list[dict], hits: list[dict], req_id: str, *,
                        allowed_numbers=None, admin_correction_allowed: bool = False):
    """답변 생성 → 규칙 검증 → 관리자 정책 적용.

    ``regenerate``는 실패 플래그를 모델에 돌려주고 전체 답변을 다시 쓰게 한다.
    재시도까지 실패하면 마지막 생성 답변을 경고 상태로 반환한다. 차단은 명시적으로
    ``block``을 선택했을 때만 수행해 규칙 기반 오탐이 곧바로 사용자 답변을 없애지 않게 한다.
    """
    text, meta = _llm(messages, req_id=req_id)
    attempts = 1
    total_latency = meta.get("latency_ms") or 0
    checks = _run_answer_checks(
        text, hits, allowed_numbers=allowed_numbers,
        admin_correction_allowed=admin_correction_allowed,
    )
    mode = ANSWER_GATE_MODE if ANSWER_GATE_MODE in {"warn", "regenerate", "block"} else "warn"

    if text is None:
        checks = _set_gate(checks, action="generation_failed", attempts=attempts, mode=mode)
    elif not ANSWER_CHECKS_ENABLED:
        checks = _set_gate(checks, action="disabled", attempts=attempts, mode=mode)
    elif checks["ok"]:
        checks = _set_gate(checks, action="passed", attempts=attempts, mode=mode)
    elif mode == "block":
        text = ANSWER_GATE_BLOCK_TEXT
        checks = _set_gate(checks, action="blocked", attempts=attempts, mode=mode)
    elif mode == "regenerate":
        retry_error = None
        for retry in range(1, max(0, int(ANSWER_GATE_MAX_RETRIES)) + 1):
            flags = "\n".join(f"- {flag}" for flag in checks.get("flags") or [])
            correction = {
                "role": "user",
                "content": (
                    "[자동 검증 결과]\n"
                    f"{flags}\n\n"
                    "위 위반을 모두 고쳐 답변 전체를 다시 작성하라. 참고문서와 관리자 정정 사실 밖의 "
                    "정보는 넣지 말고, 근거에 따라 [출처N] 또는 [관리자 정정]을 붙여라. "
                    "검증 결과나 수정 과정을 설명하지 마라."
                ),
            }
            retry_messages = [*messages, {"role": "assistant", "content": text}, correction]
            revised, retry_meta = _llm(retry_messages, req_id=f"{req_id}-gate-{retry}")
            attempts += 1
            total_latency += retry_meta.get("latency_ms") or 0
            meta = retry_meta
            if revised is None:
                retry_error = retry_meta.get("error") or "generation_failed"
                break
            text = revised
            checks = _run_answer_checks(
                text, hits, allowed_numbers=allowed_numbers,
                admin_correction_allowed=admin_correction_allowed,
            )
            if checks["ok"]:
                checks = _set_gate(
                    checks, action="regenerated", attempts=attempts, mode=mode
                )
                break
        else:
            retry_error = None
        if "gate" not in checks:
            checks = _set_gate(
                checks,
                action="regenerate_exhausted",
                attempts=attempts,
                mode=mode,
                retry_error=retry_error,
            )
    else:
        checks = _set_gate(checks, action="warned", attempts=attempts, mode=mode)

    meta = dict(meta)
    meta["latency_ms"] = total_latency
    meta["generation_attempts"] = attempts
    meta["validation_retries"] = max(0, attempts - 1)
    meta["answer_gate_mode"] = mode
    meta["answer_gate_action"] = checks["gate"]["action"]
    return text, meta, checks


def _reject_result(label: str, reason: str, cls_meta: dict, k: int,
                   query: str, retrieval_query: str,
                   qform_retrieval_mode: str = "off") -> dict:
    """reject 경로 반환 조립 — 검색·생성·검증 생략. 계약 4필드 + checks/_meta 완비(T2 검증 대상)."""
    return {
        "text": REJECT_TEXT,
        "sources": [],
        "confidence": 0.0,
        "route": "reject",
        "checks": {"ok": True, "flags": [], "skipped": "고정 거절 문구",
                   "gate": {"enabled": bool(ANSWER_CHECKS_ENABLED),
                            "mode": ANSWER_GATE_MODE, "action": "skipped_reject",
                            "generation_attempts": 0, "retries": 0,
                            "retry_error": None}},  # 모델 생성물 아님 — 검증 비대상
        "attachments": [],  # 소관 밖 — 반환 첨부 없음(계약 부가 필드)
        "_meta": {"model": MODEL_NAME, "cls_label": label, "cls_reason": reason, **cls_meta,
                  "latency_ms": cls_meta.get("cls_latency_ms"), "k": k,
                  "original_query": query, "retrieval_query": retrieval_query,
                  "retrieval_applied": False, "retrieval_boosted": False,
                  "qform_retrieval_mode": qform_retrieval_mode,
                  "qform_metadata_applied": False},
    }


def _resolve_k(k: int | None) -> int:
    """호출 시점의 런타임 기본값을 사용한다(함수 정의 시점에 5를 고정하지 않음)."""
    resolved = CONTEXT_K if k is None else int(k)
    if resolved < 1:
        raise ValueError("k는 1 이상이어야 합니다.")
    return resolved


def _generation_inputs(query: str, hits: list[dict], business: str | None = None):
    """검색 근거와 조건에 맞는 최신성 가드를 한 LLM 요청으로 조립한다."""
    context = "\n\n".join(
        f"[출처{i}] {h['page_title']}\n{h['text']}" for i, h in enumerate(hits, 1)
    )
    matched: list[dict] = []
    whitelist: set[str] = set()
    guard_error = None
    if GUARDS_ENABLED:
        try:
            business_scope = business or {
                h.get("business_function") for h in hits if h.get("business_function")
            }
            raw_context = "\n\n".join(h.get("text") or "" for h in hits)
            matched = guards.match(query, raw_context, business=business_scope)
            whitelist = guards.numeric_whitelist(matched)
            guard_block = guards.prompt_block(matched)
        except Exception as exc:
            # 가드 저장소 장애가 기본 RAG 답변까지 중단시키지 않도록 안전하게 미적용한다.
            matched, whitelist, guard_block = [], set(), ""
            guard_error = type(exc).__name__
    else:
        guard_block = ""

    sections = [f"[참고문서]\n{context}"]
    if guard_block:
        sections.append(guard_block)
    sections.append(f"[질문]\n{query}")
    messages = [
        {"role": "system", "content": SYS_PROMPT_V2},
        {"role": "user", "content": "\n\n".join(sections)},
    ]
    return messages, matched, whitelist, guard_error


def _record_guard_fires(matched: list[dict]) -> bool:
    """한 답변 요청에서 매칭된 가드의 발동 횟수를 한 번씩 기록한다."""
    if not matched:
        return False
    try:
        guards.bump_fired([g["id"] for g in matched])
        return True
    except Exception:
        return False


def _guard_meta(matched: list[dict], error: str | None, counter_recorded: bool) -> dict:
    return {
        "enabled": bool(GUARDS_ENABLED),
        "applied": bool(matched),
        "matched": [
            {"id": g.get("id"), "title": g.get("title"), "kind": g.get("kind")}
            for g in matched
        ],
        "counter_recorded": counter_recorded,
        "error": error,
    }


def answer(query: str, k: int | None = None, qform: dict | None = None, *,
           retrieval_query: str | None = None,
           qform_retrieval_mode: str = "off") -> dict:
    """계약 4필드 + 부가(checks/_meta). 분류 선행 — 소관밖은 검색·생성 없이 즉시 거절.

    qform(큐폼 슬롯 dict, 선택): 주어지면 첨부를 조합 조인으로 후단 필터(B안, §3-1).
    retrieval_query(선택): 검색과 검색 유사도에만 사용한다. 분류와 생성 프롬프트의
    질문은 항상 ``query`` 원문이며, 생략하면 기존처럼 원문으로 검색한다."""
    k = _resolve_k(k)
    search_query = retrieval_query if retrieval_query is not None else query
    label, reason, cls_meta = classify(query)
    route = _route(label)
    if route == "reject":
        return _reject_result(
            label, reason, cls_meta, k, query, search_query, qform_retrieval_mode
        )

    search_kwargs = ({"qform": qform}
                     if qform_retrieval_mode in {"metadata_soft", "field_value_soft"}
                     else {})
    hits = get_searcher().search(search_query, k=k, mode="hybrid_bf", **search_kwargs)
    messages, matched_guards, allowed_numbers, guard_error = _generation_inputs(query, hits)
    text, meta, checks = _generate_with_gate(
        messages, hits, req_id="chain", allowed_numbers=allowed_numbers,
        admin_correction_allowed=bool(matched_guards),
    )
    guard_counter_recorded = _record_guard_fires(matched_guards)

    sources, seen = [], set()
    for h in hits:
        if h["parent_doc_id"] not in seen:
            seen.add(h["parent_doc_id"])
            sources.append({"title": h["page_title"], "url": h["source_url"], "doc_id": h["parent_doc_id"]})

    # 근거 문서 첨부 조회 — 청크 태깅 우선, 없으면 문서 단위 폴백. 검색 hits만 사용(추가 콜 0).
    # qform 주어지면 조합 조인 후단 필터(B안). None이면 기존 동작 그대로.
    attach = attachments.collect(hits, qform=qform)
    return {
        "text": text,
        "sources": sources,
        "confidence": _confidence(search_query),
        "route": route,
        "checks": checks,           # 부가 필드(계약 외 추가 — 축소 아님)
        "attachments": attach,      # 부가 필드 — 근거 문서 첨부(다운로드용). 없으면 []
        "_meta": {"model": MODEL_NAME, "cls_label": label, "cls_reason": reason, **cls_meta,
                  **meta, "k": k, "qform": qform,
                  "original_query": query, "retrieval_query": search_query,
                  "retrieval_applied": True, "retrieval_boosted": search_query != query,
                  "qform_retrieval_mode": qform_retrieval_mode,
                  "qform_metadata_applied": bool(search_kwargs),
                  "guards": _guard_meta(matched_guards, guard_error, guard_counter_recorded),
                  "retrieval": _retrieval_meta(hits)},
    }


def answer_in_scope(query: str, k: int | None = None, qform: dict | None = None,
                    bf: str | None = None, *, retrieval_query: str | None = None,
                    qform_retrieval_mode: str = "off") -> dict:
    """상단 6-BF 라우터가 IN으로 확정한 절만 검색·생성한다.

    OOS 분류를 다시 수행하지 않으며, ``bf``가 있으면 검색의 업무 부스트에도 같은 값을
    전달한다. ``retrieval_query`` 는 검색에만 쓰고 생성 질문은 ``query`` 원문을 유지한다.
    이 함수 자체에는 BF/OOS 임계값이 없다.
    """
    k = _resolve_k(k)
    search_query = retrieval_query if retrieval_query is not None else query
    search_kwargs = ({"qform": qform}
                     if qform_retrieval_mode in {"metadata_soft", "field_value_soft"}
                     else {})
    hits = get_searcher().search(
        search_query, k=k, mode="hybrid_bf", bf_override=bf, **search_kwargs
    )
    messages, matched_guards, allowed_numbers, guard_error = _generation_inputs(
        query, hits, business=bf,
    )
    text, meta, checks = _generate_with_gate(
        messages, hits, req_id="chain-in", allowed_numbers=allowed_numbers,
        admin_correction_allowed=bool(matched_guards),
    )
    guard_counter_recorded = _record_guard_fires(matched_guards)

    sources, seen = [], set()
    for h in hits:
        if h["parent_doc_id"] not in seen:
            seen.add(h["parent_doc_id"])
            sources.append({"title": h["page_title"], "url": h["source_url"],
                            "doc_id": h["parent_doc_id"]})
    attach = attachments.collect(hits, qform=qform)
    return {
        "text": text, "sources": sources, "confidence": _confidence(search_query), "route": "rag",
        "checks": checks, "attachments": attach,
        "_meta": {"model": MODEL_NAME, "cls_label": bf, "cls_reason": "상단 6-BF 라우터 확정",
                  "cls_calls": 0, "cls_parse_fail": 0, "cls_latency_ms": 0,
                  **meta, "k": k, "qform": qform, "business_function": bf,
                  "original_query": query, "retrieval_query": search_query,
                  "retrieval_applied": True, "retrieval_boosted": search_query != query,
                  "qform_retrieval_mode": qform_retrieval_mode,
                  "qform_metadata_applied": bool(search_kwargs),
                  "guards": _guard_meta(matched_guards, guard_error, guard_counter_recorded),
                  "retrieval": _retrieval_meta(hits)},
    }


def _retrieval_meta(hits: list[dict]) -> list[dict]:
    """오류 재현용 최소 검색 기록. 원문 전체 대신 짧은 발췌와 점수만 남긴다."""
    out = []
    for rank, h in enumerate(hits, 1):
        try:
            score = float(h.get("_score")) if h.get("_score") is not None else None
        except (TypeError, ValueError):
            score = None
        out.append({"rank": rank, "score": score, "chunk_id": h.get("chunk_id"),
                    "doc_id": h.get("parent_doc_id"), "title": h.get("page_title"),
                    "url": h.get("source_url"),
                    "qform_boost": h.get("_qform_boost", 0.0),
                    "qform_matches": h.get("_qform_matches", []),
                    "text_excerpt": str(h.get("text") or "")[:500]})
    return out


def _confidence(query: str) -> float:
    """표시용 confidence — dense 코사인 top1 (T2 추천). 정책 분기에 쓰지 말 것(Q12)."""
    d1 = get_searcher().search(query, k=1, mode="dense")
    return round(float(d1[0]["_score"]), 4) if d1 else 0.0


def _print_calls() -> None:
    print(f"[calls] 이번 실행 {LLM_PROVIDER} 콜(재시도 포함): {_calls} / 예산 {CALL_BUDGET}")


# ── 실행 모드 (T1 스모크 · T3 E2E · T4 정상 분류) ───────────────────────
def run_cls_one(query: str) -> None:
    label, reason, meta = classify(query)
    print(f"[cls] {query}\n  → {label} ({reason})  콜 {meta['cls_calls']} · 파싱실패 {meta['cls_parse_fail']} · {meta['cls_latency_ms']}ms")


def run_smoke() -> None:
    """T1 분류 스모크 — 트랩셋·데모셋 밖 신규 3문항(기대: 정상/소관밖/모호)."""
    for expect, q in [("정상", "예금자보호제도란 무엇인가요?"),
                      ("소관밖", "자동차 보험료 할인은 어디에 문의해야 하나요?"),
                      ("모호", "예금 이자에 붙는 세금은 얼마인가요?")]:
        label, reason, meta = classify(q)
        mark = "일치" if label == expect else f"불일치(기대 {expect})"
        print(f"[smoke] {q}\n  → {label} [{mark}] ({reason})  콜 {meta['cls_calls']} · 파싱실패 {meta['cls_parse_fail']}")
    _print_calls()


def run_e2e() -> None:
    """T3 — 트랩셋 20문항 전부 answer() E2E → exp/route_e2e_results.jsonl."""
    traps = [json.loads(l) for l in (ROOT / "exp" / "trapset_v0.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out_path = ROOT / "exp" / "route_e2e_results.jsonl"
    global _calls
    rows = []
    for i, t in enumerate(traps, 1):
        c0 = _calls
        t0 = time.time()
        r = answer(t["query"])
        m = r["_meta"]
        rows.append({
            "id": i, "query": t["query"], "expected_route": t["expected_route"],
            "cls_label": m.get("cls_label"), "cls_reason": m.get("cls_reason"),
            "route": r["route"], "text": r["text"],
            "checks_flags": r["checks"]["flags"],
            "llm_calls_this_q": _calls - c0,
            "latency_ms": int((time.time() - t0) * 1000),
            # 부가(분석용)
            "trap_type": t["trap_type"], "cls_parse_fail": m.get("cls_parse_fail", 0),
            "confidence": r["confidence"],
        })
        print(f"  [{i:2d}/20] {t['trap_type']:7} 기대={t['expected_route']:7} → cls={m.get('cls_label')} route={r['route']}"
              f" 콜+{_calls - c0} (누계 {_calls})")
        time.sleep(0.5)
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    n_rej = sum(1 for r in rows if r["route"] == "reject")
    print(f"[e2e] {len(rows)}행 → {out_path.name} · reject {n_rej} / rag {len(rows) - n_rej}")
    _print_calls()


def run_clsdemo() -> None:
    """T4 — 전야 데모 정상 6문항(demo_results.jsonl rag 행, 읽기만) 분류만 실행."""
    demo = [json.loads(l) for l in (ROOT / "chatbot" / "demo_results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    queries = [r["query"] for r in demo if r["mode"] == "rag"]
    fp = 0
    for q in queries:
        label, reason, meta = classify(q)
        if label == "소관밖":
            fp += 1
        print(f"[정상문항] {q}\n  → {label} ({reason})")
    print(f"[clsdemo] 정상 6문항 중 소관밖 오분류(false positive): {fp}건")
    _print_calls()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "cls":
        run_cls_one(sys.argv[2] if len(sys.argv) > 2 else "예금자 보호 한도는 얼마인가요?")
        _print_calls()
    elif cmd == "smoke":
        run_smoke()
    elif cmd == "e2e":
        run_e2e()
    elif cmd == "clsdemo":
        run_clsdemo()
    elif cmd == "demo":
        for lab, q in [("정상", "예금보험금은 어떻게 신청하나요?"),
                       ("트랩(해외)", "미국 FDIC의 예금 보호한도는 얼마인가요?"),
                       ("롤렛(보호한도)", "예금자 보호 한도는 얼마인가요?")]:
            r = answer(q)
            print(f"══ [{lab}] {q}")
            print(f"   route={r['route']} (cls={r['_meta'].get('cls_label')}) · confidence={r['confidence']}"
                  f" · checks={'통과' if r['checks']['ok'] else r['checks']['flags']}")
            print(f"   답변: {r['text']}\n")
        _print_calls()
    else:
        sys.exit("사용법: python3 chatbot/chain.py [demo|cls \"질문\"|smoke|e2e|clsdemo]")
