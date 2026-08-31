"""검색된 근거로 답변을 만든다 (RAG의 G).

RAG에서 생성 단계의 목표는 "잘 쓰는 것"이 아니라 **주어진 근거 밖으로 나가지 않는 것**입니다.
그래서 프롬프트의 대부분이 문장력이 아니라 제약 조건에 할애됩니다.

  - 검색된 청크에 있는 내용만 사용할 것
  - 문장마다 [1], [2] 로 출처를 표시할 것
  - 근거가 없으면 지어내지 말고 "문서에 없다"고 말할 것

세 번째가 가장 중요합니다. 모르는 걸 모른다고 하는 RAG는 신뢰할 수 있지만,
그럴듯하게 지어내는 RAG는 검색을 안 하느니만 못합니다.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic

from .config import CLAUDE_MODEL, MAX_TOKENS
from .retrieve import SearchResult, format_context

SYSTEM_PROMPT = """당신은 사내 문서 검색 도우미입니다.
사용자의 질문에, 아래에 제공되는 '참고 문서'만을 근거로 답변하세요.

규칙:
1. 참고 문서에 있는 내용만 사용합니다. 일반 상식이나 추측으로 보충하지 마세요.
2. 근거가 된 문서의 번호를 문장 끝에 [1], [2] 형식으로 표시합니다.
   여러 문서를 근거로 했다면 [1][3] 처럼 나열합니다.
3. 참고 문서에 답이 없으면 "제공된 문서에서 해당 내용을 찾을 수 없습니다."라고
   답하고, 관련이 있어 보이는 문서가 있다면 무엇을 찾았는지만 덧붙이세요.
4. 답변은 한국어로, 질문에 필요한 만큼만 간결하게 작성합니다.
5. 문서에 조건이나 예외가 붙어 있으면 빠뜨리지 말고 함께 알려주세요.
   (예: "연 15일" 뿐 아니라 "근속에 따라 최대 25일"까지)"""

USER_TEMPLATE = """참고 문서:
{context}

---

질문: {question}"""


@dataclass
class Answer:
    text: str
    results: list[SearchResult]     # 답변의 근거로 넘긴 청크들
    input_tokens: int = 0
    output_tokens: int = 0
    refused: bool = False

    @property
    def sources(self) -> list[str]:
        return [r.source for r in self.results]


def build_messages(question: str, results: list[SearchResult]) -> list[dict]:
    """검색 결과와 질문을 Claude에 보낼 메시지로 조립한다."""
    return [
        {
            "role": "user",
            "content": USER_TEMPLATE.format(
                context=format_context(results),
                question=question,
            ),
        }
    ]


def generate(
    question: str,
    results: list[SearchResult],
    client: anthropic.Anthropic | None = None,
) -> Answer:
    """검색 결과를 근거로 Claude에게 답변을 생성시킨다."""
    if not results:
        return Answer(
            text="검색된 문서가 없습니다. 인덱스가 비어 있거나 질문과 관련된 내용이 없습니다.",
            results=[],
        )

    client = client or anthropic.Anthropic()

    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=build_messages(question, results),
        # 적응형 사고: Claude가 필요한 만큼만 알아서 추론합니다.
        # 답변이 과하게 느리거나 비싸면 output_config={"effort": "low"} 를 추가해
        # 추론 깊이를 낮출 수 있습니다 (문서 Q&A 정도면 low로도 충분한 경우가 많습니다).
        thinking={"type": "adaptive"},
        # 안전 정책상 모델이 응답을 거절하는 경우, 같은 요청을 대체 모델로 자동 재시도합니다.
        # 사내 문서 Q&A에서는 거의 쓰일 일이 없지만 켜두어도 비용이 들지 않습니다.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )

    # 거절은 예외가 아니라 정상 응답(HTTP 200)으로 돌아오므로 stop_reason 을 먼저 봅니다.
    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None) or "사유 미제공"
        return Answer(
            text=f"모델이 이 요청에 대한 답변을 거절했습니다. ({detail})",
            results=results,
            refused=True,
        )

    text = "\n".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    return Answer(
        text=text,
        results=results,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
