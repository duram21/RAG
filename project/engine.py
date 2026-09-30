"""무거운 것을 한 번만 로딩해 들고 있는 곳.

임베딩 모델(471MB)과 인덱스를 **한 번만** 로딩하고, 검색과 답변 생성을
제공합니다. cli / web / voice 가 전부 이걸 공유합니다.

    from engine import Engine

    engine = Engine()                  # 로딩 (느림. 한 번만)
    engine.search("장화 효과")          # 검색만
    engine.answer("장화 효과")          # 검색 + LLM 답변

왜 따로 뺐냐면 — 이 로딩 로직이 web.py 안에 있으면 voice.py 를 만들 때
그대로 복사해야 합니다. 그러면 고칠 곳이 두 배가 되죠.

앞으로 할 일 (여기 인터페이스를 유지하면 앱들은 안 건드려도 됩니다):
  - answer_stream() 추가 — 음성 대화에는 스트리밍이 필수입니다
  - 소스 여러 개 (챔피언, 패치노트) 지원
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INDEX_DIR = HERE / "data"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

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


def load_env() -> Path | None:
    """.env 를 여러 곳에서 찾는다.

    키를 여러 파일에 복사해두면 나중에 하나만 바꾸고 "왜 안 되지" 하게 됩니다.
    """
    for candidate in (HERE / ".env", ROOT / ".env", ROOT / "rag-practice" / ".env"):
        if candidate.exists():
            load_dotenv(candidate)
            return candidate
    return None


class EngineError(RuntimeError):
    pass


@dataclass
class Answer:
    text: str
    sources: list = field(default_factory=list)   # [(점수, record), ...]
    search_ms: float = 0.0
    llm_ms: float = 0.0
    unverified: list[str] = field(default_factory=list)
    model: str = ""


class Engine:
    """인덱스와 모델을 들고 있으면서 검색·답변을 제공한다."""

    def __init__(self, index_dir: Path = INDEX_DIR, with_llm: bool = True,
                 verbose: bool = True):
        self.index_dir = index_dir
        self._say = print if verbose else (lambda *a, **k: None)

        self.vectors, self.records = self._load_index()
        self._say(f"인덱스: 아이템 {len(self.records)}개, {self.vectors.shape[1]}차원")

        # 임포트를 여기서 하는 이유: sentence_transformers 는 무거워서,
        # Engine 을 안 만드는 코드까지 느려지지 않게 합니다.
        from sentence_transformers import SentenceTransformer

        self._say(f"임베딩 모델 로딩: {EMBED_MODEL_NAME}")
        self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)

        self.llm = None
        if with_llm:
            self.env_path = load_env()
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                from google import genai
                from google.genai import types

                self.llm = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(timeout=60_000),
                )
            else:
                self._say("경고: GEMINI_API_KEY 가 없습니다. 검색만 동작합니다.")

    # --- 인덱스 ---

    def _load_index(self):
        npy_path = self.index_dir / "index.npy"
        json_path = self.index_dir / "index.json"

        if not npy_path.exists():
            raise EngineError(
                f"인덱스가 없습니다: {npy_path}\n"
                "  먼저 실행하세요:  python project/build_index.py"
            )

        vectors = np.load(npy_path)
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        records = meta["records"]

        # 인덱스를 만든 모델과 질문을 인코딩할 모델이 다르면 검색이 무의미합니다.
        # 차원이 우연히 같으면 에러도 안 나고 조용히 엉뚱한 결과가 나옵니다.
        if meta.get("model") != EMBED_MODEL_NAME:
            raise EngineError(
                f"인덱스는 '{meta.get('model')}' 로 만들어졌는데 "
                f"현재 설정은 '{EMBED_MODEL_NAME}' 입니다.\n"
                "  build_index.py 를 다시 실행하세요."
            )

        # 벡터와 records 는 같은 순서로 만들어졌습니다. 개수가 어긋나면
        # 검색 결과가 엉뚱한 아이템을 가리키는데 에러는 안 납니다.
        if len(vectors) != len(records):
            raise EngineError(
                f"벡터 {len(vectors)}개 ≠ records {len(records)}개. "
                "인덱스를 다시 만드세요."
            )

        return vectors, records

    # --- 검색 ---

    def search(self, question: str, k: int = 5):
        """질문과 가까운 아이템 k개를 [(점수, record), ...] 로 돌려준다."""
        query_vec = self.embed_model.encode(
            ["query: " + question], normalize_embeddings=True
        )[0]

        # 벡터가 모두 L2 정규화되어 있으므로 내적이 곧 코사인 유사도입니다.
        scores = self.vectors @ query_vec

        # 상위 k개의 '번호'를 구한 뒤 그 번호로 records 를 찾아갑니다.
        top = np.argsort(-scores)[:k]
        return [(float(scores[i]), self.records[i]) for i in top]

    # --- 생성 ---

    def answer(self, question: str, k: int = 5) -> Answer:
        started = time.perf_counter()
        results = self.search(question, k)
        search_ms = (time.perf_counter() - started) * 1000

        if self.llm is None:
            return Answer(
                text="GEMINI_API_KEY 가 없어 검색 결과만 표시합니다.",
                sources=results,
                search_ms=search_ms,
            )

        context = build_context(results)
        user_message = f"참고 자료:\n{context}\n\n---\n\n질문: {question}"

        started = time.perf_counter()
        text, used_model = self._call_llm(user_message)
        llm_ms = (time.perf_counter() - started) * 1000

        return Answer(
            text=text.strip(),
            sources=results,
            search_ms=search_ms,
            llm_ms=llm_ms,
            unverified=check_numbers(text, context),
            model=used_model,
        )

    def _call_llm(self, user_message: str) -> tuple[str, str]:
        """무료 티어의 503/429/504 에 대비해 재시도와 모델 폴백을 넣었다."""
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=2000,
            temperature=0.1,   # 수치를 옮기는 작업이라 무작위성을 낮춘다
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )

        for candidate in [GEMINI_MODEL] + GEMINI_FALLBACKS:
            for attempt in range(3):
                try:
                    r = self.llm.models.generate_content(
                        model=candidate, contents=user_message, config=config
                    )
                    return (r.text or "[빈 응답]"), candidate
                except errors.APIError as e:
                    if e.code not in (429, 503, 504):
                        return f"[API 오류 {e.code}: {e.message}]", candidate
                    if attempt < 2:
                        time.sleep(2**attempt)

        return "[모든 모델이 응답하지 않았습니다. 잠시 후 다시 시도하세요.]", ""


# ---------------------------------------------------------------------------
# 앱들이 같이 쓰는 함수들
# ---------------------------------------------------------------------------


def build_context(results) -> str:
    """검색 결과를 LLM 에게 넘길 문자열로 조립한다."""
    return "\n\n".join(
        f"[{i}] {rec['text']}" for i, (_, rec) in enumerate(results, start=1)
    )


def check_numbers(answer: str, context: str) -> list[str]:
    """답변에 나온 숫자 중 근거에 없는 것을 찾아낸다.

    완벽한 검사는 아닙니다. LLM 이 "3가지" 처럼 스스로 센 숫자를 쓸 수 있어
    1~10 은 제외합니다. 자동 검사는 의심 목록을 좁혀줄 뿐이고,
    "지어냈나"는 보지만 "말이 되나"는 못 봅니다.
    """
    in_answer = set(re.findall(r"\d+(?:\.\d+)?", answer))
    in_context = set(re.findall(r"\d+(?:\.\d+)?", context))
    suspicious = in_answer - in_context
    return sorted(n for n in suspicious if not (n.isdigit() and int(n) <= 10))


if __name__ == "__main__":
    # 직접 실행하면 동작 확인만 합니다.
    sys.stdout.reconfigure(encoding="utf-8")
    engine = Engine()
    a = engine.answer("장화 효과가 뭐야?", k=3)
    print(f"\n검색 {a.search_ms:.0f}ms / 생성 {a.llm_ms:.0f}ms ({a.model})")
    print(f"근거: {', '.join(r['name'] for _, r in a.sources)}")
    print(f"\n{a.text}")
