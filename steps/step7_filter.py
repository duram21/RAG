"""7단계: 메타데이터 필터 — 검색으로 풀 문제와 필터로 풀 문제 나누기

6단계에서 이걸 봤습니다.

    질문: 26.16 패치에서 아지르 어떻게 됐어?
      1위  [26.14] 아지르     ← 엉뚱한 패치
      2위  [26.16] 아지르     ← 이게 정답

메타데이터를 청크에 넣어도 못 고쳤습니다. 임베딩에게 "26.16" 과 "26.14" 는
거의 같은 문자열이기 때문입니다. 벡터 검색은 **비슷함**은 잘 재지만
**정확히 일치**는 못 합니다. 원리상 그렇습니다.

그래서 질문을 두 갈래로 쪼갭니다.

    "26.16 패치에서 아지르 어떻게 됐어?"
       │
       ├─ "26.16"          → 필터. 기계적으로 정확히 걸러낸다 (if 문 하나)
       └─ "아지르 어떻게"   → 검색. 의미로 비슷한 걸 찾는다 (벡터)

정확해야 하는 건 필터에게, 비슷하면 되는 건 검색에게 시키는 겁니다.
실무 RAG 에서 아주 자주 쓰는 구조입니다.
    "2023년 문서만"  "우리 팀 문서만"  "공개 등급만"  전부 같은 모양입니다.

실행:
    python steps/step7_filter.py
"""

import json
import sys
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "patches" / "patches.json"

if not DATA_PATH.exists():
    print("데이터가 없습니다. 먼저 실행하세요:  python steps/fetch_patches.py")
    raise SystemExit(1)

blocks = json.loads(DATA_PATH.read_text(encoding="utf-8"))
model = SentenceTransformer("intfloat/multilingual-e5-small")

# 우리가 가진 패치 목록. set 은 중복 없는 모음입니다.
# 리스트와 달리 순서가 없고, "안에 있나?" 확인이 아주 빠릅니다.
ALL_PATCHES = {b["patch"] for b in blocks}


# ===========================================================================
# TODO 1. 질문에서 패치 번호를 뽑아내세요.
#
#   우리가 가진 패치는 8개뿐입니다: 26.10 ~ 26.17
#   그러니 "이 중 하나가 질문 안에 들어있나?" 만 보면 됩니다.
#
#   문자열 안에 특정 글자가 있는지는 in 으로 확인합니다:
#       "26.16" in "26.16 패치에서 아지르 어떻게 됐어?"     →  True
#       "26.16" in "가렌 뭐 바뀌었어?"                      →  False
#
#   ALL_PATCHES 를 하나씩 돌면서 질문에 들어있는 걸 찾아 돌려주세요.
#   없으면 None 을 돌려주면 됩니다 (= 필터 안 함).
#
#   힌트:
#       for patch in ALL_PATCHES:
#           if patch in question:
#               return patch
#       return None
# ===========================================================================

def extract_patch(question: str):
    """질문에 패치 번호가 있으면 그 문자열을, 없으면 None 을 돌려준다."""
    for  patch in ALL_PATCHES:
        if patch in question:
            return patch
    return None  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. 필터를 적용한 검색을 완성하세요.
#
#   scores 는 128개짜리 배열이고 blocks 도 128개입니다. **순서가 같습니다.**
#       scores[5]  ↔  blocks[5]      같은 것을 가리킴
#
#   그러니 blocks 를 번호와 함께 훑으면서, 패치가 다르면
#   그 자리의 점수를 바닥으로 밀어버리면 됩니다.
#
#   바닥값으로는 -np.inf (음의 무한대) 를 씁니다.
#   유사도는 아무리 낮아도 -1 이므로, -무한대면 절대 상위권에 못 옵니다.
#
#   힌트:
#       for i, block in enumerate(blocks):
#           if block["patch"] != want_patch:
#               scores[i] = -np.inf
#
#   != 는 "같지 않다" 입니다. (== 의 반대)
# ===========================================================================

def search(question: str, vectors, k: int = 3, use_filter: bool = True):
    query_vec = model.encode(
        ["query: " + question], normalize_embeddings=True
    )[0]
    scores = vectors @ query_vec

    want_patch = extract_patch(question) if use_filter else None

    # 있는 경우 
    if want_patch is not None:
        # ↓↓↓ 여기를 채우세요 (반복문 한 덩어리) ↓↓↓
        for i, block in enumerate(blocks):
            if(block["patch"] != want_patch):
                scores[i] = -np.inf
        pass
        # ↑↑↑ 여기를 채우세요 ↑↑↑

    top = np.argsort(-scores)[:k]
    # 필터에 걸러진 것(-inf)은 결과에서 제외합니다.
    return [(float(scores[i]), blocks[i]) for i in top if scores[i] != -np.inf]


# ===========================================================================
# 여기부터는 실험용입니다. 고치지 않아도 됩니다.
# ===========================================================================

QUESTIONS = [
    "26.16 패치에서 아지르 어떻게 됐어?",
    "26.13 패치에서 도란의 투구 어떻게 바뀌었어?",
    "26.17 패치 변경점 알려줘",
    "가렌 뭐 바뀌었어?",              # ← 패치 번호 없음. 필터가 안 걸려야 정상
]


def main() -> None:
    if extract_patch("26.16 패치에서 아지르 어떻게 됐어?") is None:
        print("TODO 1 이 비어 있습니다. extract_patch 를 채우세요.")
        return

    print(f"\n보유 패치: {', '.join(sorted(ALL_PATCHES))}")
    print(f"블록 {len(blocks)}개를 임베딩합니다...")

    texts = [f"{b['patch']} 패치 - {b['name']}\n{b['text']}" for b in blocks]
    vectors = model.encode(["passage: " + t for t in texts], normalize_embeddings=True)

    for question in QUESTIONS:
        want = extract_patch(question)
        n_match = sum(1 for b in blocks if b["patch"] == want) if want else len(blocks)

        print("\n" + "=" * 66)
        print(f"질문: {question}")
        print(f"추출된 패치: {want or '(없음 — 필터 미적용)'}   후보 {n_match}개")
        print("=" * 66)

        for label, use_filter in [("필터 없음", False), ("필터 적용", True)]:
            print(f"\n  [{label}]")
            results = search(question, vectors, use_filter=use_filter)
            for rank, (score, b) in enumerate(results, start=1):
                mark = "  ←다른 패치" if want and b["patch"] != want else ""
                print(f"    {rank}위 {score:.4f}  [{b['patch']}] {b['name']}{mark}")

    print("\n" + "-" * 66)
    print("마지막 질문을 보세요. 패치 번호가 없으면 필터가 안 걸리고,")
    print("두 결과가 똑같아야 정상입니다. 필터는 있을 때만 작동해야 합니다.")


# ===========================================================================
# 더 해볼 것
#
#   1. "최신 패치에서 뭐 바뀌었어?" 는 지금 필터가 안 걸립니다.
#      "최신" / "이번" 같은 말을 max(ALL_PATCHES) 로 바꿔주면 됩니다.
#      extract_patch 에 조건 하나만 추가하면 되니 해보세요.
#
#   2. 챔피언 이름으로도 필터할 수 있습니다.
#      "가렌" 이 질문에 있으면 name == "가렌" 인 블록만 남기는 식입니다.
#      → 그런데 이건 위험합니다. "가렌 카운터 뭐야?" 같은 질문에서
#         가렌 블록만 남기면 정작 상대 챔피언 정보를 놓칩니다.
#         필터는 강력한 만큼, 잘못 걸면 정답을 아예 없애버립니다.
#
#   3. 필터로 후보가 0개가 되면 어떻게 해야 할까요?
#      지금 코드는 빈 결과를 돌려줍니다. 실무에서는 보통
#      "필터를 풀고 다시 검색" 하거나 "그 조건의 문서가 없다"고 알려줍니다.
# ===========================================================================


if __name__ == "__main__":
    main()
