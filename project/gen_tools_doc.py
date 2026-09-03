"""OP.GG MCP 도구 목록을 문서(OPGG_TOOLS.md)로 뽑아낸다.

도구가 29개라 손으로 적으면 틀리고, 서버가 바꾸면 낡습니다.
스키마에서 직접 생성하면 다시 돌리기만 하면 항상 최신입니다.

실행:
    python project/gen_tools_doc.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "OPGG_TOOLS.md"


def load_client_module():
    """opgg-api.py 는 이름에 하이픈이 있어 평범한 import 가 안 된다.

    파이썬 모듈 이름에는 하이픈을 못 씁니다(빼기 연산자로 읽히니까요).
    그래서 파일 경로로 직접 불러옵니다.
    (애초에 opgg_api.py 로 지었으면 그냥 import 로 끝났을 일입니다.)
    """
    spec = importlib.util.spec_from_file_location("opgg", HERE / "opgg-api.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe_arg(name: str, spec: dict, required: bool) -> str:
    """인자 하나를 표의 한 줄로 만든다."""
    kind = spec.get("type", "?")
    if kind == "array":
        kind = f"{spec.get('items', {}).get('type', '?')}[]"

    if "enum" in spec:
        # 마크다운 표에서 | 는 칸 구분자라 백슬래시로 막아야 합니다.
        # 파이썬 문자열에서 \| 는 유효한 이스케이프가 아니므로 r"" 로 씁니다.
        allowed = r" \| ".join(f"`{v}`" for v in spec["enum"])
    elif "default" in spec:
        allowed = f"기본값 `{spec['default']}`"
    else:
        allowed = ""

    # 설명에서 "Examples: ..." 부분을 뽑아 예시 열에 넣는다
    desc = (spec.get("description") or "").replace("\n", " ")
    example = ""
    m = re.search(r"Examples?:\s*(.+)$", desc)
    if m:
        example = m.group(1).strip()[:40]
        desc = desc[: m.start()].strip()

    mark = "**필수**" if required else "선택"
    return f"| `{name}` | {kind} | {mark} | {allowed or example} | {desc[:70]} |"


def extract_output_fields(desc: str) -> list[str]:
    """desired_output_fields 설명에서 사용 가능한 필드 경로만 뽑아낸다."""
    fields = []
    collecting = False
    for line in (desc or "").splitlines():
        line = line.strip()
        if line.startswith("Available fields:"):
            collecting = True
            continue
        if collecting:
            if line.startswith("- "):
                fields.append(line[2:])
            elif line and not line.startswith("-"):
                break
    return fields


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    opgg = load_client_module()
    client = opgg.MCPClient()
    client.connect()
    tools = client.list_tools()
    print(f"도구 {len(tools)}개 수집됨. 문서 생성 중...")

    out: list[str] = []
    add = out.append

    add("# OP.GG MCP 도구 레퍼런스")
    add("")
    add("`python project/gen_tools_doc.py` 로 서버 스키마에서 자동 생성됩니다.")
    add("직접 고치지 마세요 — 다시 생성하면 사라집니다.")
    add("")
    add("## 쓰는 법")
    add("")
    add("```python")
    add("import importlib.util")
    add("spec = importlib.util.spec_from_file_location('opgg', 'project/opgg-api.py')")
    add("opgg = importlib.util.module_from_spec(spec); spec.loader.exec_module(opgg)")
    add("")
    add("client = opgg.MCPClient()")
    add("client.connect()                      # 반드시 먼저 호출")
    add("data = client.call_tool('도구이름', {인자들})")
    add("```")
    add("")
    add("## 응답 형식이 두 가지입니다")
    add("")
    add("| 표시 | 조건 | 형태 |")
    add("|---|---|---|")
    add("| **압축** | `desired_output_fields` 를 받는 도구 | `class ...` 선언 + 위치 인자. "
        "`call_tool` 이 dict 로 변환해서 돌려줍니다 |")
    add("| **JSON** | 그 외 | 평범한 JSON |")
    add("")
    add("`desired_output_fields` 는 **닫힌 집합**입니다. "
        "각 도구의 '출력 필드' 목록에 있는 것만 쓸 수 있고, 없는 이름을 지어내면 거부됩니다.")
    add("")
    add("## 챔피언 표기법이 도구마다 다릅니다")
    add("")
    add("| 인자 이름 | 표기 | 예시 |")
    add("|---|---|---|")
    add("| `champions` (배열) | 내부 코드명 | `Garen`, `MonkeyKing` |")
    add("| `champion`, `my_champion`, `opponent_champion` | 대문자+언더바 | `GAREN`, `MONKEY_KING` |")
    add("")
    add("내부 코드명은 `python project/opgg-api.py --champions` 로 확인하세요.")
    add("")
    add("---")
    add("")

    # 게임별로 묶어서 정리
    groups: dict[str, list] = {"lol": [], "tft": [], "valorant": []}
    for t in tools:
        prefix = t["name"].split("_")[0]
        groups.setdefault(prefix, []).append(t)

    titles = {"lol": "리그 오브 레전드", "tft": "전략적 팀 전투(TFT)", "valorant": "발로란트"}

    for prefix, items in groups.items():
        add(f"# {titles.get(prefix, prefix)}  ({len(items)}개)")
        add("")

        for t in sorted(items, key=lambda x: x["name"]):
            schema = t.get("inputSchema", {})
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            compact = "desired_output_fields" in props

            add(f"## `{t['name']}`")
            add("")
            add(f"> {(t.get('description') or '').strip()}")
            add("")
            add(f"응답 형식: **{'압축' if compact else 'JSON'}**")
            add("")

            if props:
                add("| 인자 | 타입 | 필수 | 값 | 설명 |")
                add("|---|---|---|---|---|")
                # 필수를 위로
                for name in sorted(props, key=lambda n: (n not in required, n)):
                    if name == "desired_output_fields":
                        continue
                    add(describe_arg(name, props[name], name in required))
                if compact:
                    add("| `desired_output_fields` | string[] | **필수** | 아래 목록 참고 | "
                        "받아올 필드 경로 |")
                add("")
            else:
                add("인자 없음")
                add("")

            if compact:
                fields = extract_output_fields(props["desired_output_fields"].get("description"))
                if fields:
                    add("<details><summary>출력 필드 목록</summary>")
                    add("")
                    add("```")
                    for f in fields:
                        add(f)
                    add("```")
                    add("")
                    add("</details>")
                    add("")

            add("---")
            add("")

    OUT_PATH.write_text("\n".join(out), encoding="utf-8")
    print(f"생성 완료: {OUT_PATH.relative_to(HERE.parent)}  ({len(out)}줄)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
