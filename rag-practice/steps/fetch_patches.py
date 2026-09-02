"""롤 패치노트를 받아와 data/patches/patches.json 으로 저장한다.

이 파일은 RAG 와 직접 상관없는 '배관 작업'이라 빈칸 없이 다 채워져 있습니다.
다만 실무에서 데이터를 구하는 일이 어떻게 생겼는지 볼 만하니 읽어보세요.

핵심은 이겁니다 — **HTML 구조가 청크 경계를 알려준다.**

패치노트 HTML 은 이렇게 생겼습니다:

    <div class="patch-change-block">
      <h3 class="change-title">아지르</h3>            ← 챔피언 이름
      <blockquote class="context">집중 공격이...</blockquote>   ← 설계 의도
      <h4 class="change-detail-title">Q - 사막의 맹습</h4>      ← 스킬
      <ul><li>피해량: 60/80/... ⇒ 75/95/...</li></ul>         ← 실제 수치
    </div>

즉 patch-change-block 하나가 청크 하나입니다.
2단계에서 마크다운을 "## " 로 잘랐던 것과 같은 원리이고, 마커만 다릅니다.
실제 문서는 이렇게 자기 구조를 어딘가에 갖고 있는 경우가 많습니다.
그걸 찾아내는 게 청킹의 절반입니다.

실행:
    python steps/fetch_patches.py
    python steps/fetch_patches.py --from 10 --to 17
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "patches" / "patches.json"

URL_TEMPLATE = (
    "https://www.leagueoflegends.com/ko-kr/news/game-updates/"
    "league-of-legends-patch-26-{n:02d}-notes/"
)


def fetch(url: str) -> str:
    """URL 의 HTML 을 문자열로 받아온다."""
    # User-Agent 를 안 보내면 봇으로 보고 막는 사이트가 많습니다.
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def strip_tags(html: str) -> str:
    """HTML 조각에서 태그를 걷어내고 읽을 수 있는 텍스트만 남긴다.

    정규식으로 HTML 을 파싱하는 건 원래 권장되지 않습니다(구조가 복잡하면 깨집니다).
    여기서는 이미 잘라낸 작은 조각만 다루고 형태도 단순해서 이 정도로 충분합니다.
    복잡한 사이트를 다룰 땐 BeautifulSoup 같은 전용 파서를 쓰세요.
    """
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<li>", "\n- ", html)                      # 목록은 - 로
    html = re.sub(r"</(h3|h4|p|blockquote|li|ul)>", "\n", html)  # 블록 끝은 줄바꿈으로
    html = re.sub(r"<[^>]+>", "", html)                       # 나머지 태그 제거
    html = html.replace("&nbsp;", " ").replace("&amp;", "&")
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n\s*\n+", "\n", html)
    return html.strip()


def parse_blocks(html: str, patch: str) -> list[dict]:
    """패치노트 HTML 에서 변경 블록들을 뽑아낸다."""
    raw_blocks = re.findall(
        r'<div class="patch-change-block[^"]*">(.*?)</div></div>', html, re.S
    )

    blocks = []
    for raw in raw_blocks:
        # h3.change-title 안의 링크 텍스트가 챔피언/아이템 이름입니다.
        match = re.search(r'<h3 class="change-title"[^>]*>.*?>([^<]+)</a>', raw, re.S)
        if not match:
            continue

        name = match.group(1).strip()
        text = strip_tags(raw)
        if len(text) < 40:      # 내용이 거의 없는 블록은 버린다
            continue

        blocks.append({"patch": patch, "name": name, "text": text})

    return blocks


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="롤 패치노트 수집")
    parser.add_argument("--from", dest="start", type=int, default=10, help="시작 패치 번호")
    parser.add_argument("--to", dest="end", type=int, default=17, help="끝 패치 번호")
    args = parser.parse_args()

    all_blocks: list[dict] = []

    for n in range(args.start, args.end + 1):
        patch = f"26.{n:02d}"
        url = URL_TEMPLATE.format(n=n)

        try:
            html = fetch(url)
        except urllib.error.HTTPError as e:
            print(f"  {patch}  건너뜀 (HTTP {e.code})")
            continue
        except Exception as e:
            print(f"  {patch}  실패: {e}")
            continue

        blocks = parse_blocks(html, patch)
        all_blocks.extend(blocks)
        print(f"  {patch}  블록 {len(blocks):2d}개")

        # 남의 서버를 두드리는 중입니다. 간격을 두는 게 예의이자 안전장치입니다.
        time.sleep(0.5)

    if not all_blocks:
        print("\n아무것도 받지 못했습니다. 네트워크나 URL 형식을 확인하세요.", file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(all_blocks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    names = {b["name"] for b in all_blocks}
    lengths = [len(b["text"]) for b in all_blocks]

    print(f"\n저장: {OUT_PATH.relative_to(ROOT)}")
    print(f"  변경 블록 {len(all_blocks)}개 / 등장한 챔피언·아이템 {len(names)}종")
    print(f"  블록 길이: 최소 {min(lengths)} / 평균 {sum(lengths) // len(lengths)} / 최대 {max(lengths)}자")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
