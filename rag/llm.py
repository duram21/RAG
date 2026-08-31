"""LLM 공급자 추상화.

RAG 앱에서 "어떤 모델로 답변을 쓸 것인가"는 갈아끼울 수 있어야 합니다.
검색(임베딩·인덱스·랭킹)이 RAG의 본체이고 생성은 마지막 한 단계일 뿐인데,
공급자 SDK를 파이프라인 곳곳에 박아두면 나중에 바꿀 수가 없습니다.

그래서 여기서 두 가지만 정의합니다.

    Completion  — 공급자와 무관한 응답 형태
    LLMProvider — system + user 를 받아 Completion 을 돌려주는 함수 하나

나머지 코드(rag/generate.py)는 이 인터페이스만 알면 되고,
공급자 교체는 .env 의 LLM_PROVIDER 한 줄로 끝납니다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .config import CLAUDE_MODEL, GEMINI_MODEL, MAX_TOKENS


class LLMError(RuntimeError):
    """공급자별 예외를 사용자에게 보여줄 메시지로 통일한 것."""


@dataclass
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    refused: bool = False       # 안전 정책 등으로 모델이 답변을 거부한 경우
    model: str = ""


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, system: str, user: str) -> Completion: ...


# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------


class GeminiProvider:
    """Google Gemini (google-genai SDK).

    무료 티어가 있어 연습용으로 부담이 없습니다.
    https://aistudio.google.com/apikey 에서 키를 발급받아
    .env 에 GEMINI_API_KEY 로 넣으세요.
    """

    name = "gemini"

    def __init__(self, model: str = GEMINI_MODEL, api_key: str | None = None):
        from google import genai

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise LLMError(
                "GEMINI_API_KEY 가 설정되지 않았습니다.\n"
                "  https://aistudio.google.com/apikey 에서 발급 후 "
                ".env 에 GEMINI_API_KEY=... 를 넣으세요."
            )

        self.model = model
        self._client = genai.Client(api_key=key)

    def complete(self, system: str, user: str) -> Completion:
        from google.genai import errors, types

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=MAX_TOKENS,
                    # 근거가 이미 주어진 문서 Q&A라 깊은 추론이 필요 없습니다.
                    # 답변 품질이 아쉬우면 MEDIUM / HIGH 로 올려보세요.
                    thinking_config=types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.LOW
                    ),
                    # 근거 밖 내용을 지어내지 않도록 무작위성을 낮춥니다.
                    temperature=0.2,
                ),
            )
        except errors.ClientError as e:
            raise LLMError(f"Gemini 요청 오류 ({e.code}): {e.message}") from e
        except errors.ServerError as e:
            raise LLMError(f"Gemini 서버 오류 ({e.code}). 잠시 후 다시 시도하세요.") from e
        except errors.APIError as e:
            raise LLMError(f"Gemini API 오류: {e}") from e

        text = (response.text or "").strip()

        # 안전 필터에 걸리면 예외가 아니라 빈 응답 + finish_reason 으로 돌아옵니다.
        refused = False
        if not text:
            reason = None
            if response.candidates:
                reason = getattr(response.candidates[0], "finish_reason", None)
            refused = True
            text = f"모델이 응답을 생성하지 않았습니다. (finish_reason={reason})"

        usage = response.usage_metadata
        return Completion(
            text=text,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            refused=refused,
            model=self.model,
        )


# --------------------------------------------------------------------------
# Claude
# --------------------------------------------------------------------------


class ClaudeProvider:
    """Anthropic Claude (anthropic SDK).

    .env 에 ANTHROPIC_API_KEY 를 넣으세요.
    """

    name = "claude"

    def __init__(self, model: str = CLAUDE_MODEL, api_key: str | None = None):
        import anthropic

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError(
                "ANTHROPIC_API_KEY 가 설정되지 않았습니다.\n"
                "  https://console.anthropic.com/settings/keys 에서 발급 후 "
                ".env 에 ANTHROPIC_API_KEY=... 를 넣으세요."
            )

        self.model = model
        self._client = anthropic.Anthropic(api_key=key)

    def complete(self, system: str, user: str) -> Completion:
        import anthropic

        try:
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                # 적응형 사고: Claude가 필요한 만큼만 알아서 추론합니다.
                # 문서 Q&A 정도면 output_config={"effort": "low"} 로 낮춰도 충분합니다.
                thinking={"type": "adaptive"},
                # 안전 정책상 거절 시 같은 요청을 대체 모델로 자동 재시도합니다.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise LLMError("Claude 인증 실패: ANTHROPIC_API_KEY 를 확인하세요.") from e
        except anthropic.RateLimitError as e:
            retry_after = e.response.headers.get("retry-after", "60")
            raise LLMError(f"Claude 요청 한도 초과. {retry_after}초 뒤 재시도하세요.") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Claude API 오류 ({e.status_code}): {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Claude 연결 실패: 네트워크를 확인하세요.") from e

        # 거절은 예외가 아니라 정상 응답(HTTP 200)으로 오므로 stop_reason 을 먼저 봅니다.
        if response.stop_reason == "refusal":
            detail = getattr(response.stop_details, "explanation", None) or "사유 미제공"
            return Completion(
                text=f"모델이 이 요청에 대한 답변을 거절했습니다. ({detail})",
                refused=True,
                model=self.model,
            )

        text = "\n".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        return Completion(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )


# --------------------------------------------------------------------------
# 팩토리
# --------------------------------------------------------------------------

_PROVIDERS = {"gemini": GeminiProvider, "claude": ClaudeProvider}


def get_provider(name: str | None = None) -> LLMProvider:
    """이름으로 공급자를 만든다. 이름이 없으면 .env 의 LLM_PROVIDER 를 따른다."""
    name = (name or os.getenv("LLM_PROVIDER") or "gemini").strip().lower()

    if name not in _PROVIDERS:
        raise LLMError(
            f"알 수 없는 공급자 '{name}'. 사용 가능: {', '.join(_PROVIDERS)}"
        )

    return _PROVIDERS[name]()


def available_providers() -> list[str]:
    return list(_PROVIDERS)
