#!/usr/bin/env python3
"""매일 1회 실행하는 메인 스크립트.

사용법:
  python run_briefing.py            # 전체 파이프라인 (fetch → triage → slack → zotero → log)
  python run_briefing.py --dry-run  # Slack/Zotero 전송 없이 결과만 출력
  python run_briefing.py --reset    # seen_papers.json 초기화 후 실행
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # .env 파일 로드


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily arXiv Paper Briefing")
    parser.add_argument("--dry-run", action="store_true", help="Slack/Zotero 전송 없이 출력만")
    parser.add_argument("--reset",   action="store_true", help="seen 상태 초기화 후 실행")
    parser.add_argument("--no-zotero", action="store_true", help="Zotero 저장 건너뜀")
    args = parser.parse_args()

    # 지연 import (load_dotenv 이후에 실행)
    from paper_briefing.arxiv_fetcher import fetch_and_select_papers
    from paper_briefing.config import MAX_PROCESS
    from paper_briefing.logger import save_log
    from paper_briefing.slack_sender import send_to_slack
    from paper_briefing.state import load_seen, save_papers, reset_database
    from paper_briefing.triage import triage_papers
    from paper_briefing.zotero_saver import save_to_zotero

    # ── 0. seen 상태 로드 ──────────────────────────────────────────────────────
    if args.reset:
        reset_database()
        print("[main] MongoDB 초기화 완료.")

    seen = load_seen()
    print(f"[main] 기존에 처리된 논문: {len(seen)}편")

    # ── 1. arXiv 수집 + 2. 중복 필터링 + 2-1. 조건 선택 ──────────────────────
    # 각 년도별 순차 실행: 학회지 우선 → 중복 확인 → 할당량 달성까지 반복
    # 할당량: 최근 6편 / 1년전 9편 / 2년전 6편 / 3~4년전 9편 (총 30편)
    print("[main] arXiv 수집 / 중복 필터링 / 논문 선택 중...")
    to_process = fetch_and_select_papers(seen)
    print(f"[main] 최종 처리 대상: {len(to_process)}편")

    if not to_process:
        print("[main] 조건을 만족하는 논문이 없습니다. 종료.")
        return

    # ── 3. AI 트리아지 ─────────────────────────────────────────────────────────
    print("[main] AI 트리아지 중...")
    triaged = triage_papers(to_process)

    # 결과 미리보기 (상위 5편)
    print("\n[미리보기] 상위 5편:")
    for p in sorted(triaged, key=lambda x: x.score, reverse=True)[:5]:
        print(f"  [{p.score:.1f}] {p.tags} {p.title[:60]}")
        print(f"       {p.summary[:80]}")
    print()

    # ── 4. 로그 저장 ───────────────────────────────────────────────────────────
    save_log(triaged)

    if args.dry_run:
        print("[main] --dry-run 모드: Slack/Zotero 전송 건너뜀.")
        save_papers(triaged)
        return

    # # ── 5. Slack 전송 ──────────────────────────────────────────────────────────
    # send_to_slack(triaged)

    # # ── 6. Zotero 저장 (선택) ──────────────────────────────────────────────────
    # if not args.no_zotero:
    #     save_to_zotero(triaged)

    # ── 7. MongoDB에 논문 저장 ────────────────────────────────────────────────
    save_papers(triaged)
    print(f"[main] 완료. 누적 처리 논문: {len(seen)}편")


if __name__ == "__main__":
    main()
