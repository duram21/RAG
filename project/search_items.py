"""아이템 인덱스에서 검색만 한다 (LLM 없음, API 키 불필요).

    python project/search_items.py "장화 효과가 뭐야?"
    python project/search_items.py "이동속도 올려주는 아이템" -k 5
    python project/search_items.py            # 대화형

RAG 가 이상한 답을 하면 원인은 대개 생성이 아니라 검색입니다.
답변을 보기 전에 "어떤 아이템이 딸려왔는지" 를 먼저 확인하는 도구입니다.

build_index.py 를 먼저 실행해 인덱스를 만들어 두세요.
"""

from pathlib import Path
import argparse
import json
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

HERE = Path(__file__).resolve().parent
INDEX_DIR = HERE / "data"
MODEL_NAME = "intfloat/multilingual-e5-small"


def load_index():
    """인덱스를 읽어 (벡터, records) 를 돌려준다."""
    npy_path = INDEX_DIR / "index.npy"
    json_path = INDEX_DIR / "index.json"

    if not npy_path.exists():
        raise SystemExit(
            f"인덱스가 없습니다: {npy_path}\n"
            "  먼저 실행하세요:  python project/build_index.py"
        )

    vectors = np.load(npy_path)
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    records = meta["records"]

    # 인덱스를 만든 모델과 지금 질문을 인코딩할 모델이 다르면 검색이 무의미해집니다.
    # 차원이 우연히 같으면 에러도 안 나고 조용히 엉뚱한 결과가 나옵니다.
    if meta.get("model") != MODEL_NAME:
        raise SystemExit(
            f"인덱스는 '{meta.get('model')}' 로 만들어졌는데 "
            f"현재 설정은 '{MODEL_NAME}' 입니다.\n"
            "  build_index.py 를 다시 실행하세요."
        )

    # 벡터와 records 는 같은 순서로 만들어졌습니다. 개수가 어긋나면
    # 검색 결과가 엉뚱한 아이템을 가리키는데 에러는 안 납니다.
    if len(vectors) != len(records):
        raise SystemExit(
            f"벡터 {len(vectors)}개 ≠ records {len(records)}개. 인덱스를 다시 만드세요."
        )

    return vectors, records


def search(question: str, model, vectors, records, k: int = 5):
    """질문과 가까운 아이템 k개를 [(점수, record), ...] 로 돌려준다."""
    query_vec = model.encode(
        ["query: " + question], normalize_embeddings=True
    )[0]


    scores = vectors @ query_vec


    top = np.argsort(-scores)[:k]
    return [(float(scores[i]), records[i]) for i in top]


def print_results(question: str, results):
    print(f"\n질문: {question}")
    print("=" * 62)
    for rank, (score, rec) in enumerate(results, start=1):
        bar = "█" * int(score * 30)
        print(f"\n[{rank}] {score:.4f} {bar}")
        print(f"    {rec['name']}  ({rec['gold_total']}골드)")
        # text 의 첫 줄은 "이름 (가격)" 이라 중복이므로 둘째 줄부터 보여줍니다.
        body = "\n".join(rec["text"].splitlines()[1:])
        for line in body.splitlines()[:4]:
            print(f"      {line}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="아이템 인덱스에서 검색합니다.")
    parser.add_argument("question", nargs="?", help="질문 (생략하면 대화형)")
    parser.add_argument("-k", type=int, default=5, help="가져올 개수 (기본 5)")
    args = parser.parse_args()

    vectors, records = load_index()
    print(f"인덱스: 아이템 {len(records)}개, {vectors.shape[1]}차원")

    print(f"모델 로딩: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    if args.question:
        print_results(args.question, search(args.question, model, vectors, records, args.k))
        return 0

    # 대화형 — 모델을 한 번만 로딩하므로 두 번째 질문부터는 즉시 응답합니다.
    print("\n질문을 입력하세요. (빈 줄 또는 /quit 로 종료)")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return 0
        if not line or line in {"/quit", "/exit"}:
            print("종료합니다.")
            return 0
        print_results(line, search(line, model, vectors, records, args.k))


if __name__ == "__main__":
    raise SystemExit(main())
