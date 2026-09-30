"""아이템에 대해 질문하면 검색 결과를 근거로 답변한다.

    python project/ask_items.py "장화 효과가 뭐야?"
    python project/ask_items.py "체력 회복되는 아이템 뭐 있어?" -k 8
    python project/ask_items.py                    # 대화형
    python project/ask_items.py "..." --show-context

무거운 로딩과 검색·생성 로직은 engine.py 에 있습니다. 여기는 껍데기입니다.

준비물: GEMINI_API_KEY (.env 또는 환경변수)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Answer, Engine, EngineError, build_context  # noqa: E402


def print_answer(question: str, answer: Answer, show_context: bool = False) -> None:
    print(f"\n질문: {question}")

    print(f"\n검색된 아이템 {len(answer.sources)}개:")
    for i, (score, rec) in enumerate(answer.sources, start=1):
        print(f"  [{i}] {score:.4f}  {rec['name']} ({rec['gold_total']}골드)")

    if show_context:
        print("\n--- LLM 에 넘긴 근거 전문 ---")
        print(build_context(answer.sources))

    print()
    print("=" * 62)
    print(answer.text)
    print("=" * 62)
    print(f"검색 {answer.search_ms:.0f}ms · 생성 {answer.llm_ms:.0f}ms"
          + (f" · {answer.model}" if answer.model else ""))

    if answer.unverified:
        print(f"\n⚠ 근거에 없는 숫자: {', '.join(answer.unverified)}")
        print("  (지어낸 것일 수도, 검사가 과민한 것일 수도 있습니다)")
    else:
        print("✓ 답변의 숫자가 모두 근거에 있습니다")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="아이템에 대해 질문합니다.")
    parser.add_argument("question", nargs="?", help="질문 (생략하면 대화형)")
    parser.add_argument("-k", type=int, default=5, help="근거로 넘길 아이템 수 (기본 5)")
    parser.add_argument("--show-context", action="store_true",
                        help="LLM 에 넘긴 근거 전문 출력")
    args = parser.parse_args()

    try:
        engine = Engine()
    except EngineError as e:
        print(e, file=sys.stderr)
        return 1

    if engine.llm is None:
        print("\nGEMINI_API_KEY 가 없습니다. 검색만 보려면 search_items.py 를 쓰세요.",
              file=sys.stderr)
        return 1

    if args.question:
        print_answer(args.question, engine.answer(args.question, args.k),
                     args.show_context)
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
        print_answer(line, engine.answer(line, args.k))


if __name__ == "__main__":
    raise SystemExit(main())
