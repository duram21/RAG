"""전체 RAG 파이프라인 실행: 검색 → 생성.

    python scripts/ask.py "연차는 며칠인가요?"
    python scripts/ask.py "배포 규칙 알려줘" -k 6 --show-context
    python scripts/ask.py "연차는 며칠인가요?" --provider claude

공급자는 .env 의 LLM_PROVIDER 를 따르며 --provider 로 덮어쓸 수 있습니다.
해당 공급자의 API 키가 .env 에 있어야 합니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from rag.config import INDEX_DIR, ROOT, TOP_K
from rag.console import setup_console
from rag.generate import generate
from rag.llm import LLMError, available_providers, get_provider
from rag.retrieve import retrieve
from rag.store import VectorStore


def main() -> int:
    setup_console()
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="문서를 검색해 LLM이 답변합니다.")
    parser.add_argument("question", help="질문")
    parser.add_argument("-k", type=int, default=TOP_K, help=f"근거로 넘길 청크 수 (기본 {TOP_K})")
    parser.add_argument("--index", type=Path, default=INDEX_DIR, help="인덱스 디렉터리")
    parser.add_argument(
        "--provider",
        choices=available_providers(),
        help="LLM 공급자 (기본: .env 의 LLM_PROVIDER)",
    )
    parser.add_argument("--show-context", action="store_true", help="LLM에 넘긴 근거 전문 출력")
    args = parser.parse_args()

    store = VectorStore.load(args.index)

    # 1) 검색 — 여기까지는 LLM도 API 키도 필요 없습니다.
    results = retrieve(args.question, store, k=args.k)

    print(f"\n질문: {args.question}")
    print(f"\n검색된 근거 {len(results)}개:")
    for r in results:
        print(f"  [{r.rank}] {r.score:.4f}  {r.source}")

    if args.show_context:
        print("\n--- LLM에 넘긴 근거 전문 ---")
        for r in results:
            print(f"\n[{r.rank}] {r.source}\n{r.chunk.body}")

    # 2) 생성
    try:
        provider = get_provider(args.provider)
        print(f"\n답변 생성 중... ({provider.name} / {provider.model})\n")
        answer = generate(args.question, results, provider=provider)
    except LLMError as e:
        print(f"\n{e}", file=sys.stderr)
        return 1

    print("=" * 60)
    print(answer.text)
    print("=" * 60)
    print(f"\n토큰: 입력 {answer.input_tokens:,} / 출력 {answer.output_tokens:,}")

    return 1 if answer.refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
