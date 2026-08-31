# RAG 연습 프로젝트

검색 증강 생성(Retrieval-Augmented Generation)을 밑바닥부터 단계별로 만들어보는 연습용 저장소입니다.
벡터 DB 라이브러리를 쓰지 않고 numpy로 직접 인덱스를 구현해서, 검색이 실제로
어떻게 동작하는지 눈으로 확인하는 것을 목표로 합니다.

## 스택

| 역할 | 선택 | 이유 |
|---|---|---|
| 임베딩 | `sentence-transformers` (로컬) | 무료·오프라인·재색인 즉시. API 한도에 걸리지 않음 |
| 인덱스 | numpy 배열 + `.npy` | 코사인 유사도를 직접 구현해 원리를 학습 |
| 생성 | Gemini 또는 Claude (교체 가능) | `.env` 의 `LLM_PROVIDER` 한 줄로 전환 |

생성 공급자는 [rag/llm.py](rag/llm.py) 뒤에 감춰져 있습니다. 검색(임베딩·인덱스·랭킹)이
RAG의 본체이고 생성은 마지막 한 단계일 뿐인데, 공급자 SDK를 파이프라인 곳곳에 박아두면
나중에 바꿀 수가 없기 때문입니다.

## 구조

```
rag/
  chunking.py   문서 → 청크
  embedding.py  텍스트 → 벡터 (로컬 모델)
  store.py      인덱스 저장/로드 + 코사인 유사도 검색
  retrieve.py   질문 → 관련 청크
  llm.py        LLM 공급자 추상화 (Gemini / Claude)
  generate.py   근거 → 답변
scripts/        실행 진입점 (ingest, search, ask)
data/docs/      검색 대상 문서 (샘플: 가상 회사 '누리테크' 사내 핸드북)
index/          생성된 인덱스 (gitignore, ingest 실행 시 생성)
```

## 설치

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# .venv\Scripts\activate         # Windows PowerShell
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt

cp .env.example .env
```

그리고 `.env` 에 쓸 공급자와 키를 채웁니다. 둘 중 하나만 있으면 됩니다.

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=...        # https://aistudio.google.com/apikey (무료 티어 있음)
# ANTHROPIC_API_KEY=...   # https://console.anthropic.com/settings/keys
```

임베딩은 로컬 모델이라 **인덱싱과 검색은 API 키 없이도 동작합니다.**
키는 답변 생성(`ask.py`)에만 필요합니다.

## 사용법

```bash
python scripts/ingest.py                        # 문서를 청킹·임베딩해서 인덱스 생성
python scripts/search.py "연차는 며칠인가요?"    # 검색 결과만 확인 (API 키 불필요)
python scripts/ask.py "연차는 며칠인가요?"       # 검색 + LLM 답변

python scripts/ask.py "연차는 며칠인가요?" --provider claude   # 공급자 임시 변경
python scripts/models.py --check                # 내 키로 실제 되는 모델 확인
```

## 무료 티어에서 생기는 일

Gemini 무료 티어는 **인기 있는 최신 모델일수록 503(과부하)** 을 자주 냅니다.
모델 ID가 틀린 게 아니라 정말로 붐비는 것이므로, 코드가 스스로 헤쳐나가게 해뒀습니다.

1. 같은 모델로 지수 백오프 재시도 (1초 → 2초)
2. 그래도 안 되면 `GEMINI_FALLBACKS` 의 다음 모델로 전환
3. 성공한 모델을 기억해 다음 질문은 거기서 시작

`REQUEST_TIMEOUT_MS` 도 함께 둡니다. 타임아웃이 없으면 과부하 모델의 응답을
무한정 기다리게 되어 대체 모델로 넘어갈 기회조차 없습니다.

지금 어떤 모델이 살아 있는지는 `python scripts/models.py --check` 로 확인하고,
`rag/config.py` 의 `GEMINI_MODEL` 을 바꾸면 됩니다.

`search.py`를 먼저 써보세요. RAG가 이상한 답을 하면 원인은 대개 생성이 아니라
검색이고, 이 스크립트로 어떤 청크가 딸려왔는지 바로 확인할 수 있습니다.

## 진행 단계

- [x] Phase 0 — 프로젝트 뼈대와 샘플 문서
- [x] Phase 1 — 인덱싱 (로드 → 청킹 → 임베딩 → 저장)
- [x] Phase 2 — 검색 (코사인 유사도 top-k)
- [x] Phase 3 — 생성 (Claude로 근거 기반 답변)
- [ ] Phase 4 — CLI 통합 및 대화형 모드
- [ ] Phase 5 — 하이브리드 검색(BM25)과 인용
- [ ] Phase 6 — 검색 품질 평가
