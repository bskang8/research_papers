"""
NotebookLM 파일 다운로드 자동화 스크립트 (Playwright 기반)

사용법:
  python clawing_test.py              # 첫 실행: 브라우저 창에서 Google 로그인
  python clawing_test.py --headless   # 저장된 세션으로 headless 실행 (두 번째 실행부터)

동작 순서:
  1. Chromium 브라우저를 열어 Google 로그인 대기
  2. 로그인 완료 후 NotebookLM 노트북으로 이동
  3. Audio Overview (M4A) 다운로드
  4. PDF 소스 파일 다운로드
  5. 인증 상태를 파일로 저장 (다음 실행 시 재사용)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
NOTEBOOK_URL = (
    "https://notebooklm.google.com/notebook/d5d61e4b-6e87-4eab-bd4c-b5a8d58f8cc3"
)
DOWNLOAD_DIR = Path("./notebooklm_downloads")
AUTH_FILE = Path("./notebooklm_auth.json")

LOGIN_TIMEOUT_SEC = 300   # 로그인 대기 최대 시간 (초)
ACTION_TIMEOUT_MS = 30_000  # UI 동작 타임아웃 (ms)


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────
def log(msg: str):
    print(f"[+] {msg}", flush=True)


def warn(msg: str):
    print(f"[!] {msg}", flush=True)


# ─────────────────────────────────────────────
# 로그인 확인
# ─────────────────────────────────────────────
def wait_for_login(page):
    """사용자가 Google 로그인을 완료할 때까지 대기."""
    log("Google 로그인을 완료해 주세요... (브라우저 창을 확인하세요)")
    deadline = time.time() + LOGIN_TIMEOUT_SEC
    while time.time() < deadline:
        url = page.url
        if "notebooklm.google.com" in url and "accounts.google.com" not in url:
            log("로그인 감지됨!")
            return True
        time.sleep(2)
    warn(f"{LOGIN_TIMEOUT_SEC}초 내에 로그인이 완료되지 않았습니다.")
    return False


def is_logged_in(page) -> bool:
    return (
        "notebooklm.google.com" in page.url
        and "accounts.google.com" not in page.url
    )


# ─────────────────────────────────────────────
# Audio Overview (M4A) 다운로드
# ─────────────────────────────────────────────
def download_audio_overview(page, download_dir: Path) -> list[Path]:
    """Audio Overview 패널을 찾아 M4A 파일을 다운로드한다."""
    log("Audio Overview 다운로드 시도 중...")
    downloaded = []

    # 페이지가 완전히 로드될 때까지 대기
    page.wait_for_load_state("networkidle", timeout=ACTION_TIMEOUT_MS)

    # ── 전략 1: 네트워크 요청에서 오디오 URL 가로채기 ──────────────────────
    audio_urls: list[str] = []

    def intercept_audio(response):
        url = response.url
        if any(ext in url for ext in [".m4a", ".mp3", ".ogg", ".aac", "audio"]):
            content_type = response.headers.get("content-type", "")
            if "audio" in content_type or any(
                ext in url for ext in [".m4a", ".mp3", ".ogg"]
            ):
                if url not in audio_urls:
                    audio_urls.append(url)
                    log(f"오디오 URL 감지: {url[:80]}...")

    page.on("response", intercept_audio)

    # ── 전략 2: UI에서 Audio Overview 다운로드 버튼 클릭 ────────────────────
    # NotebookLM 오디오 패널 셀렉터 (여러 후보를 시도)
    audio_panel_selectors = [
        "button[aria-label*='audio' i]",
        "button[aria-label*='오디오' ]",
        "[data-testid*='audio']",
        "button:has-text('Audio overview')",
        "button:has-text('오디오 개요')",
        ".audio-overview",
        "[class*='audio']",
    ]

    for sel in audio_panel_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                log(f"오디오 패널 발견: {sel}")
                el.click()
                page.wait_for_timeout(2000)
                break
        except Exception:
            continue

    # 다운로드 버튼 셀렉터
    download_btn_selectors = [
        "button[aria-label*='download' i]",
        "button[aria-label*='다운로드']",
        "button[title*='download' i]",
        "[data-testid*='download']",
        "button:has-text('Download')",
        "button:has-text('다운로드')",
        "a[download]",
        "a[href*='.m4a']",
        "a[href*='.mp3']",
    ]

    for sel in download_btn_selectors:
        try:
            btns = page.locator(sel)
            count = btns.count()
            for i in range(count):
                btn = btns.nth(i)
                if btn.is_visible(timeout=2000):
                    log(f"다운로드 버튼 발견: {sel}")
                    with page.expect_download(timeout=60_000) as dl_info:
                        btn.click()
                    dl = dl_info.value
                    dest = download_dir / (dl.suggested_filename or "audio_overview.m4a")
                    dl.save_as(dest)
                    log(f"오디오 저장: {dest}")
                    downloaded.append(dest)
        except Exception:
            continue

    # ── 전략 3: 가로챈 오디오 URL에서 직접 다운로드 ─────────────────────────
    if not downloaded and audio_urls:
        import requests  # type: ignore

        log(f"가로챈 오디오 URL {len(audio_urls)}개에서 직접 다운로드 시도...")
        cookies = {
            c["name"]: c["value"] for c in page.context.cookies()
        }
        headers = {
            "User-Agent": page.evaluate("navigator.userAgent"),
            "Referer": NOTEBOOK_URL,
        }
        for idx, url in enumerate(audio_urls):
            try:
                resp = requests.get(url, cookies=cookies, headers=headers, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 1024:
                    dest = download_dir / f"audio_overview_{idx + 1}.m4a"
                    dest.write_bytes(resp.content)
                    log(f"오디오 저장: {dest} ({len(resp.content):,} bytes)")
                    downloaded.append(dest)
            except Exception as e:
                warn(f"직접 다운로드 실패 ({url[:60]}...): {e}")

    page.remove_listener("response", intercept_audio)

    if not downloaded:
        warn("Audio Overview를 찾지 못했습니다.")
        warn("  NotebookLM에서 Audio Overview가 생성되어 있는지 확인하세요.")
        _take_screenshot(page, "audio_overview_debug.png")

    return downloaded


# ─────────────────────────────────────────────
# PDF 소스 다운로드
# ─────────────────────────────────────────────
def download_pdf_sources(page, download_dir: Path) -> list[Path]:
    """소스 패널에서 PDF 파일을 다운로드한다."""
    log("PDF 소스 다운로드 시도 중...")
    downloaded = []

    page.wait_for_load_state("networkidle", timeout=ACTION_TIMEOUT_MS)

    # ── 전략 1: 네트워크에서 PDF URL 가로채기 ───────────────────────────────
    pdf_urls: list[str] = []

    def intercept_pdf(response):
        url = response.url
        content_type = response.headers.get("content-type", "")
        if ".pdf" in url or "application/pdf" in content_type:
            if url not in pdf_urls:
                pdf_urls.append(url)
                log(f"PDF URL 감지: {url[:80]}...")

    page.on("response", intercept_pdf)

    # ── 전략 2: 소스 목록에서 각 소스의 컨텍스트 메뉴 열기 ────────────────────
    source_item_selectors = [
        "[data-testid='source-item']",
        "[class*='source-item']",
        "[class*='SourceItem']",
        "li[class*='source']",
        ".source-card",
        "[aria-label*='source' i]",
    ]

    for sel in source_item_selectors:
        try:
            items = page.locator(sel)
            count = items.count()
            if count > 0:
                log(f"소스 항목 {count}개 발견: {sel}")
                for i in range(count):
                    item = items.nth(i)
                    if not item.is_visible(timeout=2000):
                        continue
                    # 마우스 오버 → 더보기 메뉴 → 다운로드
                    item.hover()
                    page.wait_for_timeout(500)
                    # "..." 버튼 또는 옵션 버튼 탐색
                    for menu_sel in [
                        "button[aria-label*='more' i]",
                        "button[aria-label*='option' i]",
                        "button[aria-label*='더보기']",
                        "button[aria-haspopup='menu']",
                        "button:has-text('...')",
                    ]:
                        try:
                            menu_btn = item.locator(menu_sel).first
                            if menu_btn.is_visible(timeout=1500):
                                menu_btn.click()
                                page.wait_for_timeout(500)
                                # 다운로드 메뉴 항목 클릭
                                for dl_sel in [
                                    "menuitem:has-text('Download')",
                                    "menuitem:has-text('다운로드')",
                                    "[role='menuitem']:has-text('Download')",
                                    "[role='menuitem']:has-text('다운로드')",
                                    "button:has-text('Download')",
                                ]:
                                    try:
                                        dl_item = page.locator(dl_sel).first
                                        if dl_item.is_visible(timeout=1500):
                                            with page.expect_download(timeout=60_000) as dl_info:
                                                dl_item.click()
                                            dl = dl_info.value
                                            dest = download_dir / (
                                                dl.suggested_filename or f"source_{i+1}.pdf"
                                            )
                                            dl.save_as(dest)
                                            log(f"PDF 저장: {dest}")
                                            downloaded.append(dest)
                                            break
                                    except Exception:
                                        continue
                                break
                        except Exception:
                            continue
                break
        except Exception:
            continue

    # ── 전략 3: 가로챈 PDF URL에서 직접 다운로드 ────────────────────────────
    if not downloaded and pdf_urls:
        import requests  # type: ignore

        log(f"가로챈 PDF URL {len(pdf_urls)}개에서 직접 다운로드 시도...")
        cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        headers = {
            "User-Agent": page.evaluate("navigator.userAgent"),
            "Referer": NOTEBOOK_URL,
        }
        for idx, url in enumerate(pdf_urls):
            try:
                resp = requests.get(url, cookies=cookies, headers=headers, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 1024:
                    dest = download_dir / f"source_{idx + 1}.pdf"
                    dest.write_bytes(resp.content)
                    log(f"PDF 저장: {dest} ({len(resp.content):,} bytes)")
                    downloaded.append(dest)
            except Exception as e:
                warn(f"직접 다운로드 실패: {e}")

    page.remove_listener("response", intercept_pdf)

    if not downloaded:
        warn("PDF 소스를 찾지 못했습니다.")
        _take_screenshot(page, "pdf_sources_debug.png")

    return downloaded


# ─────────────────────────────────────────────
# 디버그용 스크린샷
# ─────────────────────────────────────────────
def _take_screenshot(page, filename: str):
    try:
        path = DOWNLOAD_DIR / filename
        page.screenshot(path=str(path), full_page=True)
        log(f"디버그 스크린샷 저장: {path}")
    except Exception:
        pass


# ─────────────────────────────────────────────
# 메인 플로우
# ─────────────────────────────────────────────
def run(headless: bool):
    DOWNLOAD_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        # 브라우저 컨텍스트 설정
        launch_opts = dict(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        # 저장된 인증 상태 로드
        context_opts = dict(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
        )
        if AUTH_FILE.exists():
            log(f"저장된 인증 상태 로드: {AUTH_FILE}")
            context_opts["storage_state"] = str(AUTH_FILE)

        browser = p.chromium.launch(**launch_opts)
        context = browser.new_context(**context_opts)
        page = context.new_page()

        try:
            # ── 1. 노트북 페이지로 이동 ────────────────────────────────────
            log(f"페이지 이동: {NOTEBOOK_URL}")
            page.goto(NOTEBOOK_URL, timeout=30_000)
            page.wait_for_timeout(2000)

            # ── 2. 로그인 처리 ─────────────────────────────────────────────
            if not is_logged_in(page):
                if headless:
                    warn("저장된 세션이 만료됐습니다. --headless 없이 다시 실행하여 재로그인하세요.")
                    return
                if not wait_for_login(page):
                    warn("로그인 타임아웃. 스크립트를 종료합니다.")
                    return

            log(f"노트북 접근 성공: {page.url}")

            # ── 3. 인증 상태 저장 (다음 실행에서 재사용) ──────────────────
            context.storage_state(path=str(AUTH_FILE))
            log(f"인증 상태 저장: {AUTH_FILE}")

            # 페이지가 완전히 렌더링될 때까지 대기
            page.wait_for_load_state("networkidle", timeout=30_000)
            page.wait_for_timeout(3000)

            # ── 4. 파일 다운로드 ───────────────────────────────────────────
            audio_files = download_audio_overview(page, DOWNLOAD_DIR)
            pdf_files = download_pdf_sources(page, DOWNLOAD_DIR)

            # ── 5. 결과 요약 ───────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("다운로드 결과")
            print("=" * 60)

            all_files = audio_files + pdf_files
            if all_files:
                for f in all_files:
                    size = f.stat().st_size if f.exists() else 0
                    print(f"  {f.name}  ({size:,} bytes)")
                print(f"\n저장 위치: {DOWNLOAD_DIR.resolve()}")
            else:
                print("  다운로드된 파일이 없습니다.")
                print()
                print("  가능한 원인:")
                print("  1. Audio Overview가 아직 생성되지 않음")
                print("  2. NotebookLM UI가 업데이트되어 셀렉터가 변경됨")
                print("  3. 노트북에 PDF 소스가 없음")
                print()
                print(f"  디버그 스크린샷 확인: {DOWNLOAD_DIR}/")
                _take_screenshot(page, "final_state.png")

        except PlaywrightTimeoutError as e:
            warn(f"타임아웃 오류: {e}")
            _take_screenshot(page, "timeout_error.png")
        except KeyboardInterrupt:
            warn("사용자가 중단했습니다.")
        finally:
            context.close()
            browser.close()


# ─────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NotebookLM 파일 다운로드 자동화")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="headless 모드로 실행 (저장된 세션 필요)",
    )
    args = parser.parse_args()

    if args.headless and not AUTH_FILE.exists():
        print("오류: --headless 옵션은 저장된 인증 상태 파일이 필요합니다.")
        print("먼저 'python clawing_test.py' (headed 모드)로 로그인하세요.")
        sys.exit(1)

    log(f"Python: {sys.version.split()[0]}")
    log(f"다운로드 디렉토리: {DOWNLOAD_DIR.resolve()}")
    log(f"모드: {'headless' if args.headless else 'headed (브라우저 창 표시)'}")
    print()

    run(headless=args.headless)


if __name__ == "__main__":
    main()
