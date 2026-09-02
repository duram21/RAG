"""9단계: 최신성 — "최근에 뭐 바뀌었어?" 를 제대로 답하기

직접 발견하신 문제입니다.

    "그웬 최근에 뭐 바뀌었어?"
      1위  [26.12] 그웬  (0.893)     ← 4패치나 지난 것
      2위  [26.16] 그웬  (0.873)     ← 이게 최근인데

여러 패치에 등장하는 챔피언 22개로 재봤더니 **최신이 1위로 나온 건 12/22.**
동전 던지기입니다. "최근" 이라는 단어가 검색에 아무 영향을 못 줬습니다.

임베딩은 시간 개념이 없습니다. "26.16" 이 "26.12" 보다 나중이라는 걸 모릅니다.
순위는 순전히 "어느 글이 질문과 더 비슷하게 생겼나" 로 정해집니다.

7단계와 같은 결론입니다 — **검색이 못 하는 일은 검색 밖에서 처리한다.**
다만 이번엔 방법이 다릅니다.

    7단계 (패치 지정)  →  **필터**. 아닌 건 아예 후보에서 제외
    9단계 (최신 선호)  →  **가산점**. 최신일수록 점수를 조금 더 준다

왜 필터가 아니라 가산점이냐면, "최신 패치만" 으로 잘라버리면 그웬이
26.17 에 없을 때 결과가 0개가 되기 때문입니다. 최신을 **선호**하되
관련성을 완전히 무시하진 않아야 합니다.

실행:
    python steps/step9_recency.py
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


# ===========================================================================
# TODO 1. 질문이 "최신"을 원하는지 판단하세요.
#
#   이런 말이 들어있으면 최신을 원하는 겁니다:
#       최근, 최신, 이번, 방금, 요즘
#
#   질문에 이 중 하나라도 들어있으면 True, 아니면 False 를 돌려주세요.
#
#   힌트 — any() 를 쓰면 한 줄입니다:
#       any(word in question for word in WORDS)
#
#   any() 는 "하나라도 True 면 True" 입니다.
#       any([False, False, True])   →  True
#       any([False, False, False])  →  False
#
#   반복문으로 쓰셔도 똑같습니다:
#       for word in RECENCY_WORDS:
#           if word in question:
#               return True
#       return False
# ===========================================================================

RECENCY_WORDS = ["최근", "최신", "이번", "방금", "요즘"]


def wants_recent(question: str) -> bool:
    flag = any(word in question for word in RECENCY_WORDS)
    return flag  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. 패치 번호를 0.0 ~ 1.0 사이의 "최신도" 로 바꾸세요.
#
#   가장 오래된 패치가 0.0, 가장 최신이 1.0 이 되게 만듭니다.
#
#       26.10  →  0.0     (OLDEST)
#       26.13  →  0.43
#       26.17  →  1.0     (NEWEST)
#
#   패치 문자열에서 뒷자리 숫자만 떼어내면 계산할 수 있습니다.
#
#       "26.14".split(".")      →  ["26", "14"]
#       "26.14".split(".")[1]   →  "14"          ← 아직 글자입니다
#       int("14")               →  14            ← 이제 숫자
#
#   int() 는 글자를 숫자로 바꿔줍니다. 글자끼리는 뺄셈이 안 되니 필요합니다.
#
#   세 개를 다 숫자로 바꾼 뒤 이렇게 계산하면 됩니다:
#
#       (지금 - 가장오래된) / (가장최신 - 가장오래된)
#
#       26.14 라면  (14 - 10) / (17 - 10) = 4 / 7 = 0.571
# ===========================================================================

def recency_score(patch: str) -> float:
    """가장 오래된 패치는 0.0, 가장 최신 패치는 1.0."""
    # 26.10 -> 0.0
    # 26.17 -> 1.0
    a, b = patch.split(".")
    oldest = int(OLDEST.split(".")[1])
    newest = int(NEWEST.split(".")[1])

    b = int(b)
    return (b-oldest) / (newest-oldest) # ← 여기를 채우세요


# ===========================================================================
# TODO 3. 검색에 가산점을 반영하세요.
#
#   질문이 최신을 원할 때만, 각 블록의 점수에 최신도를 더합니다.
#
#       scores[i] = scores[i] + BOOST * recency_score(블록의 패치)
#
#   BOOST 는 "최신성을 얼마나 중요하게 볼지" 를 정하는 손잡이입니다.
#       0 이면      최신성 무시 (지금까지와 동일)
#       너무 크면   관련성 무시하고 무조건 최신 것만
#
#   적당한 값은 데이터를 보고 정해야 합니다. 아래 실험이 도와줍니다.
#
#   힌트:
#       for i, block in enumerate(blocks):
#           scores[i] += boost * recency_score(block["patch"])
#
#   += 는 "기존 값에 더하기" 입니다.  a += 3  은  a = a + 3  과 같습니다.
# ===========================================================================

def search(question: str, vectors, k: int = 3, boost: float = 0.10):
    query_vec = model.encode(["query: " + question], normalize_embeddings=True)[0]
    scores = vectors @ query_vec

    if wants_recent(question) and boost > 0:
        # ↓↓↓ 여기를 채우세요 ↓↓↓
        for i, block in enumerate(blocks):
            scores[i] += boost * recency_score(block["patch"])
        pass

        # ↑↑↑ 여기를 채우세요 ↑↑↑

    top = np.argsort(-scores)[:k]
    return [(float(scores[i]), blocks[i]) for i in top]


# ===========================================================================
# 여기부터는 실험용입니다. 고치지 않아도 됩니다.
#
# 5단계에서 배운 걸 그대로 씁니다 — 바꿨으면 재본다.
# 여러 패치에 등장하는 챔피언들에게 "최근에 뭐 바뀌었어?" 를 물어서,
# 최신 패치 블록이 1위로 나오는 비율을 BOOST 값별로 측정합니다.
# ===========================================================================

def evaluate(vectors, boost: float) -> tuple[int, int, list]:
    counts = collections.Counter(b["name"] for b in blocks)
    targets = [n for n, c in counts.items() if c >= 2]

    hits, misses = 0, []
    for name in targets:
        results = search(f"{name} 최근에 뭐 바뀌었어?", vectors, k=1, boost=boost)
        got = results[0][1]

        # 이 챔피언이 등장한 패치 중 가장 최신
        latest = max(b["patch"] for b in blocks if b["name"] == name)

        if got["name"] == name and got["patch"] == latest:
            hits += 1
        else:
            misses.append((name, latest, got["patch"], got["name"]))

    return hits, len(targets), misses


def main() -> None:
    if not wants_recent("그웬 최근에 뭐 바뀌었어?"):
        print("TODO 1 이 비어 있습니다. wants_recent 를 채우세요.")
        return

    if recency_score(NEWEST) == recency_score(OLDEST):
        print("TODO 2 가 비어 있습니다. recency_score 를 채우세요.")
        return

    print(f"\n패치 범위: {OLDEST} ~ {NEWEST}")
    print("최신도 변환 확인:")
    for p in ALL_PATCHES:
        bar = "#" * int(recency_score(p) * 30)
        print(f"  {p}  {recency_score(p):.3f}  {bar}")

    print(f"\n블록 {len(blocks)}개 임베딩 중...")
    texts = [f"{b['patch']} 패치 - {b['name']}\n{b['text']}" for b in blocks]
    vectors = model.encode(["passage: " + t for t in texts], normalize_embeddings=True)

    print("\n" + "=" * 60)
    print("BOOST 값을 바꿔가며 정확도 측정")
    print("=" * 60)

    last_misses = None
    for boost in [0.0, 0.01, 0.02, 0.05, 0.10, 0.30]:
        hits, total, misses = evaluate(vectors, boost)
        bar = "#" * int(hits / total * 40)
        note = "  ← 가산점 없음(기존)" if boost == 0 else ""
        print(f"  BOOST {boost:.2f}   {hits:2d}/{total}  {bar}{note}")
        if boost == 0.05:
            last_misses = misses

    if last_misses:
        print(f"\nBOOST 0.05 에서 아직 틀린 것 {len(last_misses)}개:")
        for name, latest, got_patch, got_name in last_misses:
            print(f"  {name:12s} 정답 {latest} → 나온 것 [{got_patch}] {got_name}")


# ===========================================================================
# 다 돌린 뒤에 생각해볼 것
#
#   1. BOOST 를 키우면 정확도가 계속 오르나요? 어디서 멈추나요?
#      아주 크게 하면 100% 가 될 것 같지만, 그건 "관련성을 완전히 버리고
#      무조건 최신 블록을 집는" 상태입니다. 이 평가에서는 만점이지만
#      실제로는 엉뚱한 챔피언을 물어와도 최신이면 1위가 됩니다.
#
#      → **평가 점수를 올리는 것과 좋아지는 것은 다릅니다.**
#         지표를 만들면 사람은 그 지표를 속이는 방향으로 최적화하게 됩니다.
#         평가셋에 "최근" 이 없는 질문도 섞어야 이걸 잡아낼 수 있습니다.
#
#   2. 지금 방식의 허점은 무엇일까요?
#      - "최근" 이 없어도 사람은 대개 최신을 원합니다 ("그웬 뭐 바뀌었어?")
#      - "26.12 때 그웬 어땠어?" 처럼 옛것을 콕 집어 묻는 경우도 있습니다
#        (이건 7단계 필터가 처리합니다)
#      - RECENCY_WORDS 목록에 없는 표현은 못 잡습니다 ("요새", "지난주")
#
#   3. 진짜 해법은 무엇일까요?
#      실무에서는 질문의 **의도**를 LLM 에게 먼저 물어보는 방법을 씁니다.
#      "이 질문은 최신을 원하는가? 특정 패치를 원하는가?" 를 판단하게 한 뒤
#      그 결과로 검색 조건을 정하는 거죠. 단어 목록보다 훨씬 유연합니다.
#      대신 LLM 호출이 한 번 더 늘어 느려지고 비용이 듭니다. 트레이드오프입니다.
# ===========================================================================


if __name__ == "__main__":
    main()
