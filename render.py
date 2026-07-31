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
    --accent: #39ff88;       /* 포인트 컬러: 형광 초록 */
    --accent-dim: #1f8f52;
    --home: #4a4a4a;
    --draw: #6b6b6b;
    --away: #6b6b6b;
    --hit: #34d058;          /* 적중 = 초록 */
    --miss: #ef4444;         /* 미적중 = 빨강 */
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
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 12px;
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
    margin-top: 4px;
  }}
  .header-right {{
    text-align: right;
  }}
  .accuracy {{
    font-size: 13px;
    font-weight: 600;
  }}
  .accuracy .rate {{
    color: var(--accent);
    font-size: 18px;
  }}
  .accuracy-sub {{
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 2px;
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
    color: var(--accent);
    border-color: var(--accent);
  }}
  .section-title {{
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 28px 0 12px;
    border-left: 2px solid var(--accent);
    padding-left: 8px;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }}
  .date-group {{
    margin-bottom: 20px;
  }}
  .date-label {{
    font-size: 12px;
    font-weight: 600;
    color: var(--text-dim);
    margin: 4px 0 10px;
  }}
  .date-label .tag {{
    color: var(--accent);
    font-weight: 500;
    margin-left: 4px;
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
    color: var(--text);
    font-weight: 700;
    padding: 0 8px;
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
    font-weight: 600;
    color: var(--accent);
  }}
  .badge {{
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
    color: var(--text-dim);
    white-space: nowrap;
  }}
  .badge.hit {{ color: var(--hit); border-color: var(--hit); }}
  .badge.miss {{ color: var(--miss); border-color: var(--miss); }}
  .badge.pending {{ color: var(--text-dim); }}
  .empty {{ color: var(--text-dim); font-size: 13px; padding: 40px 0; text-align: center; grid-column: 1 / -1; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>프리미엄 분석 대시보드</h1>
      <div class="meta">수집 시각: {scraped_at} · 총 {count}건</div>
    </div>
    <div class="header-right">
      <div class="accuracy">당일 적중률 <span class="rate" id="accuracy-rate">-</span></div>
      <div class="accuracy-sub" id="accuracy-sub"></div>
    </div>
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
  <div id="upcoming-grid"></div>

  <div class="section-title">완료됨</div>
  <div id="finished-grid"></div>
</div>

<script>
const DATA = {data_json};

function pct(v) {{ return (v === undefined || v === null) ? 0 : v; }}

// 홈/무/원정 중 확률이 가장 높은 쪽을 찾는다 (동률이면 홈 > 무 > 원정 순으로 우선)
function leaderOf(prob) {{
  const home = pct(prob.home), draw = pct(prob.draw), away = pct(prob.away);
  let leader = "home", max = home;
  if (draw > max) {{ leader = "draw"; max = draw; }}
  if (away > max) {{ leader = "away"; max = away; }}
  return leader;
}}

function probBarHTML(prob, leader) {{
  const home = pct(prob.home), draw = pct(prob.draw), away = pct(prob.away);
  const activeColor = "var(--accent-dim)";
  const inactiveColor = "var(--home)";
  return `
    <div class="prob-bar">
      ${{home ? `<span style="width:${{home}}%; background:${{leader === "home" ? activeColor : inactiveColor}}"></span>` : ""}}
      ${{draw ? `<span style="width:${{draw}}%; background:${{leader === "draw" ? activeColor : inactiveColor}}"></span>` : ""}}
      ${{away ? `<span style="width:${{away}}%; background:${{leader === "away" ? activeColor : inactiveColor}}"></span>` : ""}}
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
    else badge = `<span class="badge">완료</span>`;
  }}

  const prob = m.prob || {{}};
  const leader = leaderOf(prob);
  const team1Color = leader === "home" ? "var(--accent)" : "var(--text)";
  const team2Color = leader === "away" ? "var(--accent)" : "var(--text)";

  // 클릭/이동 불가 - 순수 정보 카드로만 표시
  return `
    <div class="card">
      <div class="card-head">
        <span>${{m.league || ""}}</span>
        <span>${{m.date || ""}} ${{m.time || ""}}</span>
      </div>
      <div class="teams">
        <span style="color:${{team1Color}}">${{m.team1 || "?"}}</span>
        ${{scoreHTML}}
        <span style="color:${{team2Color}}">${{m.team2 || "?"}}</span>
      </div>
      ${{probBarHTML(prob, leader)}}
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-top: 4px;">
        <div class="ai-picks">${{(m.ai_picks || []).join(", ")}}</div>
        ${{badge}}
      </div>
    </div>
  `;
}}

function dateLabel(d) {{
  if (!d) return "";
  if (d === DATA.kst_today) return "오늘";
  if (d === DATA.kst_yesterday) return "어제";
  return d;
}}

// source_date 기준으로 그룹핑해서 날짜 라벨 + 그리드를 순서대로 만든다.
// matches는 이미 날짜 내림차순으로 정렬되어 들어온다고 가정.
function buildGroupedHTML(matches, emptyText) {{
  if (!matches.length) return `<div class="empty">${{emptyText}}</div>`;

  const groups = [];
  let currentDate = undefined;
  let currentItems = null;
  matches.forEach(m => {{
    const d = m.source_date || "";
    if (d !== currentDate) {{
      currentDate = d;
      currentItems = [];
      groups.push({{ date: d, items: currentItems }});
    }}
    currentItems.push(m);
  }});

  return groups.map(g => `
    <div class="date-group">
      <div class="date-label">${{dateLabel(g.date)}}${{g.date ? `<span class="tag">${{g.date}}</span>` : ""}}</div>
      <div class="grid">${{g.items.map(cardHTML).join("")}}</div>
    </div>
  `).join("");
}}

function updateAccuracy(sportFilter) {{
  // "당일 적중률"이므로 오늘(KST) 날짜의 완료 경기만 집계한다.
  // 옛 데이터(병합 전, source_date/kst_today 정보가 없는 경우)는 전체를 대상으로 폴백.
  const finished = DATA.matches.filter(m =>
    m.status === "종료" &&
    (sportFilter === "all" || m.sport === sportFilter) &&
    (!DATA.kst_today || !m.source_date || m.source_date === DATA.kst_today)
  );
  const hits = finished.filter(m => m.result === "적중").length;
  const misses = finished.filter(m => m.result === "미적중").length;
  const total = hits + misses;
  const rateEl = document.getElementById("accuracy-rate");
  const subEl = document.getElementById("accuracy-sub");
  if (total === 0) {{
    rateEl.textContent = "-";
    subEl.textContent = "완료된 경기 없음";
    return;
  }}
  const rate = ((hits / total) * 100).toFixed(1);
  rateEl.textContent = `${{rate}}%`;
  subEl.textContent = `${{hits}}적중 / ${{misses}}미적중 (${{total}}건)`;
}}

function render(sportFilter) {{
  const upcoming = DATA.matches.filter(m => m.status !== "종료" && (sportFilter === "all" || m.sport === sportFilter));
  const finished = DATA.matches.filter(m => m.status === "종료" && (sportFilter === "all" || m.sport === sportFilter));

  document.getElementById("upcoming-grid").innerHTML =
    buildGroupedHTML(upcoming, "해당 종목의 예정 경기가 없습니다.");
  document.getElementById("finished-grid").innerHTML =
    buildGroupedHTML(finished, "해당 종목의 완료된 경기가 없습니다.");

  updateAccuracy(sportFilter);
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