"""문서를 읽어 벡터 인덱스를 만든다 (RAG 파이프라인의 준비 단계).

    python scripts/ingest.py
    python scripts/ingest.py --docs 다른/문서/폴더 --show 5
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.chunking import chunk_directory
from rag.config import DOCS_DIR, INDEX_DIR
from rag.console import setup_console
from rag.embedding import embed_passages
from rag.store import VectorStore


def main() -> int:
    setup_console()

    parser = argparse.ArgumentParser(description="문서를 청킹·임베딩해 인덱스를 생성합니다.")
    parser.add_argument("--docs", type=Path, default=DOCS_DIR, help="문서 디렉터리")
    parser.add_argument("--index", type=Path, default=INDEX_DIR, help="인덱스 출력 디렉터리")
    parser.add_argument("--show", type=int, default=3, help="샘플로 출력할 청크 개수")
    args = parser.parse_args()

    # 1) 로드 + 청킹
    print(f"[1/3] 청킹: {args.docs}")
    t0 = time.perf_counter()
    chunks = chunk_directory(args.docs)

    per_doc: dict[str, int] = {}
    for c in chunks:
        per_doc[c.doc_id] = per_doc.get(c.doc_id, 0) + 1
    for doc_id, n in per_doc.items():
        print(f"      {doc_id}: {n}개 청크")

    lengths = [len(c.text) for c in chunks]
    print(
        f"      총 {len(chunks)}개 청크 "
        f"(길이 최소 {min(lengths)} / 평균 {sum(lengths) // len(lengths)} / 최대 {max(lengths)}자)"
    )

    # 2) 임베딩
    print(f"[2/3] 임베딩: {len(chunks)}개 청크")
    vectors = embed_passages([c.text for c in chunks])
    print(f"      벡터 shape = {vectors.shape}")

    # 3) 저장
    print(f"[3/3] 저장: {args.index}")
    store = VectorStore(vectors=vectors, chunks=chunks)
    store.save(args.index)

    elapsed = time.perf_counter() - t0
    print(f"\n완료 ({elapsed:.1f}초)")

    if args.show:
        print(f"\n--- 청크 샘플 {args.show}개 ---")
        step = max(1, len(chunks) // args.show)
        for c in chunks[::step][: args.show]:
            preview = c.body[:120].replace("\n", " ")
            print(f"\n[{c.source}]  ({len(c.text)}자)")
            print(f"  {preview}...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
