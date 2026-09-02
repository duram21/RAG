"""문서를 검색 단위(청크)로 쪼갠다.

RAG에서 청킹은 검색 품질을 가장 크게 좌우하는 단계입니다.
여기서는 두 단계로 나눕니다.

  1) 마크다운 헤딩(`## ...`) 기준으로 의미 단위 섹션을 자른다.
  2) 섹션이 CHUNK_SIZE 보다 길면 문단 경계를 지키며 겹치게(overlap) 다시 자른다.

각 청크에는 소속 문서명과 헤딩을 함께 붙여둡니다.
"연차는 며칠?" 같은 질문은 본문보다 '휴가 정책 > 연차 휴가' 라는 제목과 더 잘 맞기 때문에,
제목을 청크 텍스트에 포함시키면 검색 정확도가 눈에 띄게 올라갑니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    """검색과 인용의 최소 단위."""

    text: str          # 임베딩 대상 텍스트 (제목 + 본문)
    body: str          # 본문만 (사람에게 보여줄 때 사용)
    doc_id: str        # 출처 파일명
    heading: str       # 소속 섹션 제목
    index: int         # 문서 내 몇 번째 청크인지

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def source(self) -> str:
        """`휴가정책.md > 연차 휴가` 형태의 사람이 읽을 출처 표기."""
        return f"{self.doc_id} > {self.heading}" if self.heading else self.doc_id


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def split_sections(text: str) -> list[tuple[str, str]]:
    """마크다운 텍스트를 (헤딩, 본문) 목록으로 자른다.

    첫 헤딩보다 앞에 있는 내용은 헤딩 없이(`""`) 한 덩어리로 담습니다.
    """
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [("", text.strip())]

    sections: list[tuple[str, str]] = []

    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((heading, body))

    return sections


def split_with_overlap(
    text: str,
    size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """긴 텍스트를 문단 경계를 지키며 겹치게 자른다.

    문단(빈 줄 기준)을 하나씩 채워 넣다가 `size`를 넘으면 끊고,
    다음 조각은 직전 조각의 끝 `overlap` 글자부터 이어서 시작합니다.
    """
    if len(text) <= size:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # 문단 하나가 이미 size 보다 크면 문장 단위로 더 잘게 쪼갠다.
        pieces = [para] if len(para) <= size else _split_sentences(para, size)

        for piece in pieces:
            if current and len(current) + len(piece) + 2 > size:
                chunks.append(current.strip())
                tail = current[-overlap:] if overlap else ""
                current = f"{tail}\n\n{piece}" if tail else piece
            else:
                current = f"{current}\n\n{piece}" if current else piece

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _split_sentences(text: str, size: int) -> list[str]:
    """문장 종결 부호 기준으로 자른다 (한 문단이 지나치게 긴 경우의 대비책)."""
    sentences = re.split(r"(?<=[.!?。])\s+", text)
    pieces: list[str] = []
    current = ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > size:
            pieces.append(current.strip())
            current = s
        else:
            current = f"{current} {s}" if current else s
    if current.strip():
        pieces.append(current.strip())
    return pieces


def chunk_document(path: Path) -> list[Chunk]:
    """파일 하나를 읽어 Chunk 목록으로 변환한다."""
    raw = path.read_text(encoding="utf-8")
    doc_id = path.name

    chunks: list[Chunk] = []
    for heading, body in split_sections(raw):
        for piece in split_with_overlap(body):
            # 임베딩에는 제목을 앞에 붙여 문맥을 보강한다.
            text = f"{heading}\n\n{piece}" if heading else piece
            chunks.append(
                Chunk(
                    text=text,
                    body=piece,
                    doc_id=doc_id,
                    heading=heading,
                    index=len(chunks),
                )
            )

    return chunks


def chunk_directory(docs_dir: Path) -> list[Chunk]:
    """디렉터리 안의 모든 .md / .txt 문서를 청킹한다."""
    paths = sorted(
        p for p in docs_dir.rglob("*") if p.suffix.lower() in {".md", ".txt"}
    )
    if not paths:
        raise FileNotFoundError(f"{docs_dir} 안에 .md 또는 .txt 문서가 없습니다.")

    chunks: list[Chunk] = []
    for path in paths:
        chunks.extend(chunk_document(path))
    return chunks
