"""검색만 실행해본다 (LLM 호출 없음, API 키 불필요).

RAG가 엉뚱한 답을 할 때 원인은 대개 생성이 아니라 검색입니다.
답변을 보기 전에 "어떤 청크가 딸려왔는지"를 먼저 확인하는 용도의 도구입니다.

    python scripts/search.py "연차는 며칠인가요?"
    python scripts/search.py "배포 요일" -k 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import INDEX_DIR, TOP_K
from rag.console import setup_console
from rag.retrieve import retrieve
from rag.store import VectorStore


def main() -> int:
    setup_console()

    parser = argparse.ArgumentParser(description="인덱스에서 관련 청크를 검색합니다.")
    parser.add_argument("query", help="검색할 질문")
    parser.add_argument("-k", type=int, default=TOP_K, help=f"가져올 청크 수 (기본 {TOP_K})")
    parser.add_argument("--index", type=Path, default=INDEX_DIR, help="인덱스 디렉터리")
    parser.add_argument("--full", action="store_true", help="청크 전문 출력")
    args = parser.parse_args()

    store = VectorStore.load(args.index)
    results = retrieve(args.query, store, k=args.k)

    print(f"\n질문: {args.query}")
    print(f"인덱스: {len(store)}개 청크 중 상위 {len(results)}개\n")

    for r in results:
        bar = "█" * int(r.score * 40)
        print(f"[{r.rank}] {r.score:.4f} {bar}")
        print(f"    {r.source}")
        body = r.chunk.body if args.full else r.chunk.body[:150].replace("\n", " ") + "..."
        indented = "\n".join(f"    {line}" for line in body.split("\n"))
        print(f"{indented}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
