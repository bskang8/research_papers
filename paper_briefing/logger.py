"""실행 로그를 logs/ 디렉터리에 저장합니다."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List

from .arxiv_fetcher import Paper


LOG_DIR = "logs"


def save_log(papers: List[Paper]) -> str:
    """papers 결과를 JSON으로 logs/YYYY-MM-DD.json 에 저장합니다."""
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(LOG_DIR, f"{today}.json")

    data = [
        {
            "id": p.id,
            "title": p.title,
            "score": p.score,
            "tags": p.tags,
            "summary": p.summary,
            "authors": p.authors,
            "published": p.published,
            "citation_count": p.citation_count,
            "arxiv_url": p.arxiv_url,
            "pdf_url": p.pdf_url,
        }
        for p in papers
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[log] {path} 에 {len(papers)}편 저장.")
    return path
