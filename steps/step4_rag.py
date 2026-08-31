"""4단계: RAG 완성 — 검색 결과를 LLM 에게 넘겨 답변 만들기

3단계까지로 'R'(검색)이 끝났습니다. 이제 'G'(Generation, 생성)를 붙입니다.

핵심은 이렇습니다.
    LLM 은 우리 회사 문서를 모릅니다. 학습한 적이 없으니까요.
    그래서 질문만 던지면 그럴듯한 거짓말을 합니다.
    대신 **검색해서 찾은 문서를 질문과 함께 넣어주고** "이것만 보고 답해" 라고 시킵니다.
    이게 RAG(검색 증강 생성) 입니다.

그런데 여기서 진짜 어려운 문제가 나옵니다.
    3단계 마지막에서 봤듯, 답이 없는 질문에도 검색은 뭔가를 돌려줍니다.
    그 엉뚱한 문서를 받은 LLM 이 "아 이걸로 답을 만들어야 하는구나" 하고
    지어내기 시작하면, 검색을 안 하느니만 못한 시스템이 됩니다.

    그래서 이 단계의 절반은 **"모르면 모른다고 말하게 만들기"** 입니다.

준비물: .env 파일에 GEMINI_API_KEY 가 있어야 합니다.

실행:
    python steps/step4_rag.py
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# 3단계에서 만든 검색기를 그대로 가져다 씁니다.
# (import 하면 step3_search.py 의 위쪽 코드가 실행되어 인덱스가 만들어집니다)
from step3_search import search

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MODEL = "gemini-3.6-flash"
FALLBACKS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print(".env 에 GEMINI_API_KEY 가 없습니다.", file=sys.stderr)
    raise SystemExit(1)

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=60_000),   # 60초 (밀리초 단위)
)


# ===========================================================================
# TODO 1. 검색 결과를 LLM 에게 보여줄 문자열로 조립하세요.
#
#   search(question) 이 돌려주는 것:
#       [(점수, 문서이름, 청크내용), (점수, 문서이름, 청크내용), ...]
#
#   이걸 아래와 같은 모양의 **문자열 하나**로 만들어야 합니다.
#
#       [1] 출처: 01-휴가정책.md
#       연차 휴가
#       정규직 구성원은 입사와 동시에...
#
#       [2] 출처: 01-휴가정책.md
#       병가
#       병가는 연 10일까지...
#
#   왜 [1], [2] 번호를 붙이냐면 — 답변에서 이 번호를 인용하게 만들기 위해서입니다.
#   그래야 사용자가 "이 말이 어디서 나왔지?" 를 되짚어볼 수 있습니다.
#
#   힌트:
#     blocks = []                        빈 리스트를 만들고
#     for i, (score, doc, text) in enumerate(results, start=1):
#         blocks.append(f"[{i}] 출처: {doc}\n{text}")     ← 한 덩어리씩 담고
#     return "\n\n".join(blocks)         마지막에 빈 줄로 이어붙인다
#
#   "구분자".join(리스트) 는 리스트를 하나의 문자열로 합칩니다.
#       ", ".join(["a", "b", "c"])   →  "a, b, c"
#       "\n\n".join(["a", "b"])      →  "a\n\nb"   (사이에 빈 줄)
# ===========================================================================

def build_context(results) -> str:
    blocks = []
    # (점수, 문서이름, 청크내용)
    for i, (score, doc, text) in enumerate(results, start = 1):
        blocks.append(f"[{i}] 출처: {doc}\n{text}")
    return "\n\n".join(blocks)  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. Gemini 를 호출하세요.
#
#   client.models.generate_content(...) 를 부르면 됩니다. 인자 세 개:
#
#       model=model_name
#       contents=user_message
#       config=config              ← 아래에 이미 만들어 뒀습니다
#
#   결과에서 글자만 꺼내려면 response.text 입니다.
#
#   즉 이 모양입니다:
#       response = client.models.generate_content(model=???, contents=???, config=???)
#       return response.text
# ===========================================================================

def ask_llm(system_prompt: str, user_message: str, model_name: str = MODEL) -> str:
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=2000,
        temperature=0.2,   # 낮을수록 덜 창의적 = 근거에서 덜 벗어남
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    # 무료 티어는 인기 모델이 503(과부하)을 자주 냅니다.
    # 재시도하고, 그래도 안 되면 다른 모델로 넘어갑니다.
    for candidate in [model_name] + FALLBACKS:
        for attempt in range(3):
            try:
                # ↓↓↓ 여기를 채우세요 ↓↓↓
                response = client.models.generate_content(model=candidate, contents=user_message, config=config)
                if response is None:
                    return "[TODO 2 가 비어 있습니다]"
                return response.text
                # ↑↑↑ 여기를 채우세요 ↑↑↑
            except errors.APIError as e:
                if e.code not in (429, 503):
                    return f"[API 오류 {e.code}: {e.message}]"
                if attempt < 2:
                    time.sleep(2 ** attempt)
        print(f"    ({candidate} 실패 → 다음 모델 시도)")

    return "[모든 모델이 응답하지 않았습니다]"


# ===========================================================================
# 여기부터는 실험용입니다. 고치지 않아도 됩니다.
#
# 시스템 프롬프트를 두 가지 준비했습니다. 같은 질문에 어떻게 다르게 답하는지 보세요.
# ===========================================================================

LOOSE_PROMPT = """당신은 사내 문서 도우미입니다.
아래 참고 문서를 바탕으로 사용자의 질문에 친절하게 답변하세요."""

STRICT_PROMPT = """당신은 사내 문서 검색 도우미입니다.
사용자의 질문에, 아래 '참고 문서'만을 근거로 답변하세요.

규칙:
1. 참고 문서에 있는 내용만 사용합니다. 일반 상식이나 추측으로 보충하지 마세요.
2. 근거가 된 문서의 번호를 문장 끝에 [1], [2] 형식으로 표시합니다.
3. 참고 문서에 답이 없으면 "제공된 문서에서 해당 내용을 찾을 수 없습니다."라고
   답하세요. 그럴듯하게 지어내지 마세요.
4. 답변은 한국어로 간결하게 작성합니다."""

USER_TEMPLATE = """참고 문서:
{context}

---

질문: {question}"""


def main() -> None:
    demo_question = "하이하이"
    results = search(demo_question)
    context = build_context(results)

    if not context:
        print("TODO 1 이 비어 있습니다. build_context 를 채우세요.")
        return

    print("\n" + "=" * 62)
    print("TODO 1 결과 확인 — LLM 에게 이런 모양으로 넘어갑니다")
    print("=" * 62)
    print(context[:400] + "...\n")

    # --- 실험: 답이 있는 질문 vs 없는 질문 × 느슨한 프롬프트 vs 엄격한 프롬프트 ---
    experiments = [
        ("연차 휴가 며칠 쓸 수 있어?", "문서에 답이 있음"),
        ("회사 주차장은 몇 층인가요?", "문서에 답이 없음  ← 여기가 진짜 시험"),
    ]

    for question, note in experiments:
        results = search(question)
        user_message = USER_TEMPLATE.format(
            context=build_context(results), question=question
        )

        print("\n" + "=" * 62)
        print(f"질문: {question}")
        print(f"({note})")
        print("=" * 62)

        print(f"\n검색된 근거: ", end="")
        print(", ".join(f"{doc}" for _, doc, _ in results))

        for label, prompt in [("느슨한 프롬프트", LOOSE_PROMPT),
                              ("엄격한 프롬프트", STRICT_PROMPT)]:
            print(f"\n  [{label}]")
            answer = ask_llm(prompt, user_message)
            for line in answer.strip().splitlines():
                print(f"    {line}")

    print("\n" + "-" * 62)
    print("두 번째 질문의 답변 두 개를 비교해보세요.")
    print("같은 근거를 받았는데도 프롬프트에 따라 결과가 달라집니다.")
    print("RAG 에서 프롬프트는 '말투 설정'이 아니라 '안전장치'입니다.")


if __name__ == "__main__":
    main()
