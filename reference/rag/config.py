"""프로젝트 전역 설정.

값을 바꿔가며 검색 품질이 어떻게 달라지는지 실험해보는 것이 이 파일의 목적입니다.
"""

from pathlib import Path

# --- 경로 ---
# reference/rag/config.py 이므로 저장소 루트는 세 칸 위입니다.
ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = ROOT / "data" / "docs"
INDEX_DIR = ROOT / "index"

# --- 임베딩 ---
# multilingual-e5-small: 한국어를 포함한 100여 개 언어를 지원하는 작은 검색용 모델(384차원).
# e5 계열은 질문에는 "query: ", 문서에는 "passage: " 접두사를 붙여야 성능이 나옵니다.
# (rag/embedding.py 에서 자동으로 처리합니다.)
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384

# --- 청킹 ---
# 청크가 너무 크면 관련 없는 내용이 섞여 검색 정확도가 떨어지고,
# 너무 작으면 문맥이 잘려 답변 근거로 쓰기 어려워집니다.
CHUNK_SIZE = 500       # 청크 하나의 목표 길이 (문자 수)
CHUNK_OVERLAP = 100    # 인접 청크가 겹치는 길이 — 경계에서 문맥이 끊기는 걸 완화

# --- 검색 ---
TOP_K = 4              # 답변 생성에 넘길 청크 개수

# --- 생성 ---
# 어떤 공급자를 쓸지는 .env 의 LLM_PROVIDER 로 정합니다 ("gemini" 또는 "claude").
# 여기 값은 각 공급자를 골랐을 때 쓸 모델입니다.
# gemini-3.7-flash 는 최신이지만 무료 티어에서 503(과부하)이 잦습니다.
# 안정적으로 응답하는 3.6-flash 를 기본값으로 씁니다.
# 사용 가능한 모델 목록: python scripts/models.py
GEMINI_MODEL = "gemini-3.6-flash"

# 기본 모델이 계속 503(과부하)이면 아래 순서로 대체 모델을 시도합니다.
# 무료 티어에서는 최신·인기 모델일수록 막히므로, 조금씩 덜 붐비는 쪽으로 내려갑니다.
GEMINI_FALLBACKS = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]

# 한 요청을 기다려주는 시간 (밀리초). 이 시간을 넘기면 포기하고 다음 모델로 넘어갑니다.
# 타임아웃이 없으면 과부하 모델의 응답을 무한정 기다리게 됩니다.
REQUEST_TIMEOUT_MS = 60_000
CLAUDE_MODEL = "claude-opus-5"
MAX_TOKENS = 16000
