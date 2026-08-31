# RAG 연습 프로젝트

검색 증강 생성(Retrieval-Augmented Generation)을 밑바닥부터 단계별로 만들어보는 연습용 저장소입니다.
벡터 DB 라이브러리를 쓰지 않고 numpy로 직접 인덱스를 구현해서, 검색이 실제로
어떻게 동작하는지 눈으로 확인하는 것을 목표로 합니다.

## 스택

| 역할 | 선택 | 이유 |
|---|---|---|
| 임베딩 | `sentence-transformers` (로컬) | 무료·오프라인. Anthropic은 임베딩 API를 제공하지 않음 |
| 인덱스 | numpy 배열 + `.npz` | 코사인 유사도를 직접 구현해 원리를 학습 |
| 생성 | Claude Opus 5 (`anthropic` SDK) | 검색된 근거로 답변 작성 |

## 구조

```
rag/          핵심 모듈 (청킹 · 임베딩 · 저장 · 검색 · 생성)
scripts/      실행 진입점 (ingest, ask)
data/docs/    검색 대상 문서 (샘플: 가상 회사 '누리테크' 사내 핸드북)
index/        생성된 인덱스 (gitignore, ingest 실행 시 생성)
```

## 설치

```bash
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
# .venv\Scripts\activate         # Windows PowerShell
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt

cp .env.example .env             # 그리고 .env 에 ANTHROPIC_API_KEY 채우기
```

## 사용법

```bash
python scripts/ingest.py         # 문서를 청킹·임베딩해서 인덱스 생성
python scripts/ask.py "연차는 며칠인가요?"
```

## 진행 단계

- [x] Phase 0 — 프로젝트 뼈대와 샘플 문서
- [ ] Phase 1 — 인덱싱 (로드 → 청킹 → 임베딩 → 저장)
- [ ] Phase 2 — 검색 (코사인 유사도 top-k)
- [ ] Phase 3 — 생성 (Claude로 근거 기반 답변)
- [ ] Phase 4 — CLI 통합 및 대화형 모드
- [ ] Phase 5 — 하이브리드 검색(BM25)과 인용
- [ ] Phase 6 — 검색 품질 평가
