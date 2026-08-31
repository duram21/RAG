"""콘솔 출력 유틸.

두 가지 문제를 진입점에서 한 번에 처리합니다.

1. 인코딩 — Windows에서 Python의 기본 stdout 인코딩은 cp949 라서
   한글이 깨지거나 UnicodeEncodeError 가 납니다.

2. 버퍼링 — 출력을 파일이나 파이프로 넘기면 stdout은 블록 버퍼링이 되는데
   stderr는 그대로 논버퍼링이라, 오류 메시지가 진행 상황보다 먼저 튀어나와
   순서가 뒤집힙니다. 줄 단위 버퍼링으로 바꿔 순서를 맞춥니다.
"""

from __future__ import annotations

import sys


def setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
