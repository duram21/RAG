"""아이템 검색만 한다 (LLM 없음, API 키 불필요).

    python project/search_items.py "장화 효과가 뭐야?"
    python project/search_items.py "이동속도 올려주는 아이템" -k 8
    python project/search_items.py            # 대화형

RAG 가 이상한 답을 하면 원인은 대개 생성이 아니라 검색입니다.
답변을 보기 전에 "어떤 아이템이 딸려왔는지" 를 먼저 확인하는 도구입니다.

무거운 로딩과 검색 로직은 engine.py 에 있습니다. 여기는 껍데기입니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, EngineError  # noqa: E402


def print_results(question: str, results) -> None:
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

    try:
        # LLM 은 안 쓰므로 API 키 없이도 동작합니다.
        engine = Engine(with_llm=False)
    except EngineError as e:
        print(e, file=sys.stderr)
        return 1

    if args.question:
        print_results(args.question, engine.search(args.question, args.k))
        return 0

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
        print_results(line, engine.search(line, args.k))


if __name__ == "__main__":
    raise SystemExit(main())
