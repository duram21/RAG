"""아이템 Q&A 웹 UI.

    python project/web.py
    → 브라우저에서 http://127.0.0.1:8000

터미널에서 매번 실행하면 모델 로딩에 40초씩 걸립니다.
서버로 띄우면 시작할 때 한 번만 로딩하고, 이후 질문은 즉시 처리됩니다.

무거운 로딩과 검색·생성 로직은 engine.py 에 있습니다. 여기는 껍데기입니다.

추가 설치가 필요 없습니다. starlette 와 uvicorn 은 이미
다른 패키지의 의존성으로 설치되어 있습니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine  # noqa: E402

# 서버가 뜰 때 한 번만 로딩합니다.
ENGINE = Engine()


async def index(request: Request) -> HTMLResponse:
    return HTMLResponse(PAGE)


async def ask(request: Request) -> JSONResponse:
    body = await request.json()
    question = (body.get("question") or "").strip()
    k = int(body.get("k") or 5)

    if not question:
        return JSONResponse({"error": "질문이 비어 있습니다."}, status_code=400)

    a = ENGINE.answer(question, k)

    return JSONResponse({
        "answer": a.text,
        "sources": [
            {
                "rank": i,
                "score": round(score, 4),
                "name": rec["name"],
                "gold": rec["gold_total"],
                "text": rec["text"],
            }
            for i, (score, rec) in enumerate(a.sources, start=1)
        ],
        "search_ms": round(a.search_ms),
        "llm_ms": round(a.llm_ms),
        "unverified": a.unverified,
    })


PAGE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>롤 아이템 Q&amp;A</title>
<style>
  :root {
    color-scheme: light;
    --bg: #f7f7f5; --card: #ffffff; --line: #e4e4e0;
    --fg: #1a1a18; --muted: #74746e; --accent: #b4623a;
    --warn-bg: #fdf3e3; --warn-fg: #8a5a12; --warn-line: #e8d5ae;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #1a1a18; --card: #232320; --line: #34342f;
      --fg: #ecece8; --muted: #9a9a92; --accent: #d98a5f;
      --warn-bg: #2e2415; --warn-fg: #e0b978; --warn-line: #4a3a1e;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #1a1a18; --card: #232320; --line: #34342f;
    --fg: #ecece8; --muted: #9a9a92; --accent: #d98a5f;
    --warn-bg: #2e2415; --warn-fg: #e0b978; --warn-line: #4a3a1e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--fg);
    font: 15px/1.6 system-ui, -apple-system, "Segoe UI", "Malgun Gothic", sans-serif;
    padding: 0 16px;
  }
  .wrap { max-width: 760px; margin: 0 auto; padding-block: 40px 60px; }
  h1 { font-size: 20px; margin: 0 0 4px; letter-spacing: -0.01em; }
  .sub { color: var(--muted); font-size: 13px; margin: 0 0 24px; }

  form { display: flex; gap: 8px; flex-wrap: wrap; }
  input[type=text] {
    flex: 1 1 260px; min-width: 0; padding: 12px 14px; font: inherit;
    background: var(--card); color: var(--fg);
    border: 1px solid var(--line); border-radius: 10px;
  }
  input[type=text]:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  select, button {
    padding: 12px 16px; font: inherit; border-radius: 10px;
    border: 1px solid var(--line); background: var(--card); color: var(--fg);
  }
  button[type=submit] {
    background: var(--accent); color: #fff; border-color: transparent;
    cursor: pointer; font-weight: 600; min-width: 84px;
  }
  button[type=submit]:disabled { opacity: .55; cursor: progress; }

  .examples { margin: 12px 0 0; display: flex; gap: 6px; flex-wrap: wrap; }
  .examples button {
    background: transparent; color: var(--muted); border: 1px solid var(--line);
    font-size: 12.5px; padding: 5px 10px; font-weight: 400; cursor: pointer;
  }
  .examples button:hover { color: var(--fg); border-color: var(--accent); }

  .card {
    background: var(--card); border: 1px solid var(--line);
    border-radius: 12px; padding: 18px 20px; margin-top: 20px;
  }
  .answer { white-space: pre-wrap; }
  .answer strong { font-weight: 650; }

  .meta { color: var(--muted); font-size: 12px; margin-top: 14px;
          border-top: 1px solid var(--line); padding-top: 10px;
          font-variant-numeric: tabular-nums; }

  .warn { margin-top: 12px; padding: 10px 12px; border-radius: 8px;
          background: var(--warn-bg); color: var(--warn-fg);
          border: 1px solid var(--warn-line); font-size: 13px; }

  details { margin-top: 14px; }
  summary { cursor: pointer; color: var(--muted); font-size: 13px; }
  .src { border-top: 1px solid var(--line); padding: 10px 0; }
  .srchead { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
  .rank { color: var(--accent); font-weight: 650; font-size: 13px; }
  .gold { color: var(--muted); font-size: 12.5px; }
  .score { margin-left: auto; color: var(--muted); font-size: 12px;
           font-variant-numeric: tabular-nums; }
  .srcbody { color: var(--muted); font-size: 13px; white-space: pre-wrap;
             margin-top: 4px; }

  .spin { display: inline-block; width: 13px; height: 13px; vertical-align: -2px;
          border: 2px solid var(--line); border-top-color: var(--accent);
          border-radius: 50%; animation: r .7s linear infinite; margin-right: 8px; }
  @keyframes r { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="wrap">
  <h1>롤 아이템 Q&amp;A</h1>
  <p class="sub">아이템 292개를 검색해 근거로 답합니다. 자료에 없으면 없다고 답합니다.</p>

  <form id="f">
    <input type="text" id="q" placeholder="예) 무한의 대검이랑 B.F. 대검 차이가 뭐야?" autofocus autocomplete="off">
    <select id="k" title="근거로 넘길 아이템 수">
      <option value="3">3개</option>
      <option value="5" selected>5개</option>
      <option value="8">8개</option>
    </select>
    <button type="submit" id="go">질문</button>
  </form>

  <div class="examples" id="ex">
    <button type="button">장화 효과가 뭐야?</button>
    <button type="button">체력 회복되는 아이템 뭐 있어?</button>
    <button type="button">궁극기 쿨타임 줄여주는 아이템</button>
    <button type="button">무한의 대검이랑 B.F. 대검 차이</button>
  </div>

  <div id="out"></div>
</div>

<script>
const $ = (s) => document.querySelector(s);
const out = $("#out"), go = $("#go"), q = $("#q");

function esc(s) {
  return String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}
// LLM 이 **굵게** 를 자주 쓰므로 그것만 살린다
function fmt(s) {
  return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}

$("#ex").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  q.value = e.target.textContent;
  $("#f").requestSubmit();
});

$("#f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = q.value.trim();
  if (!question) return;

  go.disabled = true;
  out.innerHTML = '<div class="card"><span class="spin"></span>검색하고 답변을 만드는 중...</div>';

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, k: Number($("#k").value) }),
    });
    const d = await res.json();
    if (d.error) { out.innerHTML = '<div class="card">' + esc(d.error) + '</div>'; return; }

    let html = '<div class="card"><div class="answer">' + fmt(d.answer) + '</div>';

    if (d.unverified && d.unverified.length) {
      html += '<div class="warn">근거에 없는 숫자: ' + esc(d.unverified.join(", ")) +
              ' — 지어낸 것일 수도, 검사가 과민한 것일 수도 있습니다.</div>';
    }

    html += '<div class="meta">검색 ' + d.search_ms + 'ms · 생성 ' + d.llm_ms + 'ms</div>';

    html += '<details><summary>근거로 쓴 아이템 ' + d.sources.length + '개 보기</summary>';
    for (const s of d.sources) {
      const body = s.text.split("\n").slice(1).join("\n");
      html += '<div class="src"><div class="srchead">' +
              '<span class="rank">[' + s.rank + ']</span>' +
              '<span>' + esc(s.name) + '</span>' +
              '<span class="gold">' + s.gold + '골드</span>' +
              '<span class="score">' + s.score.toFixed(4) + '</span></div>' +
              '<div class="srcbody">' + esc(body) + '</div></div>';
    }
    html += '</details></div>';
    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = '<div class="card">요청 실패: ' + esc(String(err)) + '</div>';
  } finally {
    go.disabled = false;
  }
});
</script>
</body>
</html>
"""

app = Starlette(routes=[
    Route("/", index),
    Route("/ask", ask, methods=["POST"]),
])


if __name__ == "__main__":
    import uvicorn

    print("\n  http://127.0.0.1:8000  에서 열립니다. (Ctrl+C 로 종료)\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
