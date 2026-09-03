"""OP.GG MCP 서버 호출 클라이언트.

MCP(Model Context Protocol)는 AI 도구가 외부 데이터에 접근하는 표준 규약입니다.
겉보기엔 거창하지만 실체는 **JSON-RPC 를 HTTP POST 로 주고받는 것**입니다.

    https://mcp-api.op.gg/mcp  로 POST
    body 는 {"jsonrpc":"2.0", "id":1, "method":"...", "params":{...}}

이 서버는 Streamable HTTP 방식이고, 지켜야 할 규칙이 세 가지 있습니다.

1. Accept 헤더에 "application/json, text/event-stream" 둘 다 넣어야 한다
   (스트리밍으로 응답할 수도 있어서 서버가 확인합니다. 빼면 406 이 납니다)

2. initialize 응답의 **mcp-session-id 헤더**를 받아
   이후 모든 요청에 다시 실어 보내야 한다

3. initialize 직후 notifications/initialized 를 보내야
   서버가 준비 완료로 간주한다 (이걸 빼면 tools/call 이 거부됩니다)

실행:
    python project/opgg-api.py                  # 도구 목록
    python project/opgg-api.py GAREN DARIUS     # 라인전 상성
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://mcp-api.op.gg/mcp"
PROTOCOL_VERSION = "2025-06-18"


class MCPError(RuntimeError):
    pass


class MCPClient:
    """MCP 서버 하나와 대화하는 최소 클라이언트."""

    def __init__(self, endpoint: str = ENDPOINT, timeout: int = 60):
        self.endpoint = endpoint
        self.timeout = timeout
        self.session_id: str | None = None
        self._next_id = 0

    # --- 저수준: 요청 한 번 보내기 ---

    def _post(self, payload: dict) -> tuple[dict | None, dict]:
        """JSON-RPC 요청을 보내고 (응답본문, 응답헤더) 를 돌려준다.

        헤더는 이름을 **소문자로 통일해서** 돌려줍니다.
        HTTP 헤더 이름은 대소문자를 구분하지 않기 때문에 서버마다 표기가 다릅니다.
        같은 서버라도 curl(HTTP/2)은 "mcp-session-id",
        urllib(HTTP/1.1)은 "Mcp-Session-Id" 로 받았습니다.
        """
        headers = {
            "Content-Type": "application/json",
            # 둘 다 명시해야 합니다. 서버가 스트리밍으로 답할 수도 있어서
            # 클라이언트가 그걸 받을 수 있는지 확인합니다.
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                resp_headers = {k.lower(): v for k, v in response.headers.items()}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            raise MCPError(f"HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise MCPError(f"연결 실패: {e.reason}") from e

        if not raw.strip():           # 알림(notification)은 본문이 없습니다
            return None, resp_headers

        return _parse_body(raw), resp_headers

    def _call(self, method: str, params: dict | None = None) -> dict:
        """응답을 기대하는 요청(request). id 를 붙여 보냅니다."""
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params

        body, headers = self._post(payload)
        if body is None:
            raise MCPError(f"{method}: 빈 응답")

        # 세션 ID 는 initialize 응답 헤더로 딱 한 번 옵니다.
        if self.session_id is None:
            self.session_id = headers.get("mcp-session-id")

        if "error" in body:
            e = body["error"]
            raise MCPError(f"{method}: [{e.get('code')}] {e.get('message')}")

        return body.get("result", {})

    def _notify(self, method: str) -> None:
        """응답을 기대하지 않는 알림(notification). id 를 붙이지 않습니다."""
        self._post({"jsonrpc": "2.0", "method": method})

    # --- 고수준: 실제로 쓸 것들 ---

    def connect(self) -> dict:
        """initialize → initialized 까지 마치고 서버 정보를 돌려준다."""
        result = self._call(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "opgg-python-client", "version": "0.1"},
            },
        )
        # 이 알림을 빼먹으면 이후 tools/call 이 거부됩니다.
        self._notify("notifications/initialized")
        return result

    def list_tools(self) -> list[dict]:
        return self._call("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict):
        """도구를 호출하고 결과를 돌려준다.

        MCP 는 결과를 항상 content 배열로 감쌉니다. 대부분 text 한 덩어리이고,
        그 안에 JSON 문자열이 들어 있는 경우가 많아 한 겹 더 벗겨줍니다.
        """
        result = self._call("tools/call", {"name": name, "arguments": arguments})

        if result.get("isError"):
            raise MCPError(f"{name}: {result}")

        texts = [c["text"] for c in result.get("content", []) if c.get("type") == "text"]
        if not texts:
            return result

        joined = "\n".join(texts).strip()

        # 응답 형식이 두 가지입니다.
        #   desired_output_fields 가 없는 도구(16개) → 평범한 JSON
        #   desired_output_fields 가 있는 도구(13개) → 압축 형식
        if joined.startswith("{") or joined.startswith("["):
            try:
                return json.loads(joined)
            except json.JSONDecodeError:
                pass

        if joined.startswith("class "):
            try:
                return parse_compact(joined)
            except MCPError:
                return joined           # 파싱 실패 시 원문이라도 돌려준다

        return joined


def parse_compact(text: str):
    """OP.GG 의 압축 응답 형식을 파이썬 dict/list 로 바꾼다.

    desired_output_fields 를 받는 도구(13개)는 JSON 대신 이런 형식으로 답합니다.

        class LolListChampionDetails: data
        class Data: champions
        class Champion: name,title,stats
        class Stats: hp,armor

        LolListChampionDetails(Data([Champion("가렌","데마시아의 힘",Stats(690,38))]))

    **키 이름을 위에서 한 번만 선언하고, 데이터는 위치 인자로만 보냅니다.**
    JSON 이라면 {"name":..., "title":..., "hp":...} 를 항목마다 반복해야 하는데,
    챔피언 168명이면 그 반복이 응답의 절반을 차지합니다. LLM 에 넣을 때
    토큰을 아끼려는 설계입니다.

    파싱은 두 단계입니다.
      1) class 줄들을 읽어 "클래스 이름 → 필드 이름 목록" 표를 만든다
      2) 본문을 재귀적으로 훑으며 위치 인자를 그 이름에 맞춰 붙인다
    """
    lines = text.strip().splitlines()

    schema: dict[str, list[str]] = {}
    body_start = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("class ") and ":" in line:
            name, fields = line[6:].split(":", 1)
            schema[name.strip()] = [f.strip() for f in fields.split(",") if f.strip()]
            body_start = i + 1
        elif line:
            break

    body = "\n".join(lines[body_start:]).strip()
    if not body:
        return {}

    value, pos = _parse_value(body, 0, schema)
    _ = pos
    return value


def _parse_value(s: str, i: int, schema: dict):
    """s[i] 부터 값 하나를 읽어 (값, 다음위치) 를 돌려준다."""
    while i < len(s) and s[i] in " \t\r\n":
        i += 1

    if i >= len(s):
        return None, i

    ch = s[i]

    if ch == '"':                                   # 문자열
        out, i = [], i + 1
        while i < len(s):
            if s[i] == "\\" and i + 1 < len(s):     # 이스케이프
                out.append(s[i + 1])
                i += 2
            elif s[i] == '"':
                return "".join(out), i + 1
            else:
                out.append(s[i])
                i += 1
        raise MCPError("닫히지 않은 문자열")

    if ch == "[":                                   # 리스트
        items, i = [], i + 1
        while i < len(s):
            while i < len(s) and s[i] in " \t\r\n,":
                i += 1
            if i < len(s) and s[i] == "]":
                return items, i + 1
            value, i = _parse_value(s, i, schema)
            items.append(value)
        raise MCPError("닫히지 않은 리스트")

    # 이름으로 시작하면 생성자 호출이거나 null/true/false 같은 맨 토큰
    start = i
    while i < len(s) and (s[i].isalnum() or s[i] in "_.-+"):
        i += 1
    token = s[start:i]

    if i < len(s) and s[i] == "(":                  # 생성자 호출
        fields = schema.get(token, [])
        args, i = [], i + 1
        while i < len(s):
            while i < len(s) and s[i] in " \t\r\n,":
                i += 1
            if i < len(s) and s[i] == ")":
                i += 1
                break
            value, i = _parse_value(s, i, schema)
            args.append(value)
        # 필드 이름을 아는 만큼 짝지어 dict 로, 모르면 리스트 그대로
        if fields:
            return {name: arg for name, arg in zip(fields, args)}, i
        return args, i

    if not token:                                   # 알 수 없는 문자는 건너뛴다
        return None, i + 1

    low = token.lower()
    if low in ("null", "none"):
        return None, i
    if low == "true":
        return True, i
    if low == "false":
        return False, i

    try:                                            # 숫자
        return (float(token) if ("." in token or "e" in low) else int(token)), i
    except ValueError:
        return token, i                             # 그 외는 문자열 취급


def _parse_body(raw: str) -> dict:
    """응답 본문을 파싱한다.

    서버가 SSE(text/event-stream) 로 답하면 "data: {...}" 형식으로 옵니다.
    지금은 JSON 으로 오지만, 언제든 바뀔 수 있으니 둘 다 처리합니다.
    """
    stripped = raw.lstrip()
    if stripped.startswith("{"):
        return json.loads(stripped)

    for line in raw.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())

    raise MCPError(f"응답을 이해할 수 없습니다: {raw[:200]}")


# ---------------------------------------------------------------------------


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    client = MCPClient()
    info = client.connect()
    server = info.get("serverInfo", {})
    print(f"연결됨: {server.get('name')} v{server.get('version')}")
    print(f"세션: {client.session_id}\n")

    if len(sys.argv) < 3:
        tools = client.list_tools()
        print(f"사용 가능한 도구 {len(tools)}개:\n")
        for t in tools:
            required = t.get("inputSchema", {}).get("required", [])
            print(f"  {t['name']}")
            print(f"      필수 인자: {required or '없음'}")
        print("\n예시:  python project/opgg-api.py GAREN DARIUS")
        # return 0

    '''my_champ, opponent = sys.argv[1].upper(), sys.argv[2].upper()
    print(f"라인전 상성 조회: {my_champ} vs {opponent}\n")

    data = client.call_tool(
        "lol_get_lane_matchup_guide",
        {
            "position": "top",
            "my_champion": my_champ,
            "opponent_champion": opponent,
            "lang": "ko_KR",
        },
    )'''


    # summary = data.get("data", {}).get("summary", {})
    # stats = summary.get("average_stats", {})
    # print(f"  {data.get('my_champion')} 전체 통계")
    # print(f"    표본      {stats.get('play', 0):,} 판")
    # print(f"    승률      {stats.get('win_rate', 0):.1%}")
    # print(f"    픽률      {stats.get('pick_rate', 0):.1%}")
    # print(f"    밴률      {stats.get('ban_rate', 0):.1%}")
    # print(f"\n  (전체 응답에는 훨씬 많은 정보가 들어 있습니다. 최상위 키: {list(data)})")


    # 챔피언 정보 불러오기
    # data = client.call_tool(
    #     "lol_list_champions",
    #     {
    #         "lang": 'ko',
    #         "desired_output_fields" : [
    #             "data.champions[].name"
    #         ]
    #     }
    # )

    data = client.call_tool(
        "lol_list_items",
        {
            "lang" : "ko",
        }
    )

    print(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
