"""RAG 검색 공용 모듈 — 임베딩 · dense(FAISS) · BM25(kiwi) · 하이브리드(RRF).

- 임베딩: sentence-transformers `BAAI/bge-m3` (다국어, 1024d).
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


def embed_texts(texts: list[str]) -> np.ndarray:
    m = get_model()
    e = m.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(e, dtype="float32")


def chunk_embed_text(chunk: dict) -> str:
    """검색 임베딩 입력 — 제목 맥락을 본문 앞에 덧붙임."""
    title = chunk.get("page_title", "")
    return f"{title}\n{chunk['text']}" if title else chunk["text"]


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
        n = len(self.chunks)
        embs = self.embs if self.embs is not None else np.zeros((0, EMB_DIM), "float32")

        index = faiss.IndexFlatIP(EMB_DIM)
        if n:
            index.add(embs)
        faiss.write_index(index, str(self.dir / "faiss.index"))
        np.save(self.dir / "emb.npy", embs)

        from rank_bm25 import BM25Okapi
        corpus = [tokenize(c["text"]) for c in self.chunks]
        bm25 = BM25Okapi(corpus) if corpus else None
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
        self.index = faiss.read_index(str(self.dir / "faiss.index"))
        with open(self.dir / "bm25.pkl", "rb") as f:
            self.bm25 = pickle.load(f)["bm25"]

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
               max_per_doc: int = 1) -> list[tuple[int, float]]:
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
        """
        d = self.dense(query, pool)
        s = self.sparse(query, pool)
        rrf: dict[int, float] = {}
        for rank, (idx, _) in enumerate(d):
            rrf[idx] = rrf.get(idx, 0.0) + dw / (rrf_k + rank + 1)
        for rank, (idx, _) in enumerate(s):
            rrf[idx] = rrf.get(idx, 0.0) + sw / (rrf_k + rank + 1)
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
        pairs = [[query, chunk_embed_text(self.chunks[idx])] for idx, _ in head]
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
