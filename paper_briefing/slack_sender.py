"""Slack Incoming Webhook으로 논문 브리핑을 전송합니다."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import List

import requests

from .arxiv_fetcher import Paper


def _score_bar(score: float) -> str:
    filled = round(score)
    return "★" * filled + "☆" * (5 - filled)


def _build_blocks(papers: List[Paper]) -> list:
    today = date.today().strftime("%Y-%m-%d")
    blocks: list = []

    # 헤더
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": f"Daily Paper Briefing  {today}  ({len(papers)} papers)"},
    })

    # 태그별 트렌드 요약
    from collections import Counter
    tag_counts: Counter = Counter()
    for p in papers:
        tag_counts.update(p.tags)
    trend_lines = "\n".join(f"• *{tag}*: {cnt}편" for tag, cnt in tag_counts.most_common())
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*오늘의 트렌드*\n{trend_lines or '(없음)'}"},
    })
    blocks.append({"type": "divider"})

    # 논문 카드 (score 내림차순)
    for p in sorted(papers, key=lambda x: x.score, reverse=True):
        tag_str = ", ".join(p.tags) if p.tags else "기타"
        score_str = _score_bar(p.score)
        header_text = f"{score_str}  [{tag_str}]  {p.title}"
        links = f"<{p.arxiv_url}|arXiv>  |  <{p.pdf_url}|PDF>"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{header_text}*\n{links}"},
        })
        authors_str = ", ".join(p.authors)
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"{p.summary}\n_{authors_str} | {p.published}_"}],
        })
        blocks.append({"type": "divider"})

    return blocks


def send_to_slack(papers: List[Paper]) -> bool:
    """Slack으로 논문 브리핑을 전송합니다. 성공 시 True."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print("[slack] SLACK_WEBHOOK_URL이 설정되지 않았습니다. 전송 건너뜀.")
        return False

    blocks = _build_blocks(papers)

    # Slack blocks 하나당 최대 50개 제한 → 분할 전송
    BLOCK_LIMIT = 50
    first = True
    for start in range(0, len(blocks), BLOCK_LIMIT):
        chunk = blocks[start : start + BLOCK_LIMIT]
        payload = {
            "text": "Daily Paper Briefing",
            "blocks": chunk,
        }
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code != 200:
            print(f"[slack] 전송 실패: {resp.status_code} {resp.text}")
            return False
        first = False

    print(f"[slack] {len(papers)}편 전송 완료.")
    return True
