#!/usr/bin/env python3
"""
data/premium_<date>.json 스냅샷들 중 최근 N일치를 합쳐 data/latest.json을 만든다.

각 날짜의 스냅샷 파일은 scraper.py가 실행될 때마다 계속 남아있으므로(덮어쓰지 않음),
전체 히스토리는 항상 data/ 폴더에 보존된다. 이 스크립트는 그중 대시보드에 보여줄
"최근 N일" 구간만 골라 latest.json으로 합쳐주는 역할만 한다.

사용법:
    python merge_history.py            # 기본 최근 2일(오늘+어제)
    python merge_history.py --days 3   # 최근 3일
"""

import argparse
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_DIR = Path(__file__).parent / "data"
OUT_FILE = DATA_DIR / "latest.json"
KST = ZoneInfo("Asia/Seoul")

SNAPSHOT_RE = re.compile(r"^premium_(\d{4}-\d{2}-\d{2})\.json$")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bbongtv-merge")


def find_snapshot_files() -> dict:
    """data/premium_YYYY-MM-DD.json 파일들을 {날짜문자열: Path} 형태로 반환."""
    found = {}
    if not DATA_DIR.exists():
        return found
    for f in DATA_DIR.glob("premium_*.json"):
        m = SNAPSHOT_RE.match(f.name)
        if m:
            found[m.group(1)] = f
    return found


def load_matches(path: Path, fallback_date: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    matches = payload.get("matches", [])
    # 구버전 스냅샷(파싱 당시 source_date 필드가 없던 경우)을 대비한 안전장치
    for m in matches:
        m.setdefault("source_date", payload.get("source_date", fallback_date))
    return matches


def main():
    parser = argparse.ArgumentParser(description="날짜별 스냅샷을 합쳐 latest.json 생성")
    parser.add_argument(
        "--days", type=int, default=2, help="오늘 포함 최근 며칠치를 합칠지 (기본 2 = 오늘+어제)"
    )
    args = parser.parse_args()

    today_kst = datetime.now(KST).date()
    target_dates = [
        (today_kst - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(args.days)
    ]

    available = find_snapshot_files()
    log.info(f"보유 스냅샷: {sorted(available.keys())}")
    log.info(f"합칠 대상 날짜({args.days}일): {target_dates}")

    included_dates = [d for d in target_dates if d in available]
    for d in included_dates:
        log.info(f"{d} 스냅샷 발견")
    for d in target_dates:
        if d not in available:
            log.info(f"{d} 스냅샷 없음, 건너뜀")

    # id 기준 중복 제거 (동일 id가 여러 스냅샷에 걸쳐 있으면 더 최근 날짜 것을 우선하도록
    # 오래된 날짜 -> 최신 날짜 순으로 넣어서 최신이 덮어쓰게 함)
    dedup = {}
    for d in sorted(included_dates):
        matches = load_matches(available[d], d)
        log.info(f"{d}: {len(matches)}건 로드")
        for m in matches:
            key = m.get("id") or f"{d}:{m.get('team1')}:{m.get('team2')}:{m.get('time')}"
            dedup[key] = m
    all_matches = list(dedup.values())

    # 정렬: 날짜는 최신이 먼저, 같은 날짜 안에서는 시간 오름차순.
    # 파이썬 sort는 안정 정렬이므로 "시간 오름차순 정렬 -> 날짜 내림차순 정렬" 순으로 두 번 적용하면
    # 날짜 그룹 내부의 시간 순서가 그대로 유지된다.
    all_matches.sort(key=lambda m: m.get("time") or "")
    all_matches.sort(key=lambda m: m.get("source_date") or "", reverse=True)

    now = datetime.now(timezone.utc).astimezone()
    payload = {
        "scraped_at": now.isoformat(),
        "kst_today": today_kst.strftime("%Y-%m-%d"),
        "kst_yesterday": (today_kst - timedelta(days=1)).strftime("%Y-%m-%d"),
        "included_dates": included_dates,
        "count": len(all_matches),
        "matches": all_matches,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log.info(f"병합 완료: {len(all_matches)}건 -> {OUT_FILE}")
    if not included_dates:
        log.warning("합칠 스냅샷이 하나도 없습니다. scraper.py를 먼저 실행하세요.")


if __name__ == "__main__":
    main()