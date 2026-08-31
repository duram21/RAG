"""벡터 인덱스의 저장과 로드.

Chroma나 FAISS 같은 벡터 DB 대신 numpy 배열을 그대로 씁니다.
문서 수천 개 규모까지는 이걸로 충분히 빠르고, 무엇보다 안에서 무슨 일이
일어나는지 전부 보입니다. 나중에 실제 벡터 DB로 바꾸더라도
`VectorStore` 인터페이스만 유지하면 나머지 코드는 그대로 둘 수 있습니다.

디스크 레이아웃 (index/):
    embeddings.npy   float32 배열, shape = (청크 수, 임베딩 차원)
    chunks.jsonl     청크 메타데이터, embeddings.npy 의 행 순서와 1:1 대응
    meta.json        어떤 모델·설정으로 만든 인덱스인지 기록
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .chunking import Chunk
from .config import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL


@dataclass
class VectorStore:
    vectors: np.ndarray          # shape: (N, D), L2 정규화된 상태
    chunks: list[Chunk]          # 길이 N, vectors 의 행과 같은 순서
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.vectors) != len(self.chunks):
            raise ValueError(
                f"벡터 수({len(self.vectors)})와 청크 수({len(self.chunks)})가 다릅니다."
            )

    def __len__(self) -> int:
        return len(self.chunks)

    # --- 저장 ---

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)

        np.save(index_dir / "embeddings.npy", self.vectors)

        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for chunk in self.chunks:
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")

        meta = {
            "embedding_model": EMBEDDING_MODEL,
            "dim": int(self.vectors.shape[1]),
            "count": len(self.chunks),
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **self.meta,
        }
        (index_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # --- 로드 ---

    @classmethod
    def load(cls, index_dir: Path) -> "VectorStore":
        if not (index_dir / "embeddings.npy").exists():
            raise FileNotFoundError(
                f"{index_dir} 에 인덱스가 없습니다. 먼저 `python scripts/ingest.py` 를 실행하세요."
            )

        vectors = np.load(index_dir / "embeddings.npy")

        chunks: list[Chunk] = []
        with (index_dir / "chunks.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                chunks.append(Chunk(**json.loads(line)))

        meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))

        # 인덱스를 만든 모델과 지금 질문을 인코딩할 모델이 다르면 검색이 무의미해집니다.
        if meta.get("embedding_model") != EMBEDDING_MODEL:
            raise ValueError(
                f"인덱스는 '{meta.get('embedding_model')}' 로 만들어졌는데 "
                f"현재 설정은 '{EMBEDDING_MODEL}' 입니다. 인덱스를 다시 생성하세요."
            )

        return cls(vectors=vectors, chunks=chunks, meta=meta)

    # --- 검색 ---

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[int, float]]:
        """질문 벡터와 가장 가까운 청크 k개를 (행 번호, 점수) 목록으로 반환한다.

        저장된 벡터와 질문 벡터 모두 L2 정규화되어 있으므로
        **내적이 곧 코사인 유사도**입니다. 즉 아래 한 줄이 검색의 전부입니다.

            scores = self.vectors @ query_vector

        (N, D) @ (D,) -> (N,) 로, 모든 청크에 대한 유사도를 한 번에 계산합니다.
        점수 범위는 -1 ~ 1 이고 1에 가까울수록 비슷합니다.

        전체를 훑는 완전 탐색(brute-force)이라 청크 수에 비례해 느려지지만,
        수천~수만 개 규모까지는 밀리초 단위로 끝납니다. 그 이상으로 커지면
        이 메서드만 FAISS 같은 근사 최근접 탐색(ANN)으로 교체하면 됩니다.
        """
        scores = self.vectors @ query_vector

        k = min(k, len(scores))
        # argpartition 으로 상위 k개만 추린 뒤(O(N)) 그 안에서만 정렬한다.
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]

        return [(int(i), float(scores[i])) for i in top]
