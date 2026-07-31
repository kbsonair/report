#!/usr/bin/env python3
"""
bbongtv4.com 프리미엄 분석 페이지 스크래퍼

사용법:
    python scraper.py                      # 오늘자 페이지 파싱
    python scraper.py --date 2026-07-31    # 특정 날짜 파싱
    python scraper.py --url https://bbongtv4.com/premium/soccer   # 특정 카테고리 파싱

출력:
    data/premium_<date>.json   (날짜별 스냅샷, 누적 보관)
    data/latest.json           (가장 최근 결과, HTML 렌더링에 사용)
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://bbongtv4.com"
DEFAULT_URL = f"{BASE_URL}/premium"
DATA_DIR = Path(__file__).parent / "data"
KST = ZoneInfo("Asia/Seoul")


def kst_today_str() -> str:
    """사이트가 한국 서비스이므로, 실행 서버의 시간대(예: GitHub Actions=UTC)와 무관하게
    항상 한국 시간(KST) 기준 오늘 날짜를 반환한다."""
    return datetime.now(KST).strftime("%Y-%m-%d")


def kst_yesterday_str() -> str:
    return (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bbongtv-scraper")


def fetch_html(url: str, timeout: int = 15) -> str:
    """대상 URL의 HTML을 가져온다."""
    log.info(f"요청: {url}")
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"},
        timeout=timeout,
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    log.info(f"응답 수신: status={resp.status_code}, bytes={len(resp.content)}")
    return resp.text


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def parse_prob_labels(card) -> dict:
    """
    <div class="pr-prob-labels">
        <span><b>20%</b> 홈</span>
        <span><b>5%</b> 무</span>
        <span>원정 <b>75%</b></span>
    </div>
    형태를 {"home": 20, "draw": 5, "away": 75} 로 변환.
    라벨 문구(홈/무/원정)와 숫자 위치가 span마다 달라질 수 있어 텍스트 전체에서 추출한다.
    """
    label_map = {"홈": "home", "무": "draw", "원정": "away"}
    prob = {}
    labels_container = card.select_one(".pr-prob-labels")
    if not labels_container:
        return prob

    for span in labels_container.select("span"):
        txt = _text(span)  # 예: "20% 홈" 또는 "원정 75%"
        num_match = re.search(r"(\d+(?:\.\d+)?)\s*%", txt)
        if not num_match:
            continue
        value = float(num_match.group(1))
        key = None
        for kr, en in label_map.items():
            if kr in txt:
                key = en
                break
        if key:
            prob[key] = value
    return prob


def parse_score(teams_container) -> tuple:
    """
    종료된 경기의 경우 팀 사이에 스코어(예: '3 : 2')가 표시된다.
    팀명 span과 섞여 있을 수 있어 컨테이너 전체 텍스트에서 정규식으로 추출한다.
    스코어가 없으면 (None, None) 반환.
    """
    txt = _text(teams_container)
    m = re.search(r"(\d+)\s*:\s*(\d+)", txt)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def parse_card(card, base_url: str) -> dict:
    """
    개별 <a class="pr-card"> 요소를 파싱해서 dict로 반환.
    사이트 구조가 바뀌어도 최대한 죽지 않도록 각 필드는 개별적으로 방어 처리한다.
    """
    href = card.get("href", "")
    url = urljoin(base_url, href)

    # /premium/<sport>/<id> 형태에서 sport, id 추출
    parts = [p for p in href.strip("/").split("/") if p]
    sport = parts[1] if len(parts) >= 2 else None
    match_id = parts[2] if len(parts) >= 3 else (parts[-1] if parts else None)

    league = _text(card.select_one(".pr-card__league-name"))
    date_str = _text(card.select_one(".pr-card__date"))
    time_str = _text(card.select_one(".pr-card__time"))

    teams_container = card.select_one(".pr-card__teams")
    team_spans = card.select(".pr-card__team span")
    # 팀 로고 div 안에도 span이 있을 수 있으므로, 로고 div 밖의 텍스트만 있는 span만 취함
    team_names = [s.get_text(strip=True) for s in team_spans if s.get_text(strip=True)]
    team1 = team_names[0] if len(team_names) >= 1 else None
    team2 = team_names[1] if len(team_names) >= 2 else None

    score1, score2 = parse_score(teams_container) if teams_container else (None, None)
    has_score = score1 is not None and score2 is not None

    # 상태 판단: pin 요소(.pr-card__ai-pin)의 클래스/문구가 사이트마다 다를 수 있어
    # 신뢰하지 않고, 1) 카드 전체 텍스트에서 "적중"/"미적중" 문구 검색, 2) 스코어 존재 여부로 판단.
    # "미적중"이 "적중"을 포함하는 문자열이므로 반드시 먼저 검사한다.
    full_text = card.get_text(" ", strip=True)
    if "미적중" in full_text:
        status, result = "종료", "미적중"
    elif "적중" in full_text:
        status, result = "종료", "적중"
    elif has_score:
        # 결과 문구는 못 찾았지만 스코어가 있으면 최소한 '종료'로는 분류
        status, result = "종료", None
    else:
        status, result = "예정", None

    prob = parse_prob_labels(card)

    ai_summary = _text(card.select_one(".pr-card__ai-text"))
    ai_picks = [
        p.get_text(strip=True)
        for p in card.select(".pr-card__ai-pick")
        if p.get_text(strip=True)
    ]

    aria_label = card.get("aria-label", "")

    return {
        "id": match_id,
        "url": url,
        "sport": sport,
        "league": league or None,
        "date": date_str or None,
        "time": time_str or None,
        "status": status,
        "result": result,
        "team1": team1,
        "team2": team2,
        "score1": score1,
        "score2": score2,
        "prob": prob,
        "ai_summary": ai_summary or None,
        "ai_picks": ai_picks,
        "aria_label": aria_label or None,
    }


def parse_page(html: str, base_url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a.pr-card")
    log.info(f"카드 {len(cards)}개 발견")

    results = []
    for card in cards:
        try:
            item = parse_card(card, base_url)
            results.append(item)
        except Exception as e:
            log.warning(f"카드 파싱 실패, 건너뜀: {e}")

    parsed_ok = sum(1 for r in results if r["team1"] and r["team2"])
    log.info(f"파싱 완료: {parsed_ok}/{len(results)}건 팀명 인식 성공")
    return results


def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"저장 완료: {path}")


def main():
    parser = argparse.ArgumentParser(description="bbongtv4.com 프리미엄 분석 스크래퍼")
    parser.add_argument("--date", help="YYYY-MM-DD 형식. 미지정 시 오늘(전체) 페이지")
    parser.add_argument("--url", help="직접 URL 지정 (--date보다 우선)")
    parser.add_argument(
        "--out-name",
        help="data/ 폴더에 저장할 파일명(확장자 제외). 미지정 시 날짜로 자동 생성",
    )
    parser.add_argument(
        "--skip-latest",
        action="store_true",
        help="data/latest.json은 건드리지 않고 날짜별 스냅샷 파일만 저장 "
        "(여러 날짜를 순차 스크래핑한 뒤 merge_history.py로 합칠 때 사용)",
    )
    args = parser.parse_args()

    if args.url:
        target_url = args.url
    elif args.date:
        target_url = f"{BASE_URL}/premium/{args.date}"
    else:
        target_url = DEFAULT_URL

    try:
        html = fetch_html(target_url)
    except requests.RequestException as e:
        log.error(f"페이지 요청 실패: {e}")
        sys.exit(1)

    matches = parse_page(html, BASE_URL)

    # 이 스냅샷이 어느 날짜(KST 기준) 데이터인지 명시적으로 태그.
    # --date가 없으면(기본 /premium 페이지) 사이트의 "오늘"이므로 KST 오늘 날짜를 사용.
    snapshot_date = args.date or kst_today_str()
    for m in matches:
        m["source_date"] = snapshot_date

    now = datetime.now(timezone.utc).astimezone()
    payload = {
        "source_url": target_url,
        "source_date": snapshot_date,
        "scraped_at": now.isoformat(),
        "count": len(matches),
        "matches": matches,
    }

    out_name = args.out_name or snapshot_date
    save_json(payload, DATA_DIR / f"premium_{out_name}.json")

    if not args.skip_latest:
        save_json(payload, DATA_DIR / "latest.json")

    if not matches:
        log.warning(
            "매치가 0건입니다. 사이트 구조가 바뀌었거나 접속이 차단되었을 수 있습니다."
        )


if __name__ == "__main__":
    main()