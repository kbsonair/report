# bbongtv4 프리미엄 분석 자동 수집기

`bbongtv4.com/premium` 페이지의 경기 카드(팀명, 홈/무/원정 확률, AI 픽, 결과)를 파싱해서
JSON으로 저장하고, 정적 HTML 대시보드로 렌더링합니다. GitHub Actions로 주기적으로 자동 실행됩니다.

## 파일 구성

```
scraper.py              대상 페이지를 파싱해서 data/*.json 생성
render.py                data/latest.json → index.html 생성
requirements.txt
.github/workflows/update.yml   자동 스크래핑 + 커밋 워크플로우
data/                     날짜별 JSON 스냅샷 + latest.json
index.html                자동 생성되는 대시보드 (GitHub Pages로 서빙)
test_fixture.html         오프라인 파싱 테스트용 샘플 마크업
```

## 로컬 실행

```bash
pip install -r requirements.txt

# 오늘자 페이지 수집
python scraper.py

# 특정 날짜 (URL 패턴: /premium/YYYY-MM-DD)
python scraper.py --date 2026-08-01

# 특정 카테고리만
python scraper.py --url https://bbongtv4.com/premium/soccer

# HTML 생성
python render.py
```

`index.html`을 브라우저로 열면 결과를 바로 확인할 수 있습니다.

## GitHub로 자동 업데이트 설정

1. 새 GitHub 저장소를 만들고 이 폴더 전체를 푸시합니다.

   ```bash
   git init
   git add .
   git commit -m "init"
   git branch -M main
   git remote add origin https://github.com/<사용자명>/<저장소명>.git
   git push -u origin main
   ```

2. 저장소 **Settings → Actions → General → Workflow permissions**에서
   **"Read and write permissions"**를 켜야 워크플로우가 자동으로 커밋/푸시할 수 있습니다.

3. `.github/workflows/update.yml`의 스케줄은 기본 20분 간격입니다.
   더 자주/덜 자주 돌리려면 `cron` 값을 수정하세요 (예: `*/5 * * * *` = 5분마다).
   수동 실행은 저장소의 **Actions** 탭 → **Run workflow** 버튼으로 가능합니다.

4. GitHub Pages로 대시보드를 공개하려면 **Settings → Pages**에서
   브랜치를 `main`, 폴더를 `/ (root)`로 지정하세요.
   그러면 `https://<사용자명>.github.io/<저장소명>/`에서 `index.html`이 바로 보입니다.

## 파싱 로직에 대한 참고

- 카드 상태는 `.pr-card__ai-pin`의 텍스트로 구분합니다: `AI 추천` → 예정, `적중`/`미적중` → 종료.
- 홈/무/원정 확률은 `.pr-prob-labels` 안의 각 `<span>` 텍스트에서 정규식으로 숫자와
  홈/무/원정 라벨을 함께 추출하므로, 라벨 순서가 바뀌어도(`20% 홈` vs `원정 20%`) 안전합니다.
- 스코어는 `.pr-card__teams` 컨테이너 전체 텍스트에서 `숫자 : 숫자` 패턴으로 찾습니다.
  종료 경기의 실제 마크업이 예상과 다르면 이 부분만 조정하면 됩니다.
- 카드 하나 파싱에 실패해도 전체가 죽지 않고 해당 카드만 건너뜁니다(`try/except`).
- 사이트 HTML 구조가 바뀌면 `parse_card()` 안의 CSS 선택자만 수정하면 됩니다.

## 주의

- 이 스크립트는 공개적으로 노출된 요약 정보(팀명, 확률, AI 한줄평)만 수집합니다.
  로그인 필요 콘텐츠나 유료 회원 전용 상세 분석 페이지는 다루지 않습니다.
- 사이트 측 이용약관 및 서버 부하를 고려해 과도하게 짧은 주기(예: 1분 미만)로
  스크래핑하지 않는 것을 권장합니다.
