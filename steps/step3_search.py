"""3단계: 검색기 완성 — 1단계 + 2단계를 실제 문서에 합치기

지금까지:
    1단계  글 → 벡터, 그리고 순위 매기기
    2단계  긴 문서 → 청크

이번에는 둘을 붙여서 **문서 4개 전체를 검색**합니다.
여기까지 하면 RAG 의 'R'(Retrieval, 검색) 이 끝납니다.
남는 건 검색 결과를 LLM 에게 넘기는 일뿐입니다.

이 단계에서 새로 배우는 것:
    1단계에서는 문서 5개에 대해 np.dot 을 5번 했습니다.
    청크가 수천 개면 그렇게 못 합니다.
    numpy 의 @ 연산자를 쓰면 **전부 한 번에** 계산됩니다.

실행:
    python steps/step3_search.py
"""

from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "docs"
MODEL_NAME = "intfloat/multilingual-e5-small"

MIN_CHUNK_LEN = 30   # 이보다 짧은 조각은 버린다 (2단계의 13자짜리 0번 조각 같은 것)

model = SentenceTransformer(MODEL_NAME)


# ===========================================================================
# TODO 1. 문서 4개를 모두 읽어서 청크 목록을 만드세요.
#
#   아래 반복문의 뼈대는 만들어 뒀습니다. 2단계에서 했던 두 줄만 채우면 됩니다.
#
#   반복문(for) 읽는 법:
#       for path in doc_paths:      ← doc_paths 에서 하나씩 꺼내 path 라 부르고
#           (들여쓴 내용 실행)        ← 그 아래를 매번 실행한다
#
#   chunks 의 각 원소는 (문서이름, 청크내용) 짝입니다.
#   나중에 "이 답이 어느 문서에서 나왔는지" 보여주려면 출처를 같이 들고 다녀야 합니다.
# ===========================================================================

doc_paths = sorted(DOCS_DIR.glob("*.md"))   # glob = 조건에 맞는 파일 찾기
chunks = []                                  # 빈 리스트로 시작

for path in doc_paths:
    raw = path.read_text(encoding="utf-8")        # ← 여기를 채우세요 (2단계 TODO 1 과 똑같습니다)
    sections = raw.split("\n##")   # ← 여기를 채우세요 (2단계 TODO 2 와 똑같습니다)

    if raw is None or sections is None:
        break         # 아직 안 채웠으면 반복문 중단

    for sec in sections:
        sec = sec.strip()              # 앞뒤 공백/줄바꿈 제거
        if len(sec) < MIN_CHUNK_LEN:
            continue                   # 너무 짧으면 건너뛴다
        chunks.append((path.name, sec))   # 리스트 끝에 추가


# ===========================================================================
# TODO 2. 모든 청크를 벡터로 만드세요.
#
#   1단계 TODO 4 의 doc_vecs 와 완전히 같습니다.
#   "passage: " 접두사를 붙여서 인코딩하면 됩니다.
#
#   chunk_texts 는 아래에 이미 만들어 뒀으니 그걸 쓰세요.
#   힌트:  model.encode(["passage: " + t for t in chunk_texts], normalize_embeddings=True)
# ===========================================================================

chunk_texts = [text for (doc_name, text) in chunks]

chunk_vectors = model.encode(["passage: " + t for t in chunk_texts], normalize_embeddings=True)  # ← 여기를 채우세요


# ===========================================================================
# TODO 3. 검색 함수를 완성하세요. 두 줄입니다.
#
#   (1) query_vec — 질문을 "query: " 접두사로 인코딩 (1단계 TODO 4 와 동일)
#
#   (2) scores — 모든 청크와의 유사도를 한 번에 계산
#
#       1단계에서는 이렇게 했습니다:
#           [np.dot(query_vec, v) for v in doc_vecs]     ← 하나씩 5번
#
#       청크가 수천 개면 이 방식은 느립니다. numpy 에는 @ 연산자가 있습니다:
#           scores = chunk_vectors @ query_vec           ← 전부 한 번에
#
#       모양(shape)으로 보면:
#           chunk_vectors  (청크수, 384)
#           query_vec      (384,)
#           결과           (청크수,)      ← 청크마다 점수 하나씩
#
#       @ 는 행렬곱입니다. 각 행(청크 벡터)과 query_vec 을 내적한 결과를
#       한 줄로 쭉 뽑아줍니다. 즉 위의 반복문과 결과는 같고, 훨씬 빠릅니다.
#
#       **검색 엔진의 핵심이 이 한 줄입니다.**
# ===========================================================================

def search(question: str, k: int = 3):
    query_vec = model.encode(["query: " + question], normalize_embeddings=True)[0]   # ← (1) 여기를 채우세요
    scores = chunk_vectors @ query_vec     # ← (2) 여기를 채우세요

    if query_vec is None or scores is None:
        return None

    # np.argsort 는 "정렬했을 때의 순서(번호)"를 돌려줍니다.
    #   np.argsort([0.3, 0.9, 0.5])  →  [0, 2, 1]   (작은 것부터의 위치)
    # -scores 로 부호를 뒤집으면 큰 것부터가 됩니다. [:k] 는 앞에서 k개만.
    top_indices = np.argsort(-scores)[:k]

    return [(float(scores[i]), chunks[i][0], chunks[i][1]) for i in top_indices]


# ===========================================================================
# 여기부터는 결과 출력용입니다. 고치지 않아도 됩니다.
# ===========================================================================

QUESTIONS = [
    "연차 휴가 며칠 쓸 수 있어?",
    "금요일에 배포해도 되나요?",
    "노트북을 잃어버렸어요",
    "택시비도 정산되나요?",
    "회사 주차장은 몇 층인가요?",   # ← 문서에 답이 없는 질문
]


def main() -> None:
    if not chunks:
        print("TODO 1 이 비어 있습니다. raw 와 sections 를 채우세요.")
        return

    print(f"\n문서 {len(doc_paths)}개 → 청크 {len(chunks)}개")
    for path in doc_paths:
        n = sum(1 for doc_name, _ in chunks if doc_name == path.name)
        print(f"  {path.name}: {n}개")

    if chunk_vectors is None:
        print("\nTODO 2 가 비어 있습니다. chunk_vectors 를 채우세요.")
        return

    print(f"\n벡터 모양: {chunk_vectors.shape}  (청크 {chunk_vectors.shape[0]}개 × 숫자 {chunk_vectors.shape[1]}개)")

    if search(QUESTIONS[0]) is None:
        print("\nTODO 3 이 비어 있습니다. query_vec 과 scores 를 채우세요.")
        return

    for question in QUESTIONS:
        print("\n" + "=" * 62)
        print(f"질문: {question}")
        print("=" * 62)
        for rank, (score, doc_name, text) in enumerate(search(question), start=1):
            title = text.splitlines()[0]
            body = " ".join(text.splitlines()[1:])[:60]
            print(f"  {rank}위  {score:.4f}  [{doc_name}] {title}")
            print(f"           {body}...")

    print("\n" + "-" * 62)
    print("마지막 질문(주차장)을 보세요. 문서에 답이 없는데도 뭔가가 1위로 나옵니다.")
    print("검색은 '가장 비슷한 것'을 돌려줄 뿐, '답이 있는지'는 판단하지 않습니다.")
    print("그 판단은 4단계에서 LLM 에게 맡깁니다.")


if __name__ == "__main__":
    main()
