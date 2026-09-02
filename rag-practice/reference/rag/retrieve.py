"""질문 → 관련 청크 검색 (RAG의 R).

`store.search()` 가 벡터 연산이라면, 이 모듈은 그 위에 얹는 얇은 사용 계층입니다.
질문을 인코딩하고, 결과를 사람이 다루기 좋은 형태로 포장하고,
점수가 너무 낮은 결과는 걸러냅니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .chunking import Chunk
from .config import INDEX_DIR, TOP_K
from .embedding import embed_query
from .store import VectorStore


@dataclass
class SearchResult:
    chunk: Chunk
    score: float   # 코사인 유사도 (-1 ~ 1, 클수록 유사)
    rank: int      # 1부터 시작

    @property
    def source(self) -> str:
        return self.chunk.source


def retrieve(
    query: str,
    store: VectorStore,
    k: int = TOP_K,
    min_score: float = 0.0,
) -> list[SearchResult]:
    """질문과 관련된 청크를 점수 높은 순으로 반환한다.

    min_score: 이 점수 미만은 버립니다. 문서에 답이 없는 질문에 대해
        엉뚱한 청크를 근거로 들이대는 것을 막는 1차 방어선입니다.

        주의 — e5 계열 모델은 무관한 쌍에도 0.7 안팎의 점수를 주는 경향이 있어
        "0.5 이상이면 관련 있다" 같은 직관이 통하지 않습니다.
        실제 질문들을 넣어보고 분포를 확인한 뒤 임계값을 정하세요.
        (기본값 0.0 = 필터링 없음)
    """
    query_vector = embed_query(query)
    hits = store.search(query_vector, k)

    results = [
        SearchResult(chunk=store.chunks[idx], score=score, rank=rank)
        for rank, (idx, score) in enumerate(hits, start=1)
        if score >= min_score
    ]
    return results


def load_store(index_dir: Path = INDEX_DIR) -> VectorStore:
    """기본 인덱스를 로드한다 (편의 함수)."""
    return VectorStore.load(index_dir)


def format_context(results: list[SearchResult]) -> str:
    """검색 결과를 LLM 프롬프트에 넣을 문자열로 조립한다.

    각 청크에 `[1]`, `[2]` 번호를 붙이는 게 핵심입니다.
    모델이 답변에서 이 번호를 인용하게 만들면, 사용자가 근거를 되짚어볼 수 있습니다.
    """
    blocks = []
    for r in results:
        blocks.append(f"[{r.rank}] 출처: {r.source}\n{r.chunk.body}")
    return "\n\n".join(blocks)
