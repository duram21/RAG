"""5단계: 평가 — "잘 되는 것 같다" 를 숫자로 바꾸기

4단계까지로 RAG 는 완성됐습니다. 그런데 **얼마나 잘 되는지는 아무도 모릅니다.**
질문 몇 개를 눈으로 보고 "괜찮네" 했을 뿐입니다.

지금까지 만난 버그 두 개를 떠올려보세요.
    "\n##"  vs  "\n## "     — 이 문서에선 우연히 결과가 같았다
    model_name  vs  candidate — 한 번은 어쩌다 성공해서 정상처럼 보였다
둘 다 **겉보기엔 멀쩡했습니다.** 검색도 똑같습니다. 재보기 전엔 모릅니다.

측정하는 지표는 두 가지입니다.

    Recall@1  — 정답 청크가 1위로 나온 비율
    Recall@3  — 정답 청크가 상위 3개 안에 든 비율

Recall@3 이 중요한 이유: RAG 는 상위 k개를 통째로 LLM 에게 넘깁니다.
1위가 아니어도 3위 안에만 들면 LLM 이 그 안에서 답을 찾아냅니다.
그래서 실제 답변 품질에 더 가까운 지표입니다.

실행:
    python steps/step5_eval.py
"""

from step3_search import search

# ===========================================================================
# 평가셋 (정답지)
#
#   (질문, 정답 문서, 정답 섹션) 짝입니다.
#   이걸 만드는 게 평가에서 제일 손이 많이 가고, 제일 중요한 일입니다.
#   코드가 아니라 **판단**이 필요한 작업이라 자동화가 안 됩니다.
# ===========================================================================

EVAL_SET = [
    # --- 쉬운 질문: 문서의 단어를 거의 그대로 씀 ---
    ("연차 휴가는 며칠인가요?",              "01-휴가정책.md", "연차 휴가"),
    ("병가는 며칠까지 쓸 수 있나요?",         "01-휴가정책.md", "병가"),
    ("배포는 무슨 요일에 하나요?",            "03-개발프로세스.md", "배포"),
    ("코드 리뷰는 몇 명이 승인해야 하나요?",   "03-개발프로세스.md", "코드 리뷰"),

    # --- 보통: 다른 표현으로 물음 ---
    ("결혼하면 휴가 얼마나 나와요?",          "01-휴가정책.md", "경조사 휴가"),
    ("택시 타고 온 거 돈 받을 수 있나요?",     "02-경비정산.md", "교통비"),
    ("노트북을 잃어버렸어요",                "04-보안규정.md", "기기 관리"),
    ("비밀번호 규칙이 어떻게 되나요?",         "04-보안규정.md", "계정 및 인증"),
    ("책 사는 데 지원이 되나요?",             "02-경비정산.md", "도서 및 교육비"),

    # --- 어려움: 문서와 겹치는 단어가 거의 없음 ---
    ("서비스가 완전히 멈추면 몇 분 안에 대응해야 하죠?", "03-개발프로세스.md", "장애 대응"),
    ("새 협업 툴 쓰려면 누구한테 물어봐야 해?",          "04-보안규정.md", "외부 서비스 사용"),
    ("영수증 언제까지 올려야 하나요?",                  "02-경비정산.md", "정산 절차"),
    ("애 낳으면 며칠 쉬나요?",                        "01-휴가정책.md", "경조사 휴가"),
    ("ChatGPT에 고객 정보 넣어도 되나요?",             "04-보안규정.md", "외부 서비스 사용"),
    ("PR 몇 줄까지가 적당한가요?",                     "03-개발프로세스.md", "코드 리뷰"),
]


# ===========================================================================
# TODO 1. 검색 결과 안에 정답 청크가 있는지 판정하는 함수를 완성하세요.
#
#   results 는 3단계 search() 의 반환값입니다:
#       [(점수, 문서이름, 청크내용), ...]
#
#   청크의 **첫 줄이 섹션 제목**입니다. (2단계에서 "\n##" 로 잘랐으므로)
#       text.splitlines()[0].strip()   →  "연차 휴가"
#
#   그러니 정답 조건은:
#       문서이름이 want_doc 과 같고, 첫 줄이 want_section 과 같다
#
#   그런 게 results 앞에서 몇 번째에 있는지를 돌려주면 됩니다.
#   못 찾으면 None 을 돌려주세요.
#
#   힌트 (반복문으로 순위를 세는 모양):
#       for rank, (score, doc, text) in enumerate(results, start=1):
#           title = text.splitlines()[0].strip()
#           if doc == want_doc and title == want_section:
#               return rank
#       return None
# ===========================================================================

def find_rank(results, want_doc: str, want_section: str):
    """정답 청크가 몇 위인지 돌려준다. 없으면 None."""
    for rank, (score, doc, text) in enumerate(results, start = 1):
        title = text.splitlines()[0].strip()
        if doc == want_doc and title == want_section:
            return rank
    return None  # ← 여기를 채우세요


# ===========================================================================
# TODO 2. Recall@1 과 Recall@3 을 계산하세요.
#
#   ranks 는 질문마다의 정답 순위가 담긴 리스트입니다. 예: [1, 1, 2, None, 3, ...]
#
#   Recall@1 = (순위가 1인 질문 수) / (전체 질문 수)
#   Recall@3 = (순위가 1, 2, 3 중 하나인 질문 수) / (전체 질문 수)
#   None 은 정답을 아예 못 찾은 것이므로 둘 다 실패입니다.
#
#   힌트: sum() 은 True 를 1, False 를 0 으로 세어줍니다.
#       sum(1 for r in ranks if r == 1)                 ← 1위인 것의 개수
#       sum(1 for r in ranks if r is not None and r <= 3)
#
#   나눗셈은 / 입니다. 결과는 0.0 ~ 1.0 사이 소수가 됩니다.
# ===========================================================================

def recall_at(ranks, k: int) -> float:
    """정답이 상위 k위 안에 든 비율."""
    #Recall@1 
    a = sum(1 for r in ranks if r == 1)
    b =sum(1 for r in ranks if r is not None and r <= k)

    return b / len(ranks)  # ← 여기를 채우세요


# ===========================================================================
# 여기부터는 결과 출력용입니다. 고치지 않아도 됩니다.
# ===========================================================================

TOP_K = 3


def main() -> None:
    ranks = []
    failures = []

    for question, want_doc, want_section in EVAL_SET:
        results = search(question, k=TOP_K)
        rank = find_rank(results, want_doc, want_section)
        ranks.append(rank)

        if rank != 1:
            got = [(d, t.splitlines()[0].strip()) for _, d, t in results]
            failures.append((question, want_doc, want_section, rank, got))

    if all(r is None for r in ranks):
        print("TODO 1 이 비어 있습니다. find_rank 를 채우세요.")
        print("(정답을 하나도 못 찾았다면 대개 구현이 비어 있다는 뜻입니다)")
        return

    r1 = recall_at(ranks, 1)
    r3 = recall_at(ranks, 3)

    if r1 == 0.0 and r3 == 0.0:
        print("TODO 2 가 비어 있습니다. recall_at 을 채우세요.")
        return

    total = len(EVAL_SET)
    print("\n" + "=" * 62)
    print(f"평가 결과  (질문 {total}개, 상위 {TOP_K}개 검색)")
    print("=" * 62)
    print(f"  Recall@1 : {r1:.1%}   ({round(r1 * total)}/{total})   정답이 1위")
    print(f"  Recall@3 : {r3:.1%}   ({round(r3 * total)}/{total})   정답이 3위 안")

    if not failures:
        print("\n전부 1위입니다. 평가셋이 너무 쉬운 게 아닌지 의심해보세요.")
        return

    print("\n" + "=" * 62)
    print(f"1위를 놓친 질문 {len(failures)}개 — 여기가 개선할 지점입니다")
    print("=" * 62)

    for question, want_doc, want_section, rank, got in failures:
        status = f"{rank}위" if rank else "3위 안에 없음"
        print(f"\n  Q. {question}")
        print(f"     정답: [{want_doc}] {want_section}  →  {status}")
        for i, (doc, title) in enumerate(got, start=1):
            hit = " ←정답" if (doc == want_doc and title == want_section) else ""
            print(f"       {i}위  [{doc}] {title}{hit}")


# ===========================================================================
# 다 돌린 뒤에 생각해볼 것
#
#   1. 실패한 질문들의 공통점이 뭔가요?
#      보통 이런 것들이 걸립니다.
#        - 문서에 없는 단어로 물었을 때 ("애 낳으면" vs 문서의 "배우자 출산")
#        - 한 섹션에 여러 주제가 섞여 있을 때
#        - 여러 섹션이 다 그럴듯할 때 (경조사 휴가 vs 연차 휴가)
#
#   2. 평가셋을 직접 늘려보세요.
#      EVAL_SET 에 본인이 궁금한 질문을 추가하면 됩니다.
#      **틀릴 것 같은 질문**을 일부러 넣는 게 요령입니다.
#      다 맞는 평가셋은 아무것도 알려주지 않습니다.
#
#   3. 이 숫자가 있어야 다음 단계가 의미를 가집니다.
#      하이브리드 검색이든 청크 크기 조정이든, 바꾼 뒤 이 스크립트를 다시 돌려
#      숫자가 올랐는지 보면 됩니다. 그게 "개선했다" 의 유일한 증거입니다.
# ===========================================================================


if __name__ == "__main__":
    main()
