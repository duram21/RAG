"""검색된 근거로 답변을 만든다 (RAG의 G).

RAG에서 생성 단계의 목표는 "잘 쓰는 것"이 아니라 **주어진 근거 밖으로 나가지 않는 것**입니다.
그래서 프롬프트의 대부분이 문장력이 아니라 제약 조건에 할애됩니다.

  - 검색된 청크에 있는 내용만 사용할 것
  - 문장마다 [1], [2] 로 출처를 표시할 것
  - 근거가 없으면 지어내지 말고 "문서에 없다"고 말할 것

세 번째가 가장 중요합니다. 모르는 걸 모른다고 하는 RAG는 신뢰할 수 있지만,
그럴듯하게 지어내는 RAG는 검색을 안 하느니만 못합니다.

어떤 모델로 생성할지는 이 파일이 알 바가 아닙니다 — rag/llm.py 가 담당합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .llm import LLMProvider, get_provider
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
    results: list[SearchResult] = field(default_factory=list)  # 근거로 넘긴 청크들
    input_tokens: int = 0
    output_tokens: int = 0
    refused: bool = False
    model: str = ""

    @property
    def sources(self) -> list[str]:
        return [r.source for r in self.results]


def build_user_message(question: str, results: list[SearchResult]) -> str:
    """검색 결과와 질문을 하나의 사용자 메시지로 조립한다."""
    return USER_TEMPLATE.format(
        context=format_context(results),
        question=question,
    )


def generate(
    question: str,
    results: list[SearchResult],
    provider: LLMProvider | None = None,
) -> Answer:
    """검색 결과를 근거로 LLM에게 답변을 생성시킨다."""
    if not results:
        return Answer(
            text="검색된 문서가 없습니다. 인덱스가 비어 있거나 질문과 관련된 내용이 없습니다."
        )

    provider = provider or get_provider()
    completion = provider.complete(
        system=SYSTEM_PROMPT,
        user=build_user_message(question, results),
    )

    return Answer(
        text=completion.text,
        results=results,
        input_tokens=completion.input_tokens,
        output_tokens=completion.output_tokens,
        refused=completion.refused,
        model=completion.model,
    )
