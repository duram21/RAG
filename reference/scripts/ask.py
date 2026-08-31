"""전체 RAG 파이프라인 실행: 검색 → 생성.

질문을 인자로 주면 한 번만 답하고 끝나고, 인자 없이 실행하면 대화형 모드로 들어갑니다.

    python scripts/ask.py                          # 대화형 모드
    python scripts/ask.py "연차는 며칠인가요?"      # 한 번만
    python scripts/ask.py "배포 규칙" -k 6 --show-context
    python scripts/ask.py "연차는?" --provider claude

대화형 모드에서는 임베딩 모델과 인덱스를 한 번만 로딩하므로
두 번째 질문부터는 기다림이 거의 없습니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _require_dependencies() -> None:
    """의존성이 없으면 원인과 해결책을 알려주고 종료한다."""
    try:
        import dotenv  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as e:
        exe = Path(sys.executable)
        in_venv = ".venv" in exe.parts
        print(f"필요한 패키지가 없습니다: {e.name}", file=sys.stderr)
        if not in_venv:
            print(
                "\n가상환경이 활성화되지 않은 것 같습니다. 먼저 실행하세요:\n"
                "  .venv/Scripts/activate      (Windows)\n"
                "  source .venv/bin/activate   (macOS / Linux)",
                file=sys.stderr,
            )
        else:
            print("\n  pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1)


_require_dependencies()

from dotenv import load_dotenv

from rag.config import INDEX_DIR, ROOT, TOP_K
from rag.console import setup_console
from rag.generate import generate
from rag.llm import LLMError, LLMProvider, available_providers, get_provider
from rag.retrieve import retrieve
from rag.store import VectorStore

HELP = """
명령어:
  /help          이 도움말
  /k <숫자>      근거로 넘길 청크 수 변경 (현재 {k})
  /context       마지막 질문의 근거 전문 보기
  /quit, /exit   종료  (Ctrl+C 로도 종료됩니다)

그 외의 입력은 모두 질문으로 처리합니다.
"""


def answer_once(
    question: str,
    store: VectorStore,
    provider: LLMProvider,
    k: int,
    show_context: bool = False,
) -> list:
    """질문 하나를 검색·생성하고 결과를 출력한다. 검색 결과를 돌려준다."""
    results = retrieve(question, store, k=k)

    print(f"\n검색된 근거 {len(results)}개:")
    for r in results:
        print(f"  [{r.rank}] {r.score:.4f}  {r.source}")

    if show_context:
        print_context(results)

    print(f"\n답변 생성 중... ({provider.name} / {provider.model})\n")
    answer = generate(question, results, provider=provider)

    print("=" * 60)
    print(answer.text)
    print("=" * 60)
    print(f"토큰: 입력 {answer.input_tokens:,} / 출력 {answer.output_tokens:,}")

    return results


def print_context(results: list) -> None:
    print("\n--- LLM에 넘긴 근거 전문 ---")
    for r in results:
        print(f"\n[{r.rank}] {r.source}\n{r.chunk.body}")


def interactive(store: VectorStore, provider: LLMProvider, k: int) -> int:
    print("\n대화형 모드입니다. 질문을 입력하세요. (/help 로 명령어, /quit 로 종료)")
    print(f"인덱스: {len(store)}개 청크  |  모델: {provider.name} / {provider.model}")

    last_results: list = []

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return 0

        if not line:
            continue

        if line in {"/quit", "/exit"}:
            print("종료합니다.")
            return 0

        if line == "/help":
            print(HELP.format(k=k))
            continue

        if line == "/context":
            if last_results:
                print_context(last_results)
            else:
                print("아직 질문이 없습니다.")
            continue

        if line.startswith("/k"):
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) > 0:
                k = int(parts[1])
                print(f"근거 청크 수를 {k}개로 변경했습니다.")
            else:
                print("사용법: /k 6")
            continue

        if line.startswith("/"):
            print(f"알 수 없는 명령어입니다: {line}  (/help 참고)")
            continue

        try:
            last_results = answer_once(line, store, provider, k)
        except LLMError as e:
            # 대화형에서는 오류가 나도 세션을 끊지 않습니다.
            print(f"\n{e}")


def main() -> int:
    setup_console()
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(
        description="문서를 검색해 LLM이 답변합니다. 질문을 생략하면 대화형 모드로 실행됩니다.",
    )
    parser.add_argument("question", nargs="?", help="질문 (생략하면 대화형 모드)")
    parser.add_argument("-k", type=int, default=TOP_K, help=f"근거로 넘길 청크 수 (기본 {TOP_K})")
    parser.add_argument("--index", type=Path, default=INDEX_DIR, help="인덱스 디렉터리")
    parser.add_argument(
        "--provider",
        choices=available_providers(),
        help="LLM 공급자 (기본: .env 의 LLM_PROVIDER)",
    )
    parser.add_argument("--show-context", action="store_true", help="LLM에 넘긴 근거 전문 출력")
    args = parser.parse_args()

    try:
        store = VectorStore.load(args.index)
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1

    try:
        provider = get_provider(args.provider)
    except LLMError as e:
        print(e, file=sys.stderr)
        return 1

    if args.question is None:
        return interactive(store, provider, args.k)

    print(f"\n질문: {args.question}")
    try:
        answer_once(args.question, store, provider, args.k, args.show_context)
    except LLMError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
