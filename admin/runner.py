# -*- coding: utf-8 -*-
"""재빌드·평가 러너 — crawler 코드를 **수정하지 않고** 파라미터를 주입해 실행한다.

`jobs.py` 가 이 파일을 서브프로세스로 띄우고 stdout 의 마커를 읽어 진행률을 갱신한다.

    python runner.py --mode eval    --config '{"CHUNK_SIZE":800,...}'
    python runner.py --mode rebuild --config '{...}' --recrawl

왜 별도 러너인가
  · `crawler/chunk.py` 의 상수를 `setattr` 로 덮은 뒤 `pipeline.main()` 을 부른다.
    `pipeline` 이 `import chunk as chunk_mod` 로 **같은 모듈 객체**를 쓰므로 주입이 통한다.
    (`settings.apply_runtime()` 과 같은 방식 — 파일을 고치지 않는다.)
  · 평가는 **샌드박스 인덱스**(`data/index_eval`)에서 돌리고 끝나면 지운다.
    `rag.Store.build_and_save()` 가 `data/chunks.jsonl` 을 덮어쓰므로 그 파일도 백업·복원한다.

마커
    __STEP__ <이름>          단계 시작
    __RESULT__ <json>        최종 결과
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
import traceback
from datetime import datetime

ADMIN = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(os.environ.get("KDIC_REPO", ADMIN.parent)).resolve()
CRAWLER = REPO / "crawler"
BACKUP = ADMIN / "data" / "backup"

# 백업 대상 — build_and_save() 가 건드리는 산출물 전부
TARGETS = ["data/chunks.jsonl", "data/index"]
# 첨부 모드가 건드리는 것 — link_files.py 가 parsed 를 고쳐 쓴다.
# data/files 는 파일을 더하기만 하고 manifest 는 맨 끝에 한 번에 쓰므로 백업하지 않는다
# (중간에 죽어도 옛 manifest 가 그대로 남아 콘솔은 계속 동작한다).
FILE_TARGETS = ["data/parsed"]


def step(name: str) -> None:
    print(f"__STEP__ {name}", flush=True)


def _paths():
    return [(CRAWLER / t) for t in TARGETS]


def backup() -> pathlib.Path:
    """산출물 스냅샷. **같은 초에 두 번 불릴 수 있다** — 체인이 평가 직후 재빌드를
    시작하면 초 단위 타임스탬프가 겹쳐 `copytree` 가 FileExistsError 로 죽는다.
    그래서 이름을 유일하게 만들고, 복사도 덮어쓰기를 허용한다.
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst, n = BACKUP / ts, 1
    while dst.exists():
        n += 1
        dst = BACKUP / f"{ts}-{n}"
    dst.mkdir(parents=True, exist_ok=True)
    for p in _paths():
        if not p.exists():
            continue
        t = dst / p.name
        shutil.copytree(p, t, dirs_exist_ok=True) if p.is_dir() else shutil.copy2(p, t)
    # 오래된 백업 정리 — 최근 5개만 남긴다
    for old in sorted(BACKUP.iterdir(), reverse=True)[5:]:
        shutil.rmtree(old, ignore_errors=True)
    return dst


def restore(src: pathlib.Path) -> None:
    """백업에서 되돌린다. **삭제 후 복사가 아니라 덮어쓰기**다.

    지우기 권한이 없는 환경(마운트·읽기전용 부모)에서 `unlink()` 가 실패하면 복원 자체가
    무산된다. 파일은 그대로 덮어쓰고, 디렉터리는 `dirs_exist_ok` 로 합친다.
    """
    for p in _paths():
        b = src / p.name
        if not b.exists():
            continue
        if b.is_dir():
            p.mkdir(parents=True, exist_ok=True)
            for stale in p.iterdir():               # 백업에 없는 잔여물만 정리(실패해도 무시)
                if not (b / stale.name).exists():
                    try:
                        shutil.rmtree(stale) if stale.is_dir() else stale.unlink()
                    except OSError:
                        pass
            shutil.copytree(b, p, dirs_exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(b, p)                      # 덮어쓰기 — unlink 불필요


def _verify(src: pathlib.Path) -> dict:
    """복원이 실제로 됐는지 해시로 확인한다 — '복원했다'는 말만 믿지 않는다."""
    import hashlib
    out = {}
    for p in _paths():
        b = src / p.name
        if not b.exists() or b.is_dir() or not p.exists():
            continue
        h = lambda f: hashlib.sha1(f.read_bytes()).hexdigest()[:12]
        out[p.name] = {"ok": h(b) == h(p), "sha": h(p)}
    return out


def clamp_overlap(v: int) -> tuple[int, str | None]:
    """OVERLAP=0 방어.

    `chunk.py` 는 겹침을 `cur[-OVERLAP:]` 로 잘라 붙이는데, 파이썬에서 `s[-0:]` 는 빈
    문자열이 아니라 **문자열 전체**다. 그래서 0 은 '겹침 없음'이 아니라 '직전 누적분 통째
    복제'로 동작한다(실측: 179 → 195청크, 총 글자수 +18%, hit@5 0.7277 → 0.6942).
    원본을 고치지 않는 대신 주입 단계에서 1 로 올린다 — 1 자 겹침은 사실상 겹침 없음이다.
    """
    v = int(v)
    if v > 0:
        return v, None
    return 1, ("겹침 0은 코드상 '직전 조각 통째 복제'로 동작해 1자로 낮춰 실행합니다 "
               "(chunk.py 의 cur[-OVERLAP:] 는 0일 때 문자열 전체를 반환).")


def inject(cfg: dict, mods) -> dict:
    """chunk 모듈 상수 주입. 실제로 바뀐 값만 돌려준다(로그용)."""
    chunk_mod = mods["chunk"]
    applied = {}
    ov, warn = clamp_overlap(cfg.get("OVERLAP", 100))
    if warn:
        print(f"  ⚠ {warn}", flush=True)
    mapping = {
        "CHUNK_SIZE": int(cfg.get("CHUNK_SIZE", 800)),
        "OVERLAP": ov,
        "MIN_CHUNK": int(cfg.get("MIN_CHUNK", 60)),
        "TABLE_GAP_MAX": (int(cfg.get("TABLE_GAP_MAX", 12))
                          if cfg.get("TABLE_KEEP", True) else 0),
    }
    for k, v in mapping.items():
        if hasattr(chunk_mod, k):
            applied[k] = {"before": getattr(chunk_mod, k), "after": v}
            setattr(chunk_mod, k, v)
    if warn:
        applied["_warn"] = warn
    return applied


def run_pipeline(recrawl: bool) -> None:
    """pipeline.main() 을 인자만 바꿔 그대로 호출한다."""
    import pipeline
    argv = ["pipeline.py", "--manifest", "crawl_manifest.csv", "--rebuild"]
    if not recrawl:
        argv.insert(3, "--use-cache")
    old, sys.argv = sys.argv, argv
    try:
        pipeline.main()
    finally:
        sys.argv = old


# ── Q-Form 연결 ─────────────────────────────────────────────────────────
# 평가·재검증이 챗봇과 **같은 Q-Form 경로**를 타게 하는 부분이다. 이게 없으면
# `QFORM_RETRIEVAL_MODE` 를 무엇으로 두든 러너는 질문 원문만 넘겼고 `search()` 에
# `qform` 인자를 붙이지 않았다 — 콘솔에서 값을 바꿔도 지표가 한 자리도 안 움직이는
# 상태였다. `apply_search_settings()` 가 `rag.QFORM_META_BOOST` 를 주입해도
# 슬롯이 없으면 `_apply_qform_meta_boost()` 가 즉시 빈손으로 돌아온다.
QFORM_FIELDS = ("party", "sub_task", "qualification", "subject", "method")
QFORM_QUERY_MODES = {"field_value", "field_value_soft"}    # 검색문 field:value 확장
QFORM_SOFT_MODES = {"metadata_soft", "field_value_soft"}   # 청크 메타 가산
QFORM_OFF = {"mode": "off", "boost": 0.0, "scope": "msdr"}


def qform_settings() -> dict:
    """콘솔에 저장된 Q-Form 검색 설정. 콘솔을 못 읽어도 평가 자체는 돌아야 한다."""
    try:
        import settings as admin_settings
        cfg = admin_settings.current()
        return {"mode": str(cfg["QFORM_RETRIEVAL_MODE"]),
                "boost": float(cfg["QFORM_META_BOOST"]),
                "scope": str(cfg["QFORM_SCOPE"])}
    except Exception as e:                       # 콘솔 설정이 없으면 기존 동작(미반영)
        return {**QFORM_OFF, "error": f"{type(e).__name__}: {e}"}


def qform_slots(question: str, business_function: str | None, scope: str) -> dict:
    """평가 문항 → 사용자 슬롯. 챗봇과 **같은 결정론 추출기**(LLM 호출 0)를 쓴다.

    평가셋에는 슬롯 라벨이 없다. 사람이 손으로 붙이면 그 라벨 자체가 또 하나의 가정이
    되므로, 실제 대화에서 슬롯을 만드는 것과 같은 함수로 질문에서 뽑는다. 업무는
    평가셋의 `business_function` 을 그대로 넘긴다 — 인자를 생략하면 `extract()` 가
    내부 폴백 분류를 돌려서 라우터 유무에 따라 지표가 흔들린다.
    """
    import qform_extract
    got = qform_extract.extract(question, business_function, scope=scope)
    return {f: got[f] for f in QFORM_FIELDS if got.get(f)}


def qform_query(question: str, slots: dict, mode: str) -> tuple[str, dict]:
    """모드별 (검색문, `search()` 추가 인자). `qform_flow._finalize` 와 같은 규칙이다."""
    query, kwargs = question, {}
    if slots and mode in QFORM_QUERY_MODES:
        import qform_state
        extra = qform_state.serialize(slots)
        if extra:
            query = f"{question}\n\n{extra}"
    if slots and mode in QFORM_SOFT_MODES:
        kwargs["qform"] = dict(slots)
    return query, kwargs


def qform_coverage(index_dir: str) -> dict:
    """이 인덱스 청크에 `qform_meta` 가 실제로 붙어 있는가(콘솔 대시보드와 같은 계산)."""
    try:
        import metrics
        return metrics.qform_meta_coverage(pathlib.Path(index_dir) / "chunk_meta.jsonl")
    except Exception as e:
        return {"available": False, "error": f"{type(e).__name__}: {e}"}


def qform_warnings(qf: dict, cov: dict) -> list[str]:
    """설정은 켜져 있는데 실제로는 무동작인 조합을 잡아낸다."""
    warn = []
    if qf.get("error"):
        warn.append(f"콘솔 Q-Form 설정을 읽지 못해 미반영으로 돌립니다 ({qf['error']}).")
    if qf.get("mode") in QFORM_SOFT_MODES:
        if not cov.get("available"):
            warn.append("청크 메타를 읽지 못했습니다 — 메타 가산 효과를 확인할 수 없습니다.")
        elif not cov.get("keyed"):
            warn.append("인덱스 청크에 qform_meta 필드가 없습니다 — 재청킹해야 메타 가산이 동작합니다.")
        elif not cov.get("tagged"):
            warn.append("qform_meta 가 전부 비어 있습니다 — data/qform_combos_*.csv 를 확인하세요.")
        if float(qf.get("boost") or 0.0) <= 0:
            warn.append("QFORM_META_BOOST 가 0이라 메타 가산이 꺼져 있습니다.")
    return warn


def check_qform(index_dir: str, out: dict) -> dict:
    """`Q-Form 메타데이터 확인` 단계 본체 — 설정·태깅 현황·경고를 결과에 싣는다."""
    step("Q-Form 메타데이터 확인")
    qf = qform_settings()
    cov = qform_coverage(index_dir)
    warn = qform_warnings(qf, cov)
    out["qform_settings"] = qf
    out["qform_meta"] = cov
    out["qform_warnings"] = warn
    print(f"  Q-Form 반영 {qf['mode']} · 가산 {qf['boost']} · 슬롯 스코프 {qf['scope']}"
          f" · 태깅 {cov.get('tagged', 0)}/{cov.get('chunks', 0)}청크", flush=True)
    for w in warn:
        print(f"  ⚠ {w}", flush=True)
    return qf


def _anchor_hits(ev, gt_rows: list[dict], retrieved: list[dict],
                 chunk_meta: list[dict]) -> dict:
    """대조군 비교용 앵커 지표(판정 기준은 본 평가와 동일).

    `hit@5` 는 콘솔 전체가 쓰는 잣대라 반드시 같이 낸다. 다만 Q-Form 가산은 후보를
    새로 넣는 게 아니라 **이미 뽑힌 청크의 순위를 미는** 신호라, 효과가 먼저 나타나는
    자리는 1위다 — hit@5 만 보면 순위가 2→1로 올라도 0.0000 으로 보인다.
    """
    if not gt_rows or not retrieved:
        return {}
    res = ev.evaluate_retrieval(gt_rows, retrieved, chunk_meta,
                                score="anchor", id_fallback=False)
    a = res.get("anchor_level") or {}
    if not a.get("n_scored"):
        return {}
    return {"hit@1": round(a.get("hit@1", 0), 4), "hit@5": round(a.get("hit@5", 0), 4),
            "mrr@10": round(a.get("mrr", 0), 4), "n_scored": a["n_scored"]}


def _qform_report(ev, searcher, gt: list[dict], retrieved: list[dict],
                  chunk_meta: list[dict], slots_by_id: dict[str, dict],
                  qf: dict, boosted_hits: int) -> dict:
    """Q-Form이 이번 측정에서 무엇을 했는지 — 적용 범위와 **대조군 대비 효과**.

    대조군은 **슬롯이 잡힌 문항만** 다시 돌린다. 슬롯이 없는 문항은 두 경로의 검색
    입력이 글자 단위로 같아 결과도 정의상 같으므로, 전체를 두 번 돌리면 시간만 두 배
    쓰고 차이는 그 부분집합에서만 나온다. 전체 지표에 섞어 희석하지 않고 분모를
    적용 문항으로 밝혀 적는다.
    """
    mode = qf.get("mode", "off")
    fields = {f: 0 for f in QFORM_FIELDS}
    for slots in slots_by_id.values():
        for f in slots:
            fields[f] = fields.get(f, 0) + 1
    rep = {"mode": mode, "scope": qf.get("scope"), "boost": float(qf.get("boost") or 0.0),
           "n_questions": len(gt), "n_with_slots": len(slots_by_id),
           "slot_fields": fields, "boosted_hits": boosted_hits, "applied": None}
    if qf.get("error"):
        rep["error"] = qf["error"]
    if mode == "off" or not slots_by_id:
        return rep

    sub = [r for r in gt if r.get("id") in slots_by_id]
    by_id = {r["id"]: r for r in retrieved if r.get("id")}
    on = [by_id[r["id"]] for r in sub if r.get("id") in by_id]
    off = [{"id": r.get("id"),
            "retrieved_chunk_ids": [h["chunk_id"] for h in
                                    searcher.search(r["question"], k=10, mode="hybrid_bf")]}
           for r in sub]
    a_on = _anchor_hits(ev, sub, on, chunk_meta)
    a_off = _anchor_hits(ev, sub, off, chunk_meta)
    rep["applied"] = {"n": len(sub), "n_scored": a_on.get("n_scored"),
                      "on": a_on or None, "off": a_off or None,
                      "delta": {m: round(a_on[m] - a_off[m], 4)
                                for m in ("hit@1", "hit@5", "mrr@10")
                                if m in a_on and m in a_off} or None}
    return rep


def run_eval(index_dir: str, gt_name: str = "gt_testset_retrieval_450.jsonl",
             qform: dict | None = None) -> dict:
    """평가 함수를 직접 호출해 지표 dict 를 받는다 — 콘솔 문자열을 정규식으로 긁지 않는다.

    **판정은 앵커텍스트 전용이다**(`score="anchor"` · `id_fallback=False`). `gt_chunk_ids`
    는 특정 청킹에 대한 좌표라 재청킹하면 값이 변한다 — 그걸 지표로 쓰면 청크 파라미터를
    바꿀 때마다 수치가 검색 성능이 아니라 판정 방식 때문에 움직이고, 콘솔 ⑦탭이 그
    움직임을 '정확도 변화'로 표시한다. 그래서 `hit@k` · `mrr@10` 은 전부 앵커 판정값이다.
    chunk_id 판정값은 `chunk_hit@*` 로 따로 실어 감사용으로만 남긴다.

    `qform`: `qform_settings()` 가 읽어 온 콘솔의 Q-Form 검색 설정. 모드가 `off` 가
    아니면 챗봇과 같은 경로(검색문 field:value 확장 · 청크 메타 가산)로 검색하고,
    무엇이 얼마나 달라졌는지를 `qform` 블록에 함께 싣는다. **기본값은 `None` =
    미반영**이라 이 인자를 주지 않는 호출은 기존과 완전히 같다.
    """
    import eval as ev
    import rag
    gt_path = CRAWLER / gt_name
    if not gt_path.exists():
        alt = CRAWLER / "data" / gt_name
        gt_path = alt if alt.exists() else gt_path
    if not gt_path.exists():
        return {"error": f"평가셋을 찾을 수 없습니다: {gt_name}"}

    qf = {**QFORM_OFF, **(qform or {})}
    mode, scope = str(qf.get("mode") or "off"), str(qf.get("scope") or "msdr")

    gt = ev._load_jsonl(gt_path)
    searcher = rag.Searcher(index_dir=index_dir)
    slots_by_id: dict[str, dict] = {}
    boosted_hits = 0
    retrieved = []
    for r in gt:
        slots = (qform_slots(r["question"], r.get("business_function"), scope)
                 if mode != "off" else {})
        query, kwargs = qform_query(r["question"], slots, mode)
        hits = searcher.search(query, k=10, mode="hybrid_bf", **kwargs)
        if slots:
            boosted_hits += sum(1 for h in hits if h.get("_qform_boost"))
            if r.get("id"):                      # 대조군은 id 로 짝을 맞춘다
                slots_by_id[r["id"]] = slots
        retrieved.append({"id": r.get("id"),
                          "retrieved_chunk_ids": [h["chunk_id"] for h in hits]})
    chunk_meta = ev._load_jsonl(pathlib.Path(index_dir) / "chunk_meta.jsonl")
    res = ev.evaluate_retrieval(gt, retrieved, chunk_meta,
                                score="anchor", id_fallback=False)
    m, a = res["chunk_level"], res.get("anchor_level") or {}
    if not a:
        # 앵커 판정을 못 했다면(청크 메타 없음 등) 숫자를 만들지 않는다 — chunk_id 수치를
        # 앵커 자리에 몰래 넣으면 콘솔이 잣대가 다른 값을 '정확도'로 표시한다.
        return {"error": "앵커 판정을 하지 못했습니다 (청크 본문 없음). "
                         "chunk_meta.jsonl 에 text 필드가 있는지 확인하세요.",
                "chunks": len(chunk_meta)}
    scored, missing = a.get("n_scored", 0), a.get("n_missing_span", 0)
    return {
        "score_mode": "anchor",                 # 이 기록이 앵커 계열임을 스스로 밝힌다
        "n_evaluated": scored,                  # 앵커 채점 문항 = 지표의 실제 분모
        "n_missing_span": missing,              # 앵커 미보유 → 분모 제외분
        "anchor_coverage": round(scored / ((scored + missing) or 1), 4),
        "chunks": len(chunk_meta),
        "hit@1": round(a.get("hit@1", 0), 4), "hit@3": round(a.get("hit@3", 0), 4),
        "hit@5": round(a.get("hit@5", 0), 4), "hit@10": round(a.get("hit@10", 0), 4),
        "mrr@10": round(a.get("mrr", 0), 4),
        "anchor_hit@5": round(a.get("hit@5", 0), 4),
        # ── 아래는 감사용 참고값. 판정에 쓰이지 않는다 ──
        "chunk_hit@5": round(m.get("hit@5", 0), 4),
        "chunk_n_evaluated": m.get("n_evaluated"),
        "recall@50": round(m.get("macro_recall@50", 0), 4),
        # Q-Form 이 이번 측정에 무엇을 했는가(적용 문항 수·대조군 대비 효과)
        "qform": _qform_report(ev, searcher, gt, retrieved, chunk_meta,
                               slots_by_id, qf, boosted_hits),
    }


def apply_search_settings() -> list[str]:
    """평가 직전에 **저장된 검색 설정**을 `rag` 모듈에 주입한다.

    이 호출이 없으면 평가가 `crawler/rag.py` 의 **파일 기본값**으로 돌아간다. 관리자가
    프리셋이나 ⑥ 고급 값을 바꿔도 지표가 꿈쩍하지 않고, `BF_MODE` 를 `hard` 로 저장해 둬도
    실제 측정은 `soft` 로 나갔다. `rag` 는 상수를 호출 시점에 읽으므로 setattr 주입이
    그대로 먹는다(`rag.py` 379행: "런타임에 rag.RRF_K를 바꿔도 반영되지 않아 A/B가 조용히
    틀린다 — 실제로 겪음").
    """
    try:
        import settings as admin_settings
        return admin_settings.apply_runtime()
    except Exception as e:                       # 콘솔 설정이 없어도 평가 자체는 돌아야 한다
        return [f"apply_runtime skip({type(e).__name__}: {e})"]


def _need_stack() -> None:
    missing = [m for m in ("faiss", "numpy", "rank_bm25")
               if __import__("importlib.util", fromlist=["x"]).find_spec(m) is None]
    if missing:
        raise RuntimeError(
            f"검색 스택 패키지가 없습니다: {', '.join(missing)}. "
            f"챗봇과 같은 파이썬 환경에서 콘솔을 띄우거나 "
            f"`pip install -r crawler/requirements.txt` 를 먼저 실행하세요.")


def run_files(out: dict) -> None:
    """첨부 실파일을 다시 받아 청크 메타에 연결한다.

    `pipeline.py` 는 이걸 부르지 않는다 — 재크롤링을 해도 첨부 파일은 그대로다.
    원 저자가 정한 실행 순서가 `parser.py → fetch_attachments.py → link_files.py → chunk.py`
    라서, 여기서는 가운데 두 단계만 돌리고 마지막 재청킹은 콘솔이 따로 안내한다
    (`settings.mark_dirty`).
    """
    import fetch_attachments
    import link_files

    step("첨부 파일 내려받기")
    try:
        fetch_attachments.main()
    except SystemExit as e:                    # "첨부 있는 문서 없음" 등
        raise RuntimeError(f"첨부 다운로드를 시작하지 못했습니다: {e}") from None

    man = CRAWLER / "data" / "files" / "manifest.json"
    rows = json.loads(man.read_text(encoding="utf-8")) if man.exists() else []
    ok = [r for r in rows if r.get("status") == "ok"]
    out["files"] = {"total": len(rows), "ok": len(ok),
                    "failed": len(rows) - len(ok),
                    "bytes": sum(int(r.get("size_bytes") or 0) for r in ok)}

    step("청크 메타에 연결")
    link_files.main()
    out["read_only"] = False


def run_verify(out: dict) -> None:
    """**현재 서비스 인덱스를 그대로** 평가한다. 다시 자르지도, 다시 만들지도 않는다.

    재빌드 직후 '실제로 반영된 인덱스'가 재빌드 때 잰 수치와 같은지 확인하는 용도.
    산출물을 전혀 건드리지 않으므로 백업·복원이 필요 없다.
    """
    _need_stack()
    import rag
    step("검색 인덱스 확인")
    idx = CRAWLER / rag.INDEX_DIR
    if not (idx / "faiss.index").exists():
        raise RuntimeError(f"인덱스가 없습니다: {idx}. 먼저 재빌드가 필요합니다.")
    n = sum(1 for _ in (idx / "chunk_meta.jsonl").open(encoding="utf-8"))
    out["chunks"] = n
    print(f"  서비스 인덱스 청크 {n}건 → {idx}", flush=True)

    # 읽기 전용 모드라 태깅이 비어 있어도 고치지 않는다 — 상태만 알리고 재청킹을 권한다.
    qf = check_qform(rag.INDEX_DIR, out)

    step("평가셋 검증")
    out["search"] = apply_search_settings()
    out["metrics"] = run_eval(rag.INDEX_DIR, qform=qf)
    out["qform"] = (out["metrics"] or {}).get("qform")
    out["read_only"] = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["eval", "rebuild", "verify", "files"], required=True)
    ap.add_argument("--config", default="{}")
    ap.add_argument("--recrawl", action="store_true")
    args = ap.parse_args()
    cfg = json.loads(args.config)

    os.chdir(CRAWLER)                     # crawler 스크립트는 cwd 상대경로를 쓴다
    for p in (str(ADMIN), str(CRAWLER), str(REPO / "chatbot")):
        if p not in sys.path:
            sys.path.insert(0, p)

    out: dict = {"mode": args.mode, "recrawl": args.recrawl}
    snap = None
    mutated = False          # 산출물을 실제로 건드렸는가 — 아니면 복원할 것도 없다

    if args.mode == "verify":
        try:
            run_verify(out)
            out["status"] = "done"
        except Exception as e:
            out["status"] = "failed"
            out["error"] = f"{type(e).__name__}: {e}"
            out["trace"] = traceback.format_exc()[-2000:]
            out["restored"] = False
            out["note"] = "읽기 전용 검증이라 복원할 것이 없습니다."
        print("__RESULT__ " + json.dumps(out, ensure_ascii=False), flush=True)
        return 0 if out["status"] == "done" else 1

    if args.mode == "files":
        global TARGETS
        TARGETS = FILE_TARGETS               # 이 모드는 parsed 만 되돌리면 된다
        try:
            step("현재 상태 백업")
            snap = backup()
            out["backup"] = str(snap)
            mutated = True
            run_files(out)
            out["status"] = "done"
        except Exception as e:
            out["status"] = "failed"
            out["error"] = f"{type(e).__name__}: {e}"
            out["trace"] = traceback.format_exc()[-2000:]
            if snap and mutated:
                try:
                    step("실패 — 원상복구")
                    restore(snap)
                    out["restored"] = True
                except Exception as e2:
                    out["restore_error"] = str(e2)
        print("__RESULT__ " + json.dumps(out, ensure_ascii=False), flush=True)
        return 0 if out["status"] == "done" else 1

    try:
        step("현재 상태 백업")
        snap = backup()
        out["backup"] = str(snap)

        _need_stack()

        import chunk as chunk_mod
        import rag
        mods = {"chunk": chunk_mod, "rag": rag}

        step("청크 파라미터 주입")
        out["injected"] = inject(cfg, mods)

        sandbox = args.mode == "eval"
        index_dir = "data/index_eval" if sandbox else rag.INDEX_DIR
        if sandbox:
            rag.INDEX_DIR = index_dir     # pipeline.main() 이 이 값을 읽는다
            shutil.rmtree(CRAWLER / index_dir, ignore_errors=True)

        step("홈페이지 수집 + 파싱" if args.recrawl else "저장된 원문으로 다시 자르기")
        mutated = True
        run_pipeline(args.recrawl)

        step("검색 인덱스 확인")
        idx = CRAWLER / index_dir
        if not (idx / "faiss.index").exists():
            raise RuntimeError(f"인덱스가 생성되지 않았습니다: {idx}")
        n = sum(1 for _ in (idx / "chunk_meta.jsonl").open(encoding="utf-8"))
        out["chunks"] = n
        print(f"  인덱스 청크 {n}건 → {idx}")

        # 방금 자른 청크에 Q-Form 메타가 실제로 붙었는지 확인한 뒤 평가에 그 설정을 건다.
        qf = check_qform(index_dir, out)

        step("평가셋 검증")
        out["search"] = apply_search_settings()
        out["metrics"] = run_eval(index_dir, qform=qf)
        out["qform"] = (out["metrics"] or {}).get("qform")

        if sandbox:
            step("샌드박스 정리 · 원상복구")
            shutil.rmtree(idx, ignore_errors=True)
            restore(snap)                 # build_and_save() 가 덮어쓴 chunks.jsonl 복원
            out["restored"] = True
            out["verify"] = _verify(snap)
        out["status"] = "done"

    except Exception as e:
        out["status"] = "failed"
        out["error"] = f"{type(e).__name__}: {e}"
        out["trace"] = traceback.format_exc()[-2000:]
        if snap and mutated:
            try:
                step("실패 — 원상복구")
                restore(snap)
                out["restored"] = True
                out["verify"] = _verify(snap)
            except Exception as e2:
                out["restore_error"] = str(e2)
        else:
            out["restored"] = False
            out["note"] = "산출물을 건드리기 전에 멈춰 복원이 필요하지 않았습니다."
    print("__RESULT__ " + json.dumps(out, ensure_ascii=False), flush=True)
    return 0 if out["status"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
