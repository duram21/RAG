"""6단계: 실제 데이터 — 롤 패치노트 128개 블록 검색하기

샘플 문서(19청크)에서 실제 데이터(128블록)로 옮겨갑니다.
데이터가 커지고 지저분해지면 어떤 문제가 생기는지 직접 보는 게 목적입니다.

먼저 데이터를 받아오세요:
    python steps/fetch_patches.py

그다음:
    python steps/step6_patch_search.py

이 단계의 질문:
    "청크 텍스트에 무엇을 넣을 것인가?"

    지금까지는 문서 내용을 그대로 임베딩했습니다. 그런데 패치노트에는
    본문 말고도 중요한 정보가 붙어 있습니다 — 어느 패치인지, 누구 얘기인지.

    아지르 블록의 본문은 이렇게 시작합니다:
        "집중 공격이 아지르의 주요 핵심 룬으로 떠오른 만큼..."

    다행히 '아지르'가 본문에 들어 있습니다. 그런데 이런 블록도 있습니다:
        "기본 능력치
         - 마나: 339 ⇒ 375"

    누구 얘긴지 본문만 봐서는 알 수 없습니다. 이름은 HTML 의 h3 태그에만
    있었고, 우리는 그걸 name 필드에 따로 담아뒀습니다.

    이런 정보를 **메타데이터**라고 합니다. 그리고 메타데이터를 청크 텍스트에
    합쳐서 임베딩할지 말지는 RAG 설계에서 자주 나오는 갈림길입니다.
    이번 단계에서 양쪽을 다 만들어 비교합니다.
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


# ===========================================================================
# TODO 1. 메타데이터를 붙인 청크 텍스트를 만드세요.
#
#   block 은 이렇게 생긴 딕셔너리입니다:
#       {"patch": "26.16", "name": "아지르", "text": "아지르\n집중 공격이..."}
#
#   딕셔너리에서 값을 꺼낼 땐 대괄호에 열쇠(key)를 넣습니다:
#       block["patch"]   →  "26.16"
#       block["name"]    →  "아지르"
#       block["text"]    →  "아지르\n집중 공격이..."
#
#   이 셋을 합쳐서 아래 모양의 문자열 하나를 만들어 돌려주세요:
#
#       26.16 패치 - 아지르
#       아지르
#       집중 공격이 아지르의...
#
#   즉 첫 줄에 "<패치> 패치 - <이름>" 을 넣고, 줄바꿈 후 본문을 붙입니다.
#
#   힌트: f-string 안에서도 줄바꿈은 \n 입니다.
#       f"{a} 패치 - {b}\n{c}"
# ===========================================================================

def build_text_with_meta(block: dict) -> str:
    return ""  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. 검색 함수를 완성하세요. 3단계에서 하신 것과 같습니다.
#
#   (1) query_vec — 질문을 "query: " 접두사로 인코딩하고 [0] 으로 꺼내기
#   (2) scores    — vectors @ query_vec
#
#   달라진 점은 vectors 를 인자로 받는다는 것뿐입니다.
#   메타데이터 있는 버전과 없는 버전을 같은 함수로 검색하려고 그렇게 했습니다.
# ===========================================================================

def search(question: str, vectors, k: int = 3):
    query_vec = None   # ← (1) 여기를 채우세요
    scores = None      # ← (2) 여기를 채우세요

    if query_vec is None or scores is None:
        return None

    top = np.argsort(-scores)[:k]
    return [(float(scores[i]), blocks[i]) for i in top]


# ===========================================================================
# 여기부터는 실험용입니다. 고치지 않아도 됩니다.
# ===========================================================================

QUESTIONS = [
    ("가렌 뭐 바뀌었어?",            "챔피언 이름으로 찾기"),
    ("26.16 패치에서 아지르 어떻게 됐어?", "패치 번호까지 지정"),
    ("체력이 너프된 챔피언 알려줘",     "이름 없이 의미로만 찾기"),
    ("도란의 투구 변경점",            "아이템 이름으로 찾기"),
]


def embed(texts: list[str]):
    return model.encode(
        ["passage: " + t for t in texts], normalize_embeddings=True
    )


def main() -> None:
    sample = build_text_with_meta(blocks[0])
    if not sample:
        print("TODO 1 이 비어 있습니다. build_text_with_meta 를 채우세요.")
        return

    print("\n=== TODO 1 결과 확인 ===")
    print(sample[:200] + "...\n")

    print(f"블록 {len(blocks)}개를 두 가지 방식으로 임베딩합니다...")

    # 방식 A: 본문만 (지금까지 해온 방식)
    plain_vectors = embed([b["text"] for b in blocks])

    # 방식 B: 메타데이터 + 본문 (TODO 1 의 결과)
    meta_vectors = embed([build_text_with_meta(b) for b in blocks])

    if search(QUESTIONS[0][0], plain_vectors) is None:
        print("\nTODO 2 가 비어 있습니다. query_vec 과 scores 를 채우세요.")
        return

    for question, note in QUESTIONS:
        print("\n" + "=" * 66)
        print(f"질문: {question}")
        print(f"({note})")
        print("=" * 66)

        for label, vectors in [("A. 본문만", plain_vectors),
                               ("B. 메타데이터 포함", meta_vectors)]:
            print(f"\n  [{label}]")
            for rank, (score, b) in enumerate(search(question, vectors), start=1):
                first_line = b["text"].splitlines()[0][:40]
                print(f"    {rank}위 {score:.4f}  [{b['patch']}] {b['name']}  — {first_line}")

    print("\n" + "-" * 66)
    print("A 와 B 를 비교하세요. 특히 두 번째 질문(패치 번호 지정)을 보세요.")


# ===========================================================================
# 다 돌린 뒤에 생각해볼 것
#
#   1. 메타데이터를 넣으니 나아졌나요? 어떤 질문에서 특히?
#
#   2. "26.16 패치에서" 라고 못박은 질문의 결과를 보세요.
#      메타데이터를 넣어도 다른 패치 결과가 섞여 나올 겁니다.
#      임베딩은 "26.16" 과 "26.15" 를 아주 비슷한 문자열로 봅니다.
#      숫자의 정확한 일치는 벡터 검색이 원래 못 하는 일입니다.
#
#      → 이건 검색으로 풀 문제가 아니라 **필터로** 풀 문제입니다.
#         질문에서 패치 번호를 뽑아낸 뒤, 그 패치 블록만 남기고 검색하는 거죠.
#         스타크래프트 빌드오더 얘기할 때 나왔던 "매치업으로 먼저 거르기" 와 같습니다.
#
#   3. 고유명사 문제도 보세요.
#      "도란의 투구" 처럼 흔치 않은 이름은 임베딩이 잘 구별하지 못합니다.
#      모델이 학습할 때 거의 못 본 단어라 벡터가 뭉뚱그려집니다.
#      → 이게 다음에 할 하이브리드 검색(BM25)이 필요한 이유입니다.
#         BM25 는 단어가 정확히 일치하는지를 보기 때문에 고유명사에 강합니다.
# ===========================================================================


if __name__ == "__main__":
    main()
