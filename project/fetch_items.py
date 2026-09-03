"""롤 아이템 목록을 받아와 project/data/items.json 으로 저장한다.

    python project/fetch_items.py
    python project/fetch_items.py --lang en_US
    python project/fetch_items.py --map HOWLING_ABYSS

받아온 데이터는 나중에 RAG 로 검색할 원본이 됩니다.
"아이템 효과가 뭐야?" 에 답하려면 먼저 이 데이터가 있어야 합니다.

주의할 점:
  - 서버가 가끔 빈 배열이나 부분 응답을 돌려줍니다. 실제로 같은 요청에
    199개, 0개, 315개가 번갈아 나온 적이 있습니다. 그래서 개수가 수상하면
    다시 시도하고, 그래도 이상하면 사람에게 알립니다.
  - description 에 <mainText><stats> 같은 태그가 섞여 있습니다.
    사람이 읽을 수 있게 걷어낸 필드를 따로 만들어 둡니다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "data"
OUT_PATH = OUT_DIR / "items.json"

MIN_EXPECTED = 100   # 이보다 적게 오면 응답이 잘린 것으로 본다


def load_client_module():
    """opgg-api.py 는 파일명에 하이픈이 있어 평범한 import 가 안 된다."""
    spec = importlib.util.spec_from_file_location("opgg", HERE / "opgg-api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_tags(html: str) -> str:
    """아이템 설명에서 태그를 걷어내 읽을 수 있는 문장으로 만든다.

    원본은 이렇게 생겼습니다:
        <mainText><stats>이동 속도 <attention>25</attention></stats></mainText><br>

    태그 이름 자체가 의미를 담고 있는 경우가 있어서(passive, active 등)
    그런 것만 한국어 라벨로 바꾸고 나머지는 지웁니다.
    """
    if not html:
        return ""

    text = html
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<li>", "\n· ", text)
    # 의미가 있는 태그는 라벨로 남긴다
    text = re.sub(r"<passive>", "[지속효과] ", text)
    text = re.sub(r"<active>", "[사용효과] ", text)
    text = re.sub(r"<rarityMythic>", "[신화] ", text)
    text = re.sub(r"<rarityLegendary>", "[전설] ", text)
    text = re.sub(r"<[^>]+>", "", text)          # 나머지 태그 제거
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch_items(client, lang: str, map_name: str | None, retries: int = 3) -> list[dict]:
    """아이템 목록을 받아온다. 응답이 수상하면 다시 시도한다."""
    args: dict = {"lang": lang}
    if map_name:
        args["map"] = map_name

    best: list[dict] = []
    for attempt in range(1, retries + 1):
        data = client.call_tool("lol_list_items", args)
        items = data.get("data", {}).get("items", []) if isinstance(data, dict) else []

        print(f"  시도 {attempt}: {len(items)}개")

        if len(items) > len(best):
            best = items
        if len(best) >= MIN_EXPECTED:
            break
        if attempt < retries:
            time.sleep(1.5)

    return best


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="롤 아이템 목록을 받아 저장합니다.")
    parser.add_argument("--lang", default="ko", help="언어 코드 (기본 ko)")
    parser.add_argument("--map", dest="map_name", default=None,
                        help="SUMMONERS_RIFT | HOWLING_ABYSS | NEXUS_BLITZ | ARENA_MAP_1")
    parser.add_argument("--out", type=Path, default=OUT_PATH, help="저장 경로")
    args = parser.parse_args()

    opgg = load_client_module()
    client = opgg.MCPClient()
    client.connect()
    print(f"연결됨. 아이템 조회 (lang={args.lang}, map={args.map_name or '기본'})")

    items = fetch_items(client, args.lang, args.map_name)

    if not items:
        print("\n아이템을 하나도 받지 못했습니다.", file=sys.stderr)
        return 1
    if len(items) < MIN_EXPECTED:
        print(f"\n경고: {len(items)}개만 받았습니다. 응답이 잘렸을 수 있으니 "
              f"다시 실행해보세요.", file=sys.stderr)

    # 사람이 읽을 수 있는 설명을 덧붙인다 (원본 description 은 그대로 둔다)
    for item in items:
        item["description_text"] = strip_tags(item.get("description", ""))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "lang": args.lang,
        "map": args.map_name or "SUMMONERS_RIFT",
        "count": len(items),
        "items": items,
    }
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    size_kb = args.out.stat().st_size / 1024
    with_desc = sum(1 for i in items if i["description_text"])
    prices = [i.get("gold_total", 0) for i in items if i.get("gold_total")]

    print(f"\n저장: {args.out.relative_to(HERE.parent)}  ({size_kb:.0f} KB)")
    print(f"  아이템        {len(items)}개")
    print(f"  설명 있는 것  {with_desc}개")
    if prices:
        print(f"  가격          {min(prices)} ~ {max(prices)} 골드")

    print("\n--- 샘플 3개 ---")
    for item in items[:3]:
        print(f"\n[{item['item_id']}] {item['name']}  ({item.get('gold_total', 0)}골드)")
        preview = item["description_text"].replace("\n", " ")[:90]
        print(f"  {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
