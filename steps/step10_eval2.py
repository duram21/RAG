"""10단계: 평가셋 고치기 — 지표를 속이지 못하게 만들기

9단계에서 BOOST 를 키우자 정확도가 12 → 15 → 7 로 올랐다 떨어졌습니다.
그런데 더 중요한 걸 발견했죠.

    지금 평가셋은 전부 "최근에 뭐 바뀌었어?" 질문뿐입니다.

이러면 "무조건 최신 패치 블록을 반환하라" 는 엉터리 시스템이 만점을 받습니다.
평가는 만점인데 실제로는 쓸모없는 물건이 되는 겁니다.

    **지표를 만들면 사람은 그 지표를 속이는 방향으로 최적화하게 됩니다.**
    (사람만이 아니라 모델도, 그리고 우리 자신도 그렇습니다)

그래서 평가셋에 **반대 방향 질문**을 섞습니다.

    최신형 질문  "그웬 최근에 뭐 바뀌었어?"   → 최신 패치가 나와야 함
    일반형 질문  "그웬 스킬 어떻게 바뀌었어?"  → 챔피언만 맞으면 됨.
                                                가산점이 방해하면 안 됨

두 지표를 따로 재면, 한쪽을 올리려다 다른 쪽을 망가뜨리는 게 바로 보입니다.
좋은 평가셋은 **원하는 것만 통과시키는 게 아니라, 원하지 않는 것을 걸러냅니다.**

실행:
    python steps/step10_eval2.py
"""

import collections
import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "patches" / "patches.json"

if not DATA_PATH.exists():
    print("데이터가 없습니다. 먼저:  python steps/fetch_patches.py")
    raise SystemExit(1)

blocks = json.loads(DATA_PATH.read_text(encoding="utf-8"))
model = SentenceTransformer("intfloat/multilingual-e5-small")

ALL_PATCHES = sorted({b["patch"] for b in blocks})
OLDEST, NEWEST = ALL_PATCHES[0], ALL_PATCHES[-1]
RECENCY_WORDS = ["최근", "최신", "이번", "방금", "요즘"]


def wants_recent(question: str) -> bool:
    return any(word in question for word in RECENCY_WORDS)


def recency_score(patch: str) -> float:
    n = int(patch.split(".")[1])
    oldest = int(OLDEST.split(".")[1])
    newest = int(NEWEST.split(".")[1])
    return (n - oldest) / (newest - oldest)


def search(question: str, vectors, k: int = 3, boost: float = 0.05):
    query_vec = model.encode(["query: " + question], normalize_embeddings=True)[0]
    scores = vectors @ query_vec

    if wants_recent(question) and boost > 0:
        for i, block in enumerate(blocks):
            scores[i] += boost * recency_score(block["patch"])

    top = np.argsort(-scores)[:k]
    return [(float(scores[i]), blocks[i]) for i in top]


# ===========================================================================
# 평가셋 만들기
#
#   여러 패치에 등장한 챔피언들로 두 종류의 질문을 자동 생성합니다.
#   손으로 쓰면 좋겠지만 22개 × 2 = 44개라 기계로 만듭니다.
#   (실무에서는 손으로 쓴 것과 섞어 씁니다. 기계로 만든 질문은
#    표현이 단조로워서 실제 사용자 말투를 못 담거든요.)
# ===========================================================================

def build_eval_set():
    counts = collections.Counter(b["name"] for b in blocks)
    targets = sorted(n for n, c in counts.items() if c >= 2)

    recent_q, plain_q = [], []
    for name in targets:
        latest = max(b["patch"] for b in blocks if b["name"] == name)
        # 최신형: 최신 패치 블록이 1위여야 정답
        recent_q.append((f"{name} 최근에 뭐 바뀌었어?", name, latest))
        # 일반형: 챔피언만 맞으면 정답 (어느 패치든 상관없음)
        plain_q.append((f"{name} 어떻게 바뀌었어?", name, None))

    return recent_q, plain_q


# ===========================================================================
# TODO 1. 검색 결과 1위가 정답인지 판정하세요.
#
#   want_patch 가 있으면  → 이름도 맞고 패치도 맞아야 정답
#   want_patch 가 None 이면 → 이름만 맞으면 정답
#
#   results 는 [(점수, block), ...] 이고, 1위는 results[0] 입니다.
#   거기서 block 만 꺼내려면 results[0][1] 입니다.
#       results[0]     →  (0.89, {"patch":..., "name":...})
#       results[0][1]  →  {"patch":..., "name":...}
#
#   힌트:
#       top = results[0][1]
#       if top["name"] != want_name:
#           return False
#       if want_patch is not None and top["patch"] != want_patch:
#           return False
#       return True
# ===========================================================================

def is_hit(results, want_name: str, want_patch) -> bool:
    top = results[0][1]
    if top["name"] != want_name:
        return False
    if want_patch is not None and top["patch"] != want_patch:
        return False
    return True  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. 질문 묶음 하나의 정확도를 계산하세요.
#
#   questions 는 (질문, 정답이름, 정답패치) 짝들의 리스트입니다.
#   전부 검색해서 맞은 개수를 세고, 비율로 돌려주세요.
#
#   5단계 recall_at 과 같은 모양입니다.
#
#   힌트:
#       hits = 0
#       for question, want_name, want_patch in questions:
#           results = search(question, vectors, k=1, boost=boost)
#           if is_hit(results, want_name, want_patch):
#               hits += 1
#       return hits / len(questions)
# ===========================================================================

def accuracy(questions, vectors, boost: float) -> float:
    hits = 0
    for question, want_name, want_patch in questions:
        results = search(question, vectors, k = 1, boost= boost)
        if is_hit(results, want_name, want_patch):
            hits += 1

    return hits/len(questions)  # ← 여기를 채우세요


# ===========================================================================
# 여기부터는 결과 출력용입니다. 고치지 않아도 됩니다.
# ===========================================================================

def main() -> None:
    recent_q, plain_q = build_eval_set()
    print(f"\n평가셋: 최신형 {len(recent_q)}개 + 일반형 {len(plain_q)}개")
    print(f"  최신형 예:  {recent_q[0][0]}   → 정답 [{recent_q[0][2]}] {recent_q[0][1]}")
    print(f"  일반형 예:  {plain_q[0][0]}   → 정답 {plain_q[0][1]} (패치 무관)")

    print(f"\n블록 {len(blocks)}개 임베딩 중...")
    texts = [f"{b['patch']} 패치 - {b['name']}\n{b['text']}" for b in blocks]
    vectors = model.encode(["passage: " + t for t in texts], normalize_embeddings=True)

    if not is_hit([(0.9, blocks[0])], blocks[0]["name"], None):
        print("\nTODO 1 이 비어 있습니다. is_hit 를 채우세요.")
        return

    if accuracy(recent_q[:2], vectors, 0.05) == 0.0:
        print("\nTODO 2 가 비어 있습니다. accuracy 를 채우세요.")
        return

    print("\n" + "=" * 64)
    print("BOOST      최신형      일반형      평균")
    print("=" * 64)

    rows = []
    for boost in [0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30]:
        r = accuracy(recent_q, vectors, boost)
        p = accuracy(plain_q, vectors, boost)
        avg = (r + p) / 2
        rows.append((boost, r, p, avg))
        print(
            f"  {boost:.2f}    {r:6.1%}      {p:6.1%}      {avg:6.1%}   "
            f"{'#' * int(avg * 30)}"
        )

    best = max(rows, key=lambda row: row[3])
    print("\n" + "-" * 64)
    print(f"평균이 가장 높은 지점: BOOST {best[0]:.2f}  (평균 {best[3]:.1%})")
    print("\n9단계에서는 최신형만 재서 0.05 가 정점이었습니다.")
    print("일반형까지 넣으면 그림이 어떻게 달라지는지 보세요.")


# ===========================================================================
# 생각해볼 것
#
#   1. 일반형 정확도는 BOOST 를 키울수록 어떻게 되나요?
#      "최근"이 없으면 wants_recent 가 False 라 가산점이 아예 안 붙습니다.
#      그러니 이론상 BOOST 와 무관하게 일정해야 합니다.
#      → 실제로 그런가요? 그렇다면 이 평가셋도 아직 부족한 겁니다.
#         "가산점이 켜진 상태에서 무해한가" 를 재려면
#         **"최근"이 붙었지만 최신이 정답이 아닌 질문**이 필요합니다.
#         예: "그웬 최근 아닌 예전 변경점" — 만들기가 꽤 까다롭습니다.
#
#   2. 평균을 최고로 만드는 게 정답일까요?
#      최신형과 일반형 중 어느 쪽이 더 중요한지는 **쓰는 사람**이 정합니다.
#      "패치 노트 도우미"라면 최신형이 훨씬 자주 들어올 겁니다.
#      그렇다면 단순 평균이 아니라 가중치를 줘야 합니다.
#      → 평가 지표를 정하는 건 기술 문제가 아니라 제품 문제입니다.
#
#   3. 이 평가셋의 남은 약점은?
#      - 질문을 기계로 찍어내서 표현이 단조롭습니다.
#        실제 사용자는 "그웬 왜 이렇게 쎄짐?" 같이 씁니다.
#      - 여러 패치에 등장한 챔피언만 다룹니다. 한 번만 나온 챔피언은 뺐습니다.
#      - 정답을 하나만 인정합니다. 5단계에서 만난 문제와 같습니다.
# ===========================================================================


if __name__ == "__main__":
    main()
