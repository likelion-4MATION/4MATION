"""RAG 검색 공용 모듈 — 임베딩 · dense(FAISS) · BM25(kiwi) · 하이브리드(RRF).

- 임베딩: sentence-transformers `BAAI/bge-m3` (다국어, 1024d).
  2026-07-23 `Qwen/Qwen3-Embedding-4B`(2560d) 교체를 시도했으나 로드 단계에서
  프로세스가 응답 없이 종료(이 머신 총 RAM 16GB, 4B 파라미터 bf16 가중치만 ~8GB —
  로드 시 순간 피크 메모리가 이를 초과하는 OOM으로 추정) → **bge-m3로 롤백**.
  `embed_texts(is_query=...)`는 Qwen3-Embedding류(비대칭 query prompt 필요 모델)
  재시도 대비로 남겨두되, bge-m3는 `model.prompts`에 "query"가 등록돼 있지 않아
  `is_query=True` 호출 시 즉시 오류가 나므로 **호출부(Searcher.dense)는 되돌림**.
  DECISIONS.md 참고, 롤백 백업은 재사용됨(`data/index_backup_bgem3_chunk500/`).
- dense: FAISS IndexFlatIP + 정규화 임베딩(= 코사인).
- sparse: rank_bm25 BM25Okapi, kiwipiepy 형태소 토큰.
- 융합: RRF(k=5, dw=2.0, sw=1.0) — 400건 테스트셋 그리드서치로 튜닝(data/rrf_grid_log.txt).

Store: doc_id 단위 upsert + content_hash 스킵 (recollect 재수집 트리거용).
"""

from __future__ import annotations

import json
import pathlib
import pickle

import faiss
import numpy as np

MODEL_NAME = "BAAI/bge-m3"
RERANKER_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
INDEX_DIR = "data/index"
EMB_DIM = 1024
BM25_B = 0.85
"""BM25 길이정규화(rank_bm25 기본 0.75). 착오송금 hub 문서(장문 청크) 억제 목적으로
0.0~1.0 그리드서치(400건) — b=0.85가 기본값 대비 6개 지표(전체/착오송금 hit@1·hit@3·MRR)
중 5개 개선·1개(착오송금 hit@3) 동률로 유일하게 열세가 없어 채택. DECISIONS.md 참고."""

BF_BOOST = 0.01
"""business_function(facet) 소프트부스트 강도. 질의 임베딩과 업무영역별 centroid의
코사인 유사도로 top-1 업무영역을 예측해, RRF 점수에 예측 업무영역과 일치하는 후보만
+BF_BOOST를 더한다. 07-22 세션(ko-sroberta 기준)과 07-23 1차 재검증(bge-m3, boost
0.1~1.2)에서는 분류기 오분류가 그대로 순위 왜곡으로 전이돼 전 구간 손해로 기각됐으나,
분류기 정확도가 낮은 구간(0.1 이상)만 봤을 뿐 더 작은 값은 미검증이었음. 0.005~0.05
정밀 그리드서치(400건) 결과 **boost=0.01에서 6개 업무 hit@3가 전부 비하락(은닉재산
.952→.968 개선, 나머지 5개 동일)**이면서 전체 hit@1 .690→.693·MRR .810→.811 소폭
개선 — 유일하게 순수 이득만 있는 지점. boost=0.02는 예금보험금 hit@3 −.016 손해가
나서 0.01보다 열세. DECISIONS.md·data/facet_boost_grid_log.txt 참고."""

_model = None
_kiwi = None
_reranker = None


def get_reranker():
    """경량 다국어 cross-encoder (재랭킹 전용, bi-encoder와 별도 모델).

    근소한 점수차로 순위가 갈리는 짧고 유사한 문서들(예: 착오송금 신청방법/절차/
    신청대상처럼 문구가 겹치는 소형 문서군)을 질의-문서 쌍으로 직접 채점해 재정렬한다.
    bge-reranker-base(278M) 대비 약 6.5배 빠름(쌍당 실측 170ms vs 1.1초) — top-5
    재랭킹 기준 질의당 1초 미만으로 대화형 사용에 적합.
    """
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANKER_NAME, max_length=512)
    return _reranker


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_emb_dim() -> int:
    """실제 로드된 모델의 임베딩 차원(모델 교체 안전성).

    EMB_DIM 상수는 하위호환·참고용으로만 남겨둠 — 인덱스 빌드/검증 등 실제
    차원이 필요한 곳은 반드시 이 함수를 써서 MODEL_NAME 교체 시 값이 자동으로
    맞춰지게 한다. 상수만 쓰면 모델을 바꾼 뒤 상수를 안 고쳐도 조용히 통과했다가
    FAISS 검색 시점에야 깨지는(또는 verify_integrity.py처럼 상수가 옛 모델
    기준으로 방치되는) 문제가 실제로 있었음(EMB_DIM=768로 방치된 사례 발견·수정)."""
    m = get_model()
    if hasattr(m, "get_embedding_dimension"):
        return m.get_embedding_dimension()
    return m.get_sentence_embedding_dimension()  # 구버전 sentence-transformers 호환


def _get_kiwi():
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    return _kiwi


def tokenize(text: str) -> list[str]:
    """BM25용 한국어 토큰 (조사·기호 제거, 2자+ 명사/어간 위주)."""
    kiwi = _get_kiwi()
    keep = {"NNG", "NNP", "NNB", "NR", "NP", "VV", "VA", "SL", "SN", "SH", "MAG"}
    out = []
    for t in kiwi.tokenize(text):
        if t.tag in keep and len(t.form) >= 1:
            out.append(t.form.lower())
    return out or [text.lower()]


def embed_texts(texts: list[str], is_query: bool = False) -> np.ndarray:
    """is_query=True: Qwen3-Embedding 공식 권고대로 질의 측에 'query' prompt 적용
    (sentence-transformers 저장 prompt, model.prompts['query']). 문서 측(is_query=False)은
    프리픽스 없이 그대로 인코딩 — 모델카드 기준 비대칭 사용 패턴."""
    m = get_model()
    kwargs = {"prompt_name": "query"} if is_query else {}
    e = m.encode(texts, normalize_embeddings=True, show_progress_bar=False, **kwargs)
    return np.asarray(e, dtype="float32")


def chunk_embed_text(chunk: dict, disambiguate: bool = False) -> str:
    """검색 임베딩 입력(dense+BM25 공용) — 제목 맥락을 본문 앞에 덧붙임.

    disambiguate=True: page_title이 다른 문서와 충돌하는 소수 케이스 전용으로
    sub_category(브레드크럼[1:] 조인, 예: "착오송금반환지원 > 착오송금인 > 유의사항")를
    prefix로 사용 — 파서가 브레드크럼에서 그대로 추출한 기존 필드라 창작 없음(규칙 7 정합).

    전 청크 일괄 적용은 시도 후 폐기: 400건 평가에서 FAQ류 문서(청크 다수가
    동일 sub_category를 공유)가 상위 브레드크럼 반복으로 임베딩이 희석돼
    hit@1 .672->.650·MRR .800->.787 하락(은닉재산 신고 hit@1 .548->.371 최대
    타격, DECISIONS.md 참고). 실제 page_title 충돌은 38문서 중 2쌍뿐이라
    _colliding_titles()로 걸러낸 해당 청크에만 좁혀 적용.
    """
    if disambiguate:
        prefix = chunk.get("sub_category") or chunk.get("page_title", "")
    else:
        prefix = chunk.get("page_title", "")
    return f"{prefix}\n{chunk['text']}" if prefix else chunk["text"]


def _colliding_titles(chunks: list[dict]) -> set[str]:
    """서로 다른 문서(parent_doc_id)가 동일 page_title을 쓰는 제목 집합."""
    by_title: dict[str, set[str]] = {}
    for c in chunks:
        by_title.setdefault(c.get("page_title", ""), set()).add(c["parent_doc_id"])
    return {t for t, docs in by_title.items() if len(docs) > 1}


class Store:
    """청크 + 임베딩 + 인덱스 저장소. doc_id 단위 upsert 지원."""

    def __init__(self, index_dir: str = INDEX_DIR):
        self.dir = pathlib.Path(index_dir)
        self.chunks: list[dict] = []
        self.embs: np.ndarray | None = None
        self.doc_hash: dict[str, str] = {}
        self._load_state()

    # ── 상태 로드/저장 ───────────────────────────────────────
    def _load_state(self) -> None:
        meta = self.dir / "chunk_meta.jsonl"
        emb = self.dir / "emb.npy"
        docs = self.dir / "docs.json"
        if meta.exists() and emb.exists():
            self.chunks = [json.loads(l) for l in meta.read_text(encoding="utf-8").splitlines() if l]
            self.embs = np.load(emb)
        if docs.exists():
            self.doc_hash = json.loads(docs.read_text(encoding="utf-8"))

    def needs_update(self, doc_id: str, content_hash: str) -> bool:
        return self.doc_hash.get(doc_id) != content_hash

    # ── upsert / remove (doc_id 단위) ────────────────────────
    def upsert(self, doc_id: str, chunks: list[dict], content_hash: str) -> None:
        self._drop(doc_id)
        if chunks:
            e = embed_texts([chunk_embed_text(c) for c in chunks])
            self.chunks.extend(chunks)
            self.embs = e if self.embs is None else np.vstack([self.embs, e])
        self.doc_hash[doc_id] = content_hash

    def remove(self, doc_id: str) -> None:
        self._drop(doc_id)
        self.doc_hash.pop(doc_id, None)

    def _drop(self, doc_id: str) -> None:
        keep = [i for i, c in enumerate(self.chunks) if c["parent_doc_id"] != doc_id]
        if len(keep) != len(self.chunks):
            self.chunks = [self.chunks[i] for i in keep]
            if self.embs is not None and len(self.embs):
                self.embs = self.embs[keep] if keep else None

    # ── 인덱스 빌드 + 영속화 ─────────────────────────────────
    def build_and_save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        colliding = _colliding_titles(self.chunks)

        # 제목 충돌 청크만 sub_category 포함해 재임베딩 (upsert 시점엔 다른
        # 문서의 존재를 알 수 없어 doc_id 단위 upsert와 무관하게 저장 직전 일괄 처리).
        if colliding and self.embs is not None and len(self.embs):
            idxs = [i for i, c in enumerate(self.chunks) if c.get("page_title", "") in colliding]
            if idxs:
                texts = [chunk_embed_text(self.chunks[i], disambiguate=True) for i in idxs]
                self.embs[idxs] = embed_texts(texts)

        n = len(self.chunks)
        dim = get_emb_dim()
        embs = self.embs if self.embs is not None else np.zeros((0, dim), "float32")

        index = faiss.IndexFlatIP(dim)
        if n:
            index.add(embs)
        faiss.write_index(index, str(self.dir / "faiss.index"))
        np.save(self.dir / "emb.npy", embs)

        from rank_bm25 import BM25Okapi
        corpus = [tokenize(chunk_embed_text(c, disambiguate=c.get("page_title", "") in colliding))
                  for c in self.chunks]
        bm25 = BM25Okapi(corpus, b=BM25_B) if corpus else None
        with open(self.dir / "bm25.pkl", "wb") as f:
            pickle.dump({"bm25": bm25, "corpus_len": n}, f)

        with open(self.dir / "chunk_meta.jsonl", "w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        (self.dir / "docs.json").write_text(
            json.dumps(self.doc_hash, ensure_ascii=False, indent=2), encoding="utf-8")

        # chunks.jsonl 도 최신화 (T3 산출물과 일치)
        with open("data/chunks.jsonl", "w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")


class Searcher:
    """dense / bm25 / hybrid(RRF) 검색."""

    def __init__(self, index_dir: str = INDEX_DIR):
        self.dir = pathlib.Path(index_dir)
        self.chunks = [json.loads(l) for l in
                       (self.dir / "chunk_meta.jsonl").read_text(encoding="utf-8").splitlines() if l]
        self._colliding = _colliding_titles(self.chunks)
        self.index = faiss.read_index(str(self.dir / "faiss.index"))
        # bm25.pkl은 이 저장소의 Store.build_and_save()가 로컬에서 직접 생성한
        # 신뢰된 산출물(외부/사용자 업로드 데이터 아님) — pickle 로드 안전.
        with open(self.dir / "bm25.pkl", "rb") as f:
            self.bm25 = pickle.load(f)["bm25"]

        # 모델 교체 안전성: 로드된 인덱스 차원과 MODEL_NAME의 실제 임베딩 차원이
        # 다르면(예: 인덱스는 bge-m3=1024d로 빌드됐는데 MODEL_NAME만 다른 차원의
        # 모델로 바꾼 경우) FAISS 검색 시점의 불명확한 오류 대신 여기서 즉시,
        # 명확하게 실패시킨다.
        actual_dim = get_emb_dim()
        if self.index.d != actual_dim:
            raise ValueError(
                f"인덱스 차원 불일치: '{self.dir}'의 FAISS 인덱스는 {self.index.d}차원인데 "
                f"현재 MODEL_NAME='{MODEL_NAME}'의 임베딩 차원은 {actual_dim}입니다. "
                f"모델을 교체했다면 이 index_dir를 해당 모델로 재빌드하거나, "
                f"MODEL_NAME을 인덱스가 빌드된 모델로 되돌리세요.")

        self._bf_names, self._bf_centroids = self._build_bf_centroids()

    def _build_bf_centroids(self) -> tuple[list[str], np.ndarray]:
        """business_function별 청크 임베딩 centroid(정규화) — facet 소프트부스트용.

        IndexFlatIP는 원본 벡터를 그대로 보관하므로 emb.npy를 별도로 다시 읽지
        않고 reconstruct_n()으로 직접 복원한다(인덱스가 곧 진실 소스, 이중 관리 방지)."""
        if self.index.ntotal == 0:
            return [], np.zeros((0, get_emb_dim()), "float32")
        embs = self.index.reconstruct_n(0, self.index.ntotal)
        by_bf: dict[str, list[int]] = {}
        for i, c in enumerate(self.chunks):
            by_bf.setdefault(c["business_function"], []).append(i)
        names = sorted(by_bf)
        mat = []
        for bf in names:
            v = embs[by_bf[bf]].mean(axis=0)
            v = v / (np.linalg.norm(v) + 1e-9)
            mat.append(v)
        return names, np.stack(mat)

    def predict_business_function(self, query: str) -> str | None:
        """질의 임베딩과 업무영역 centroid의 코사인 유사도로 top-1 예측(400건
        기준 정확도 80.7%, DECISIONS.md 참고)."""
        if not self._bf_names:
            return None
        q = embed_texts([query])[0]
        sims = self._bf_centroids @ q
        return self._bf_names[int(np.argmax(sims))]

    def dense(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        q = embed_texts([query])
        D, I = self.index.search(q, min(k, len(self.chunks)))
        return [(int(i), float(d)) for i, d in zip(I[0], D[0]) if i >= 0]

    def sparse(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        if self.bm25 is None:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        order = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in order]

    def hybrid(self, query: str, k: int = 10, pool: int = 30,
               rrf_k: int = 5, dw: float = 2.0, sw: float = 1.0,
               max_per_doc: int = 1, bf_boost: float = BF_BOOST) -> list[tuple[int, float]]:
        """dense+sparse RRF 융합 후 문서당 max_per_doc개로 캡.

        청크 수가 많은 문서(대형 FAQ 등)가 RRF 점수 우위로 top-k를 독점하는
        문제 대응 — 같은 parent_doc_id의 2번째 이후 청크는 건너뛰고 다음
        순위 문서로 채운다(단순 top-1 개별 순위는 그대로 보존됨).
        max_per_doc=0이면 캡 없이 기존 동작.

        임베딩 모델을 jhgan/ko-sroberta-multitask -> BAAI/bge-m3(1024d)로
        교체하면서 RRF 파라미터를 다시 그리드서치(rrf_k×dw/sw×max_per_doc,
        60개 조합)로 재튜닝. rrf_k=5, dw=2.0(dense 가중치 상향), sw=1.0에서
        hit@3 0.830->0.930(+0.100), MRR 0.706->0.800으로 가장 우수함을 400건
        테스트셋으로 확인(dense 단독도 hit@3 0.665->0.848로 bge-m3가 기존
        모델보다 훨씬 강함 — dw를 sw보다 높게 주는 것이 합리적). data/rrf_grid_log.txt 참고.

        bf_boost: business_function 소프트부스트(BF_BOOST 참고, 400건 정밀
        그리드서치로 0.01 채택 — 6개 업무 hit@3 전부 비하락 확인). bf_boost=0이면
        기존 동작(부스트 없음)과 동일.
        """
        d = self.dense(query, pool)
        s = self.sparse(query, pool)
        rrf: dict[int, float] = {}
        for rank, (idx, _) in enumerate(d):
            rrf[idx] = rrf.get(idx, 0.0) + dw / (rrf_k + rank + 1)
        for rank, (idx, _) in enumerate(s):
            rrf[idx] = rrf.get(idx, 0.0) + sw / (rrf_k + rank + 1)
        if bf_boost:
            predicted_bf = self.predict_business_function(query)
            if predicted_bf is not None:
                for idx in list(rrf):
                    if self.chunks[idx]["business_function"] == predicted_bf:
                        rrf[idx] += bf_boost
        ranked = sorted(rrf.items(), key=lambda x: x[1], reverse=True)
        if not max_per_doc:
            return ranked[:k]
        seen: dict[str, int] = {}
        out: list[tuple[int, float]] = []
        for idx, score in ranked:
            doc_id = self.chunks[idx]["parent_doc_id"]
            if seen.get(doc_id, 0) >= max_per_doc:
                continue
            seen[doc_id] = seen.get(doc_id, 0) + 1
            out.append((idx, score))
            if len(out) >= k:
                break
        return out

    def rerank(self, query: str, hits: list[tuple[int, float]], k: int = 5,
               pool: int = 5) -> list[tuple[int, float]]:
        """hits(이미 정렬된 후보) 중 상위 pool개만 cross-encoder로 재정렬.

        pool을 작게(기본 5) 유지하는 이유: 재랭킹 비용은 후보 수에 선형 비례한다.
        1심 검색(dense+bm25 RRF)이 이미 정답을 pool 안에 들여놨는지가 재랭킹
        효과의 전제이므로, pool 밖 후보는 원래 순서 뒤에 그대로 이어붙인다.
        """
        head, tail = hits[:pool], hits[pool:]
        if not head:
            return hits[:k]
        ce = get_reranker()
        pairs = [[query, chunk_embed_text(
            self.chunks[idx], disambiguate=self.chunks[idx].get("page_title", "") in self._colliding)]
            for idx, _ in head]
        scores = ce.predict(pairs)
        order = sorted(range(len(head)), key=lambda i: scores[i], reverse=True)
        reranked = [head[i] for i in order]
        return (reranked + tail)[:k]

    def search(self, query: str, k: int = 5, mode: str = "hybrid",
               rerank_pool: int = 5) -> list[dict]:
        if mode == "dense":
            hits = self.dense(query, k)
        elif mode == "bm25":
            hits = self.sparse(query, k)
        elif mode == "hybrid_rerank":
            hits = self.hybrid(query, max(k, rerank_pool, 10))
            hits = self.rerank(query, hits, k, pool=rerank_pool)
        else:
            hits = self.hybrid(query, k)
        out = []
        for idx, score in hits:
            c = dict(self.chunks[idx])
            c["_score"] = round(score, 4)
            out.append(c)
        return out
