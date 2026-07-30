#!/usr/bin/env python3
"""
data/latest.json 을 읽어 정적 index.html 을 생성한다.
GitHub Pages로 그대로 서빙 가능 (별도 서버 불필요, fetch 없이 데이터 인라인 삽입).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "latest.json"
OUT_FILE = ROOT / "index.html"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bbongtv-render")


def load_data() -> dict:
    if not DATA_FILE.exists():
        log.error(f"데이터 파일 없음: {DATA_FILE}. scraper.py를 먼저 실행하세요.")
        raise SystemExit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>프리미엄 분석 대시보드</title>
<style>
  :root {{
    --bg: #0d0d0d;
    --card-bg: #161616;
    --border: #2a2a2a;
    --text: #eaeaea;
    --text-dim: #8a8a8a;
    --accent: #ffffff;
    --home: #4a4a4a;
    --draw: #6b6b6b;
    --away: #d9d9d9;
    --hit: #eaeaea;
    --miss: #5a5a5a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard", "Malgun Gothic", sans-serif;
    padding: 32px 20px 80px;
  }}
  .wrap {{ max-width: 980px; margin: 0 auto; }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 8px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 16px;
    margin-bottom: 24px;
  }}
  h1 {{
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 0;
  }}
  .meta {{
    font-size: 12px;
    color: var(--text-dim);
  }}
  .filters {{
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }}
  .filters button {{
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-dim);
    padding: 6px 14px;
    font-size: 12px;
    border-radius: 4px;
    cursor: pointer;
  }}
  .filters button.active {{
    color: var(--text);
    border-color: var(--text);
  }}
  .section-title {{
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 28px 0 12px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px;
  }}
  .card-head {{
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 10px;
  }}
  .teams {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 12px;
  }}
  .teams .vs {{
    font-size: 11px;
    font-weight: 400;
    color: var(--text-dim);
    padding: 0 8px;
  }}
  .score {{
    font-variant-numeric: tabular-nums;
    color: var(--text-dim);
    font-weight: 400;
  }}
  .prob-bar {{
    height: 5px;
    border-radius: 3px;
    overflow: hidden;
    display: flex;
    background: var(--border);
    margin-bottom: 6px;
  }}
  .prob-bar span {{ height: 100%; }}
  .prob-bar .home {{ background: var(--home); }}
  .prob-bar .draw {{ background: var(--draw); }}
  .prob-bar .away {{ background: var(--away); }}
  .prob-labels {{
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 12px;
  }}
  .ai-line {{
    font-size: 12px;
    color: var(--text-dim);
    margin-bottom: 4px;
  }}
  .ai-picks {{
    font-size: 13px;
    font-weight: 500;
  }}
  .badge {{
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
  }}
  .badge.hit {{ color: var(--hit); border-color: var(--hit); }}
  .badge.miss {{ color: var(--miss); }}
  .badge.pending {{ color: var(--text-dim); }}
  a.card-link {{ text-decoration: none; color: inherit; display: block; }}
  .empty {{ color: var(--text-dim); font-size: 13px; padding: 40px 0; text-align: center; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>프리미엄 분석 대시보드</h1>
    <div class="meta">수집 시각: {scraped_at} · 총 {count}건</div>
  </header>

  <div class="filters" id="filters">
    <button data-sport="all" class="active">전체</button>
    <button data-sport="soccer">축구</button>
    <button data-sport="basket">농구</button>
    <button data-sport="baseball">야구</button>
    <button data-sport="hockey">하키</button>
    <button data-sport="volley">배구</button>
  </div>

  <div class="section-title">진행 / 예정</div>
  <div class="grid" id="upcoming-grid"></div>

  <div class="section-title">종료</div>
  <div class="grid" id="finished-grid"></div>
</div>

<script>
const DATA = {data_json};

function pct(v) {{ return (v === undefined || v === null) ? 0 : v; }}

function probBarHTML(prob) {{
  const home = pct(prob.home), draw = pct(prob.draw), away = pct(prob.away);
  return `
    <div class="prob-bar">
      ${{home ? `<span class="home" style="width:${{home}}%"></span>` : ""}}
      ${{draw ? `<span class="draw" style="width:${{draw}}%"></span>` : ""}}
      ${{away ? `<span class="away" style="width:${{away}}%"></span>` : ""}}
    </div>
    <div class="prob-labels">
      <span>홈 ${{home}}%</span>
      ${{draw ? `<span>무 ${{draw}}%</span>` : ""}}
      <span>원정 ${{away}}%</span>
    </div>
  `;
}}

function cardHTML(m) {{
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const scoreHTML = hasScore
    ? `<span class="score">${{m.score1}} : ${{m.score2}}</span>`
    : `<span class="vs">VS</span>`;

  let badge = `<span class="badge pending">예정</span>`;
  if (m.status === "종료") {{
    if (m.result === "적중") badge = `<span class="badge hit">적중</span>`;
    else if (m.result === "미적중") badge = `<span class="badge miss">미적중</span>`;
    else badge = `<span class="badge">종료</span>`;
  }}

  return `
    <a class="card-link" href="${{m.url}}" target="_blank" rel="noopener">
      <div class="card">
        <div class="card-head">
          <span>${{m.league || ""}}</span>
          <span>${{m.date || ""}} ${{m.time || ""}}</span>
        </div>
        <div class="teams">
          <span>${{m.team1 || "?"}}</span>
          ${{scoreHTML}}
          <span>${{m.team2 || "?"}}</span>
        </div>
        ${{probBarHTML(m.prob || {{}})}}
        <div class="ai-line">${{m.ai_summary || ""}}</div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div class="ai-picks">${{(m.ai_picks || []).join(", ")}}</div>
          ${{badge}}
        </div>
      </div>
    </a>
  `;
}}

function render(sportFilter) {{
  const upcoming = DATA.matches.filter(m => m.status !== "종료" && (sportFilter === "all" || m.sport === sportFilter));
  const finished = DATA.matches.filter(m => m.status === "종료" && (sportFilter === "all" || m.sport === sportFilter));

  const upEl = document.getElementById("upcoming-grid");
  const finEl = document.getElementById("finished-grid");

  upEl.innerHTML = upcoming.length ? upcoming.map(cardHTML).join("") : `<div class="empty">해당 종목의 예정 경기가 없습니다.</div>`;
  finEl.innerHTML = finished.length ? finished.map(cardHTML).join("") : `<div class="empty">해당 종목의 종료 경기가 없습니다.</div>`;
}}

document.getElementById("filters").addEventListener("click", (e) => {{
  const btn = e.target.closest("button");
  if (!btn) return;
  document.querySelectorAll("#filters button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  render(btn.dataset.sport);
}});

render("all");
</script>
</body>
</html>
"""


def render(data: dict) -> str:
    scraped_at = data.get("scraped_at", "")
    try:
        dt = datetime.fromisoformat(scraped_at)
        scraped_at_display = dt.strftime("%Y-%m-%d %H:%M %Z")
    except Exception:
        scraped_at_display = scraped_at

    return PAGE_TEMPLATE.format(
        scraped_at=scraped_at_display,
        count=data.get("count", 0),
        data_json=json.dumps(data, ensure_ascii=False),
    )


def main():
    data = load_data()
    html = render(data)
    OUT_FILE.write_text(html, encoding="utf-8")
    log.info(f"HTML 생성 완료: {OUT_FILE} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
