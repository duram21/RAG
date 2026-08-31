"""텍스트를 벡터로 바꾼다.

Anthropic은 임베딩 API를 제공하지 않으므로, 여기서는 로컬 모델을 씁니다.
(원한다면 Voyage AI 등 외부 임베딩 API로 이 파일만 갈아끼우면 됩니다.)

e5 계열 모델의 특징: 질문과 문서를 **서로 다른 접두사**로 인코딩합니다.
검색은 "질문 ↔ 답이 들어있는 문서"를 매칭하는 비대칭(asymmetric) 문제이고,
같은 문장을 두 역할로 구분해 학습시킨 덕분에 접두사만 맞춰줘도 성능이 크게 올라갑니다.
"""

from __future__ import annotations

import numpy as np

from .config import EMBEDDING_MODEL

_model = None


def get_model():
    """임베딩 모델을 지연 로딩한다 (최초 호출 시 다운로드/로드)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        print(f"[embedding] 모델 로딩 중: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _encode(texts: list[str], prefix: str, show_progress: bool = False) -> np.ndarray:
    model = get_model()
    prefixed = [f"{prefix}{t}" for t in texts]
    vectors = model.encode(
        prefixed,
        batch_size=32,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True,  # L2 정규화 → 내적이 곧 코사인 유사도가 된다
    )
    return vectors.astype(np.float32)


def embed_passages(texts: list[str], show_progress: bool = True) -> np.ndarray:
    """문서(청크)를 인코딩한다. 반환 shape: (len(texts), EMBEDDING_DIM)"""
    return _encode(texts, prefix="passage: ", show_progress=show_progress)


def embed_query(text: str) -> np.ndarray:
    """질문을 인코딩한다. 반환 shape: (EMBEDDING_DIM,)"""
    return _encode([text], prefix="query: ")[0]
