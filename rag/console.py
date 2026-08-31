"""콘솔 출력 유틸.

Windows에서 Python의 기본 stdout 인코딩은 cp949 라서 한글이 깨지거나
UnicodeEncodeError 가 납니다. 스크립트 진입점에서 `setup_console()` 을 한 번
호출해 UTF-8로 맞춰줍니다.
"""

from __future__ import annotations

import sys


def setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
