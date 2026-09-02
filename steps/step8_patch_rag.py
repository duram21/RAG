"""8단계: 패치노트 RAG 완성 — 검색만 하지 말고 답변까지

6·7단계에서 검색 결과만 계속 봤습니다. 정작 "가렌 뭐 바뀌었어?" 에 대한
**답변**은 한 번도 못 봤죠. 이번에 붙입니다.

4단계와 구조는 같지만, 패치노트라서 새로 생기는 문제가 있습니다.

    **숫자를 정확히 옮기는가?**

    "피해량: 60/80/100/120/140 ⇒ 75/95/115/135/155"

    이런 걸 LLM 이 "약 75 정도로 상향" 이라고 뭉개거나, 아예 다른 숫자를
    써버리면 쓸모가 없습니다. 게임 정보는 숫자가 전부니까요.

    사람이 눈으로 일일이 확인할 수 없으니, **답변에 등장한 숫자가 근거에도
    있는지 자동으로 검사**하는 장치를 붙였습니다. 완벽하진 않지만
    "지어낸 숫자"를 상당수 잡아냅니다.

7단계에서 만든 것들을 그대로 가져다 씁니다 (import).

준비물: .env 에 GEMINI_API_KEY

실행:
    python steps/step8_patch_rag.py
    python steps/step8_patch_rag.py "리 신 최근에 뭐 바뀌었어?"
"""

import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# 7단계에서 만든 것들을 재사용합니다.
#   blocks        패치 블록 128개
#   model         임베딩 모델
#   extract_patch 질문에서 패치 번호 뽑기
#   search        필터 적용 검색
from step7_filter import blocks, extract_patch, model, search

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = "gemini-3.6-flash"
FALLBACKS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print(".env 에 GEMINI_API_KEY 가 없습니다.", file=sys.stderr)
    raise SystemExit(1)

client = genai.Client(
    api_key=api_key, http_options=types.HttpOptions(timeout=60_000)
)

SYSTEM_PROMPT = """당신은 리그 오브 레전드 패치노트 안내 도우미입니다.
아래 '참고 자료'만을 근거로 답변하세요.

규칙:
1. 참고 자료에 있는 내용만 사용합니다. 게임 지식으로 보충하지 마세요.
2. **숫자는 자료에 적힌 그대로 옮깁니다.** 반올림하거나 "약", "대략" 같은
   말로 뭉개지 마세요. 변경은 "60 ⇒ 75" 형식을 유지하세요.
3. 어느 패치의 변경인지 반드시 밝히세요. (예: "26.14 패치에서")
4. 근거 번호를 문장 끝에 [1], [2] 형식으로 표시합니다.
5. 참고 자료에 없으면 "해당 패치노트에서 찾을 수 없습니다."라고 답하세요.
6. 한국어로 간결하게 작성합니다."""


# ===========================================================================
# TODO 1. 검색 결과를 LLM 에게 넘길 문자열로 조립하세요.
#
#   4단계에서 했던 것과 거의 같습니다. 한 가지만 다릅니다 —
#   **패치 번호를 반드시 넣어야 합니다.** 그래야 LLM 이 규칙 3번
#   ("어느 패치인지 밝혀라") 을 지킬 수 있습니다.
#
#   search() 가 돌려주는 것:
#       [(점수, block), (점수, block), ...]
#       block 은 {"patch": ..., "name": ..., "text": ...} 딕셔너리
#
#   이런 모양의 문자열 하나로 만드세요:
#
#       [1] 26.14 패치 / 가렌
#       가렌
#       기본 능력치
#       - 방어력: 33 ⇒ 30
#
#       [2] 26.16 패치 / 아지르
#       ...
#
#   힌트:
#       parts = []
#       for i, (score, b) in enumerate(results, start=1):
#           parts.append(f"[{i}] {b['patch']} 패치 / {b['name']}\n{b['text']}")
#       return "\n\n".join(parts)
# ===========================================================================

def build_context(results) -> str:
    #print (results) 
    parts = []
    for i, (score, b) in enumerate(results, start = 1):
        parts.append(f"[{i}] {b['patch']} 패치 / {b['name']}\n{b['text']}")
    return "\n\n".join(parts)  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. 전체 파이프라인을 연결하세요. 세 줄입니다.
#
#   지금까지 만든 조각들을 순서대로 이어붙이기만 하면 됩니다.
#
#     (1) results — search(question, vectors) 로 검색
#     (2) context — build_context(results) 로 근거 조립
#     (3) answer  — ask_llm(SYSTEM_PROMPT, user_message) 로 답변 생성
#
#   user_message 는 아래에 이미 만드는 코드가 있으니 (2) 까지만 채우면
#   나머지는 이어집니다.
# ===========================================================================

def answer(question: str, vectors) -> tuple[str, str, list]:
    """질문 하나를 처리해 (답변, 근거문자열, 검색결과) 를 돌려준다."""
    results = search(question, vectors)   # ← (1) 여기를 채우세요
    context = build_context(results)   # ← (2) 여기를 채우세요

    if results is None or not context:
        return "[TODO 를 채우세요]", "", []

    user_message = f"참고 자료:\n{context}\n\n---\n\n질문: {question}"
    return ask_llm(SYSTEM_PROMPT, user_message), context, results


# ===========================================================================
# 여기부터는 고치지 않아도 됩니다.
# ===========================================================================

def ask_llm(system_prompt: str, user_message: str) -> str:
    """Gemini 호출. 무료 티어의 503/429 에 대비해 재시도와 모델 폴백을 넣었다."""
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=2000,
        temperature=0.1,   # 숫자를 옮기는 작업이라 무작위성을 최대한 낮춘다
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    for candidate in [MODEL] + FALLBACKS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=candidate, contents=user_message, config=config
                )
                return response.text or "[빈 응답]"
            except errors.APIError as e:
                if e.code not in (429, 503):
                    return f"[API 오류 {e.code}: {e.message}]"
                if attempt < 2:
                    time.sleep(2**attempt)
    return "[모든 모델이 응답하지 않았습니다]"


def check_numbers(answer_text: str, context: str) -> list[str]:
    """답변에 나온 숫자 중 근거에 없는 것을 찾아낸다.

    완벽한 검사는 아닙니다. LLM 이 "3가지 변경점" 처럼 스스로 센 숫자를
    쓸 수도 있으니까요. 그래도 근거에 없는 수치가 튀어나오면 대개 여기 걸립니다.
    자동 검사는 '의심 목록'을 좁혀줄 뿐, 최종 판단은 사람이 합니다.
    """
    in_answer = set(re.findall(r"\d+(?:\.\d+)?", answer_text))
    in_context = set(re.findall(r"\d+(?:\.\d+)?", context))
    suspicious = in_answer - in_context
    # 1~10 은 목록 번호일 가능성이 높아 제외한다
    return sorted(n for n in suspicious if not (n.isdigit() and int(n) <= 10))


QUESTIONS = [
    "26.14 패치에서 가렌 어떻게 바뀌었어?",
    "리 신 최근에 뭐 바뀌었어?",
    "26.16 패치에서 아지르 상향됐어 하향됐어?",
    "요네 이번에 너프됐어?",          # ← 데이터에 없을 수 있는 챔피언
]


def main() -> None:
    if not build_context([(0.9, blocks[0])]):
        print("TODO 1 이 비어 있습니다. build_context 를 채우세요.")
        return

    print(f"\n블록 {len(blocks)}개를 임베딩합니다...")
    texts = [f"{b['patch']} 패치 - {b['name']}\n{b['text']}" for b in blocks]
    vectors = model.encode(["passage: " + t for t in texts], normalize_embeddings=True)

    questions = sys.argv[1:] or QUESTIONS

    for question in questions:
        print("\n" + "=" * 66)
        print(f"Q. {question}")
        patch = extract_patch(question)
        print(f"   필터: {patch or '없음'}")
        print("=" * 66)

        text, context, results = answer(question, vectors)
        if not results:
            print(text)
            return

        print("\n  [검색된 근거]")
        for i, (score, b) in enumerate(results, start=1):
            print(f"    [{i}] {score:.4f}  {b['patch']} / {b['name']}")

        print("\n  [답변]")
        for line in text.strip().splitlines():
            print(f"    {line}")

        bad = check_numbers(text, context)
        if bad:
            print(f"\n  ⚠ 근거에 없는 숫자: {', '.join(bad)}")
            print("    (직접 확인해보세요. 지어낸 것일 수도, 검사가 과민한 것일 수도 있습니다)")
        else:
            print("\n  ✓ 답변의 숫자가 모두 근거에 있습니다")


if __name__ == "__main__":
    main()
