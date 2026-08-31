"""내 API 키로 실제 사용 가능한 모델을 조회한다.

문서에 적힌 모델 ID가 내 키에서도 되리라는 보장은 없습니다.
티어·지역·모델 수명주기에 따라 404가 나거나, 인기 모델은 503(과부하)이 잦습니다.
설정할 모델을 고르기 전에 이걸로 먼저 확인하세요.

    python scripts/models.py
    python scripts/models.py --check      # 실제로 호출해 응답하는지까지 확인
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from rag.config import GEMINI_MODEL, ROOT
from rag.console import setup_console


def main() -> int:
    setup_console()
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Gemini 사용 가능 모델 조회")
    parser.add_argument(
        "--check",
        action="store_true",
        help="주요 후보 모델에 실제 요청을 보내 응답 여부 확인",
    )
    args = parser.parse_args()

    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        print("GEMINI_API_KEY 가 없습니다. .env 를 확인하세요.", file=sys.stderr)
        return 1

    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=key)

    generation: list[str] = []
    embedding: list[str] = []
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        name = m.name.replace("models/", "")
        if "embedContent" in actions:
            embedding.append(name)
        elif "generateContent" in actions:
            generation.append(name)

    print(f"\n=== 생성 모델 ({len(generation)}개) ===")
    for name in generation:
        mark = "  <- 현재 설정" if name == GEMINI_MODEL else ""
        print(f"  {name}{mark}")

    print(f"\n=== 임베딩 모델 ({len(embedding)}개) ===")
    for name in embedding:
        print(f"  {name}")
    print("  (이 프로젝트는 로컬 임베딩을 쓰므로 사용하지 않습니다)")

    if not args.check:
        print("\n실제 응답 여부까지 확인하려면: python scripts/models.py --check")
        return 0

    # 목록에 있다고 다 되는 건 아닙니다. 실제로 한 번 찔러봅니다.
    EXCLUDE = ("image", "tts", "transcribe", "robotics", "customtools", "lyria")
    candidates = [
        n
        for n in generation
        if ("flash" in n or "pro" in n) and not any(x in n for x in EXCLUDE)
    ]

    print(f"\n=== 실제 호출 확인 ({len(candidates)}개) ===")
    config = types.GenerateContentConfig(
        max_output_tokens=20,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    for name in candidates:
        try:
            client.models.generate_content(model=name, contents="hi", config=config)
            print(f"  [정상] {name}")
        except errors.APIError as e:
            label = {503: "과부하", 429: "한도초과", 404: "없음"}.get(e.code, "오류")
            print(f"  [{label}] {name} ({e.code})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
