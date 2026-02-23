"""점수 높은 논문을 Zotero에 저장합니다 (선택 모듈)."""

from __future__ import annotations

import os
from typing import List

from .arxiv_fetcher import Paper
from .config import ZOTERO_SCORE_THRESHOLD


def save_to_zotero(papers: List[Paper]) -> int:
    """score >= ZOTERO_SCORE_THRESHOLD 논문을 Zotero에 저장합니다. 저장된 수를 반환."""
    api_key   = os.environ.get("ZOTERO_API_KEY", "")
    user_id   = os.environ.get("ZOTERO_USER_ID", "")
    coll_key  = os.environ.get("ZOTERO_COLLECTION_KEY", "")

    if not (api_key and user_id):
        print("[zotero] 자격증명이 없습니다. 건너뜀.")
        return 0

    try:
        from pyzotero import zotero
    except ImportError:
        print("[zotero] pyzotero 미설치. 건너뜀.")
        return 0

    zot = zotero.Zotero(user_id, "user", api_key)
    candidates = [p for p in papers if p.score >= ZOTERO_SCORE_THRESHOLD]
    saved = 0

    for p in candidates:
        item = zot.item_template("preprint")
        item["title"] = p.title
        item["abstractNote"] = p.abstract
        item["url"] = p.arxiv_url
        item["extra"] = f"arXiv: {p.id}\nScore: {p.score}\nTags: {', '.join(p.tags)}"
        item["creators"] = [
            {"creatorType": "author", "name": name} for name in p.authors
        ]
        if coll_key:
            item["collections"] = [coll_key]

        try:
            zot.create_items([item])
            saved += 1
        except Exception as exc:
            print(f"[zotero] {p.id} 저장 실패: {exc}")

    print(f"[zotero] {saved}편 저장 완료 (임계값: {ZOTERO_SCORE_THRESHOLD}).")
    return saved
