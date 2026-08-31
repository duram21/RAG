"""전체 RAG 파이프라인 실행: 검색 → 생성.

    python scripts/ask.py "연차는 며칠인가요?"
    python scripts/ask.py "배포 규칙 알려줘" -k 6 --show-context

ANTHROPIC_API_KEY 가 필요합니다 (.env 또는 환경변수).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic
from dotenv import load_dotenv

from rag.config import INDEX_DIR, ROOT, TOP_K
from rag.console import setup_console
from rag.generate import generate
from rag.retrieve import retrieve
from rag.store import VectorStore


def main() -> int:
    setup_console()
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="문서를 검색해 Claude가 답변합니다.")
    parser.add_argument("question", help="질문")
    parser.add_argument("-k", type=int, default=TOP_K, help=f"근거로 넘길 청크 수 (기본 {TOP_K})")
    parser.add_argument("--index", type=Path, default=INDEX_DIR, help="인덱스 디렉터리")
    parser.add_argument("--show-context", action="store_true", help="Claude에 넘긴 근거 전문 출력")
    args = parser.parse_args()

    store = VectorStore.load(args.index)

    # 1) 검색
    results = retrieve(args.question, store, k=args.k)

    print(f"\n질문: {args.question}")
    print(f"\n검색된 근거 {len(results)}개:")
    for r in results:
        print(f"  [{r.rank}] {r.score:.4f}  {r.source}")

    if args.show_context:
        print("\n--- Claude에 넘긴 근거 전문 ---")
        for r in results:
            print(f"\n[{r.rank}] {r.source}\n{r.chunk.body}")

    # 2) 생성
    print("\n답변 생성 중...\n")
    try:
        answer = generate(args.question, results)
    except anthropic.AuthenticationError:
        print("인증 실패: ANTHROPIC_API_KEY 가 올바른지 확인하세요.", file=sys.stderr)
        print("  .env 파일에 ANTHROPIC_API_KEY=sk-ant-... 를 넣거나 환경변수로 설정하세요.", file=sys.stderr)
        return 1
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "60")
        print(f"요청 한도 초과. {retry_after}초 뒤에 다시 시도하세요.", file=sys.stderr)
        return 1
    except anthropic.APIStatusError as e:
        print(f"API 오류 ({e.status_code}): {e.message}", file=sys.stderr)
        return 1
    except anthropic.APIConnectionError:
        print("네트워크 오류: 연결을 확인하세요.", file=sys.stderr)
        return 1

    print("=" * 60)
    print(answer.text)
    print("=" * 60)
    print(
        f"\n토큰: 입력 {answer.input_tokens:,} / 출력 {answer.output_tokens:,}"
    )

    return 1 if answer.refused else 0


if __name__ == "__main__":
    raise SystemExit(main())
