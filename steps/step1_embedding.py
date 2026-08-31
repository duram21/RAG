"""1단계: 임베딩 — 글을 숫자로 바꾸기

RAG의 출발점입니다. 컴퓨터는 "연차"와 "휴가"가 비슷한 말이라는 걸 모릅니다.
그래서 먼저 문장을 **숫자 목록(벡터)** 으로 바꿉니다.
이때 의미가 비슷한 문장은 비슷한 숫자가 나오도록 학습된 모델을 씁니다.

이 단계에서 눈으로 확인할 것:
    "휴가 며칠 쓸 수 있어?" 와 "연차 휴가는 15일입니다" 는
    **겹치는 단어가 '휴가' 뿐인데도** 점수가 높게 나온다.
    이게 키워드 검색(Ctrl+F)과 결정적으로 다른 점입니다.

실행:
    python steps/step1_embedding.py
"""

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"

sentences = [
    "연차 휴가는 15일입니다",          # 0
    "휴가를 며칠이나 쓸 수 있나요?",    # 1  ← 0번과 의미가 비슷 (단어는 거의 안 겹침)
    "배포는 화요일과 목요일에 합니다",  # 2  ← 0번과 무관
]


# ===========================================================================
# TODO 1. 모델을 불러오세요.
#
#   SentenceTransformer 에 MODEL_NAME 을 넘기면 됩니다.
#   처음 실행하면 모델을 내려받느라 1~2분 걸립니다. 두 번째부터는 빠릅니다.
# ===========================================================================

model = SentenceTransformer(MODEL_NAME)  # ← 여기를 고치세요


# ===========================================================================
# TODO 2. 문장들을 벡터로 바꾸세요.
#
#   model.encode(...) 를 쓰면 됩니다. 인자 두 개를 넘기세요.
#     - 첫 번째: 위의 sentences 리스트
#     - normalize_embeddings=True
#
#   normalize_embeddings 는 모든 벡터의 "길이"를 1로 맞춰줍니다.
#   왜 필요한지는 TODO 3 에서 바로 드러납니다.
# ===========================================================================

vectors = model.encode(sentences, normalize_embeddings=True)  # ← 여기를 고치세요


# ===========================================================================
# TODO 3. 0번 문장과 1번 문장의 유사도를 구하세요.
#
#   길이가 1인 벡터 두 개는 **내적(dot product)이 곧 코사인 유사도**입니다.
#   numpy 로는 np.dot(a, b) 입니다.
#
#   결과는 -1 ~ 1 사이 값이고, 1에 가까울수록 비슷하다는 뜻입니다.
# ===========================================================================

sim_0_1 = np.dot(vectors[0], vectors[1])  # 0번 ↔ 1번 (비슷할 것)
sim_0_2 = np.dot(vectors[0], vectors[2])  # 0번 ↔ 2번 (안 비슷할 것)  ← 같은 방법으로 하나 더


# ===========================================================================
# 여기부터는 결과를 보여주는 부분입니다. 고치지 않아도 됩니다.
# ===========================================================================

def main() -> None:
    if model is None:
        print("TODO 1 이 아직 비어 있습니다. model 을 채우세요.")
        return

    if vectors is None:
        print("TODO 2 가 아직 비어 있습니다. vectors 를 채우세요.")
        return

    print(f"\n문장 {len(sentences)}개를 벡터로 바꿨습니다.")
    print(f"vectors 의 모양(shape): {vectors.shape}")
    print(f"  → 문장 {vectors.shape[0]}개 × 숫자 {vectors.shape[1]}개\n")

    print("0번 문장의 벡터, 앞 8개만 미리보기:")
    print(f"  {np.round(vectors[0][:8], 3)}  ... (총 {vectors.shape[1]}개)\n")

    print(f"길이 확인: {np.linalg.norm(vectors[0]):.6f}")
    print("  → 1.0 이면 normalize_embeddings=True 가 잘 들어간 것입니다.\n")

    if sim_0_1 is None or sim_0_2 is None:
        print("TODO 3 이 아직 비어 있습니다. sim_0_1, sim_0_2 를 채우세요.")
        return

    print("-" * 55)
    print(f"[0] {sentences[0]}")
    print(f"[1] {sentences[1]}")
    print(f"    유사도 = {sim_0_1:.4f}   ← 겹치는 단어는 '휴가' 뿐인데도 높음")
    print()
    print(f"[0] {sentences[0]}")
    print(f"[2] {sentences[2]}")
    print(f"    유사도 = {sim_0_2:.4f}   ← 무관하므로 낮음")
    print("-" * 55)

    gap = sim_0_1 - sim_0_2
    if sim_0_1 > sim_0_2:
        print(f"\n의미가 비슷한 쪽이 높긴 합니다. 그런데 차이가 {gap:+.4f} 뿐입니다.")
        print("전혀 무관한 문장도 0.87 을 받았습니다. 이게 이 단계의 진짜 교훈입니다.")
        print("→ 아래 TODO 4 로 내려가세요.")
    else:
        print("\n어라, 결과가 예상과 다릅니다. TODO 3 을 다시 확인해보세요.")

    rank_demo()


# ===========================================================================
# TODO 4. 점수는 "절대값"이 아니라 "순위"로 읽는 것임을 확인하기
#
#   위에서 봤듯 이 모델의 점수는 0.8~0.9 좁은 구간에 몰립니다.
#   그래서 "0.8 넘으면 관련 있음" 같은 기준은 통하지 않습니다.
#   대신 여러 후보를 놓고 **누가 제일 높은지** 를 봐야 합니다.
#
#   그리고 이번엔 e5 모델이 요구하는 접두사를 제대로 붙입니다.
#     - 질문에는 "query: "
#     - 문서에는 "passage: "
#   검색은 "질문 ↔ 답이 든 문서" 를 맞추는 비대칭 작업이라,
#   모델이 두 역할을 구분하도록 학습되어 있습니다.
#
#   할 일 두 가지:
#     (1) query_vec — question 앞에 "query: " 를 붙여서 인코딩
#     (2) doc_vecs  — documents 의 각 문장 앞에 "passage: " 를 붙여서 인코딩
#
#   힌트 (1): 문자열은 + 로 이어붙입니다.       "query: " + question
#             encode 는 리스트를 받아 리스트를 돌려주므로
#             ["..."] 로 감싸서 넣고, 결과는 [0] 으로 하나만 꺼내세요.
#
#   힌트 (2): 리스트의 모든 항목 앞에 붙이려면 리스트 컴프리헨션을 씁니다.
#             ["passage: " + d for d in documents]
#             이번엔 5개가 통째로 필요하니 [0] 은 붙이지 마세요.
# ===========================================================================

question = "노트북 분실하면 ?"

documents = [
    "연차 휴가는 15일이며 근속에 따라 최대 25일까지 늘어납니다",
    "병가는 연 10일까지 유급으로 사용할 수 있습니다",
    "배포는 화요일과 목요일 오후 2시에 진행합니다",
    "노트북 분실 시 즉시 보안팀에 신고해야 합니다",
    "야근 식대는 1인당 15,000원까지 지원됩니다",
]


query_vec = model.encode(["query: " + question], normalize_embeddings=True)[0]   # ← (1) 여기를 채우세요
doc_vecs = model.encode(["passage: " + d for d in documents], normalize_embeddings=True)    # ← (2) 여기를 채우세요


# ===========================================================================
# 여기부터도 결과 출력용입니다. 고치지 않아도 됩니다.
# ===========================================================================

def rank_demo() -> None:
    if query_vec is None or doc_vecs is None:
        print("\n[TODO 4] query_vec, doc_vecs 를 채우면 순위 비교가 실행됩니다.")
        return

    print("\n" + "=" * 58)
    print(f"질문: {question}")
    print("=" * 58)

    # 문서마다 질문과의 유사도를 구해 (점수, 문서) 쌍으로 묶는다.
    scored = [
        (float(np.dot(query_vec, dv)), doc)
        for dv, doc in zip(doc_vecs, documents)
    ]

    scored.sort(reverse=True)   # 점수 높은 순 (reverse=True 가 내림차순)

    for rank, (score, doc) in enumerate(scored, start=1):
        mark = "   ← 1위" if rank == 1 else ""
        print(f"  {rank}위  {score:.4f}  {doc[:30]}...{mark}")

    best, worst = scored[0][0], scored[-1][0]
    print(f"\n1위 {best:.4f} / 꼴찌 {worst:.4f} — 전체 폭이 {best - worst:.4f} 밖에 안 됩니다.")
    print("점수는 다 고만고만한데 순위는 정확합니다.")
    print("그래서 벡터 검색은 '몇 점 이상'이 아니라 '상위 몇 개'로 씁니다.")


if __name__ == "__main__":
    main()
