"""아이템에 대해 질문하면 검색 결과를 근거로 답변한다.

    python project/ask_items.py "장화 효과가 뭐야?"
    python project/ask_items.py "체력 회복되는 아이템 뭐 있어?" -k 6
    python project/ask_items.py                    # 대화형
    python project/ask_items.py "..." --show-context

search_items.py 의 인덱스 로드와 검색을 그대로 씁니다.
여기서 더하는 것은 "검색 결과를 LLM 에게 넘겨 답변을 만드는" 부분뿐입니다.

준비물: GEMINI_API_KEY (.env 또는 환경변수)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from sentence_transformers import SentenceTransformer

# 같은 폴더의 search_items.py 를 그대로 재사용합니다.
# (opgg-api.py 와 달리 파일명에 하이픈이 없어서 평범한 import 가 됩니다)
from search_items import MODEL_NAME, load_index, search

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# .env 를 여러 곳에서 찾습니다. 키를 여러 파일에 복사해두면
# 나중에 하나만 바꾸고 "왜 안 되지" 하게 됩니다.
for candidate in (HERE / ".env", ROOT / ".env", ROOT / "rag-practice" / ".env"):
    if candidate.exists():
        load_dotenv(candidate)
        ENV_PATH = candidate
        break
else:
    ENV_PATH = None

GEMINI_MODEL = "gemini-3.6-flash"
FALLBACKS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

SYSTEM_PROMPT = """당신은 리그 오브 레전드 아이템 안내 도우미입니다.
아래 '참고 자료'만을 근거로 답변하세요.

규칙:
1. 참고 자료에 있는 내용만 사용합니다. 게임 지식으로 보충하지 마세요.
2. 능력치와 수치는 자료에 적힌 그대로 옮깁니다. 반올림하거나
   "약", "대략" 으로 뭉개지 마세요.
3. 가격을 언급할 때는 자료의 골드 값을 그대로 씁니다.
4. 근거가 된 아이템 번호를 문장 끝에 [1], [2] 형식으로 표시합니다.
5. 참고 자료에 없으면 "제공된 아이템 목록에서 찾을 수 없습니다."라고 답하세요.
   비슷해 보이는 게 있으면 무엇을 찾았는지만 덧붙이세요.
6. 한국어로 간결하게 작성합니다."""


def build_context(results) -> str:
    """검색 결과를 LLM 에게 넘길 문자열로 조립한다."""
    parts = []
    for i, (score, rec) in enumerate(results, start=1):
        parts.append(f"[{i}] {rec['text']}")
    return "\n\n".join(parts)


def ask_llm(client, system_prompt: str, user_message: str) -> str:
    """Gemini 호출. 무료 티어의 503/429 에 대비해 재시도와 모델 폴백을 넣었다."""
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=2000,
        temperature=0.1,   # 수치를 옮기는 작업이라 무작위성을 낮춘다
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    for candidate in [GEMINI_MODEL] + FALLBACKS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=candidate, contents=user_message, config=config
                )
                return response.text or "[빈 응답]"
            except errors.APIError as e:
                # 504(시간 초과)도 일시적 오류라 재시도 대상에 넣습니다.
                if e.code not in (429, 503, 504):
                    return f"[API 오류 {e.code}: {e.message}]"
                if attempt < 2:
                    time.sleep(2**attempt)
        print(f"  ({candidate} 실패 → 다음 모델)")

    return "[모든 모델이 응답하지 않았습니다]"


def check_numbers(answer: str, context: str) -> list[str]:
    """답변에 나온 숫자 중 근거에 없는 것을 찾아낸다.

    완벽한 검사는 아닙니다. LLM 이 "3가지" 처럼 스스로 센 숫자를 쓸 수 있어
    1~10 은 제외합니다. 자동 검사는 의심 목록을 좁혀줄 뿐입니다.
    """
    in_answer = set(re.findall(r"\d+(?:\.\d+)?", answer))
    in_context = set(re.findall(r"\d+(?:\.\d+)?", context))
    suspicious = in_answer - in_context
    return sorted(n for n in suspicious if not (n.isdigit() and int(n) <= 10))


def answer_once(question, client, model, vectors, records, k, show_context=False):
    results = search(question, model, vectors, records, k)
    context = build_context(results)

    print(f"\n질문: {question}")
    print(f"\n검색된 아이템 {len(results)}개:")
    for i, (score, rec) in enumerate(results, start=1):
        print(f"  [{i}] {score:.4f}  {rec['name']} ({rec['gold_total']}골드)")

    if show_context:
        print("\n--- LLM 에 넘긴 근거 전문 ---")
        print(context)

    print("\n답변 생성 중...\n")
    user_message = f"참고 자료:\n{context}\n\n---\n\n질문: {question}"
    text = ask_llm(client, SYSTEM_PROMPT, user_message)

    print("=" * 62)
    print(text.strip())
    print("=" * 62)

    bad = check_numbers(text, context)
    if bad:
        print(f"\n⚠ 근거에 없는 숫자: {', '.join(bad)}")
        print("  (지어낸 것일 수도, 검사가 과민한 것일 수도 있습니다)")
    else:
        print("\n✓ 답변의 숫자가 모두 근거에 있습니다")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="아이템에 대해 질문합니다.")
    parser.add_argument("question", nargs="?", help="질문 (생략하면 대화형)")
    parser.add_argument("-k", type=int, default=5, help="근거로 넘길 아이템 수 (기본 5)")
    parser.add_argument("--show-context", action="store_true", help="LLM 에 넘긴 근거 전문 출력")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY 가 없습니다.", file=sys.stderr)
        print(f"  찾아본 .env: {ENV_PATH or '없음'}", file=sys.stderr)
        print("  https://aistudio.google.com/apikey 에서 발급 후 .env 에 넣으세요.",
              file=sys.stderr)
        return 1

    vectors, records = load_index()
    print(f"인덱스: 아이템 {len(records)}개")
    print(f"모델 로딩: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    client = genai.Client(
        api_key=api_key, http_options=types.HttpOptions(timeout=60_000)
    )

    if args.question:
        answer_once(args.question, client, model, vectors, records,
                    args.k, args.show_context)
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
        answer_once(line, client, model, vectors, records, args.k)


if __name__ == "__main__":
    raise SystemExit(main())
