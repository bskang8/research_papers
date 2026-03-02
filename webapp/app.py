"""arXiv Paper Briefing - Web Dashboard"""

from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request
from pymongo import MongoClient, ASCENDING, DESCENDING

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

app = Flask(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "arxiv_papers")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "papers")
BOOKMARKS_COLLECTION = "bookmarks"

_client: MongoClient | None = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client[MONGODB_DB_NAME]


def get_collection():
    return get_db()[MONGODB_COLLECTION]


def get_bookmarks_col():
    col = get_db()[BOOKMARKS_COLLECTION]
    col.create_index("paper_id", unique=True)
    return col


def load_bookmarked_ids() -> set:
    """현재 북마크된 paper_id 집합 반환."""
    col = get_bookmarks_col()
    return {doc["paper_id"] for doc in col.find({}, {"paper_id": 1, "_id": 0})}


# ── 날짜 목록 (메인) ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    col = get_collection()
    pipeline = [
        {"$project": {"date": {"$substr": ["$saved_at", 0, 10]}}},
        {"$group": {"_id": "$date", "count": {"$sum": 1}}},
        {"$sort": {"_id": -1}},
    ]
    dates = list(col.aggregate(pipeline))

    stats_pipeline = [
        {"$project": {
            "date": {"$substr": ["$saved_at", 0, 10]},
            "score": 1, "conference": 1,
        }},
        {"$group": {
            "_id": "$date",
            "avg_score": {"$avg": "$score"},
            "conf_count": {"$sum": {"$cond": [{"$gt": ["$conference", ""]}, 1, 0]}},
        }},
    ]
    stats_by_date = {s["_id"]: s for s in col.aggregate(stats_pipeline)}

    for d in dates:
        d["avg_score"] = round(stats_by_date.get(d["_id"], {}).get("avg_score", 0), 2)
        d["conf_count"] = stats_by_date.get(d["_id"], {}).get("conf_count", 0)

    total_papers = col.count_documents({})
    bookmark_count = get_bookmarks_col().count_documents({})

    return render_template("index.html", dates=dates,
                           total_papers=total_papers, bookmark_count=bookmark_count)


# ── 날짜별 논문 목록 ──────────────────────────────────────────────────────────

@app.route("/date/<date_str>")
def papers_by_date(date_str: str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        abort(400)

    col = get_collection()
    all_papers = list(col.find(
        {"saved_at": {"$regex": f"^{date_str}"}}, {"_id": 0}
    ).sort("score", -1))

    if not all_papers:
        abort(404)

    tag_filter  = request.args.get("tag", "")
    conf_filter = request.args.get("conf", "")
    sort_by     = request.args.get("sort", "score")

    all_tags  = sorted(set(t for p in all_papers for t in p.get("tags", [])))
    all_confs = sorted(set(p["conference"] for p in all_papers if p.get("conference")))

    papers = all_papers
    if tag_filter:
        papers = [p for p in papers if tag_filter in p.get("tags", [])]
    if conf_filter:
        papers = [p for p in papers if p.get("conference") == conf_filter]

    sort_key_map = {
        "score":     lambda p: p.get("score", 0),
        "citation":  lambda p: p.get("citation_count", 0),
        "published": lambda p: p.get("published", ""),
    }
    papers = sorted(papers, key=sort_key_map.get(sort_by, sort_key_map["score"]), reverse=True)

    all_dates = sorted(
        {d["_id"] for d in col.aggregate([
            {"$project": {"date": {"$substr": ["$saved_at", 0, 10]}}},
            {"$group": {"_id": "$date"}},
        ])},
        reverse=True,
    )
    try:
        idx = all_dates.index(date_str)
        prev_date = all_dates[idx + 1] if idx + 1 < len(all_dates) else None
        next_date = all_dates[idx - 1] if idx > 0 else None
    except ValueError:
        prev_date = next_date = None

    bookmarked_ids = load_bookmarked_ids()
    bookmark_count = len(bookmarked_ids)

    return render_template(
        "date.html",
        papers=papers, date_str=date_str,
        all_tags=all_tags, all_confs=all_confs,
        tag_filter=tag_filter, conf_filter=conf_filter, sort_by=sort_by,
        total_count=len(all_papers), filtered_count=len(papers),
        prev_date=prev_date, next_date=next_date,
        bookmarked_ids=bookmarked_ids, bookmark_count=bookmark_count,
    )


# ── 논문 상세 ────────────────────────────────────────────────────────────────

@app.route("/paper/<path:paper_id>")
def paper_detail(paper_id: str):
    col = get_collection()
    paper = col.find_one({"id": paper_id}, {"_id": 0})
    if not paper:
        abort(404)

    saved_date = (paper.get("saved_at") or "")[:10]
    bookmarked_ids = load_bookmarked_ids()
    bookmark_count = len(bookmarked_ids)

    return render_template("paper.html", paper=paper, saved_date=saved_date,
                           bookmarked_ids=bookmarked_ids, bookmark_count=bookmark_count)


# ── 전체 검색 ────────────────────────────────────────────────────────────────

@app.route("/search")
def search():
    q           = request.args.get("q", "").strip()
    tag_filter  = request.args.get("tag", "")
    conf_filter = request.args.get("conf", "")
    sort_by     = request.args.get("sort", "score")

    col = get_collection()
    query: dict = {}
    if q:
        query["$or"] = [
            {"title":    {"$regex": q, "$options": "i"}},
            {"summary":  {"$regex": q, "$options": "i"}},
            {"abstract": {"$regex": q, "$options": "i"}},
        ]
    if tag_filter:
        query["tags"] = tag_filter
    if conf_filter:
        query["conference"] = conf_filter

    sort_map = {
        "score":     [("score", DESCENDING)],
        "citation":  [("citation_count", DESCENDING)],
        "published": [("published", DESCENDING)],
    }
    papers = list(col.find(query, {"_id": 0})
                     .sort(sort_map.get(sort_by, sort_map["score"]))
                     .limit(100))

    all_tags  = sorted(set(t for p in papers for t in p.get("tags", [])))
    all_confs = sorted(set(p["conference"] for p in papers if p.get("conference")))

    bookmarked_ids = load_bookmarked_ids()
    bookmark_count = len(bookmarked_ids)

    return render_template(
        "search.html",
        papers=papers, q=q,
        tag_filter=tag_filter, conf_filter=conf_filter, sort_by=sort_by,
        all_tags=all_tags, all_confs=all_confs,
        bookmarked_ids=bookmarked_ids, bookmark_count=bookmark_count,
    )


# ── 나중에 볼 논문 목록 ───────────────────────────────────────────────────────

@app.route("/bookmarks")
def bookmarks():
    sort_by     = request.args.get("sort", "bookmarked_at")
    tag_filter  = request.args.get("tag", "")
    conf_filter = request.args.get("conf", "")

    bm_col  = get_bookmarks_col()
    papers_col = get_collection()

    # 북마크된 항목 (북마크 날짜 포함)
    bm_docs = list(bm_col.find({}, {"_id": 0}))
    bm_map  = {d["paper_id"]: d["bookmarked_at"] for d in bm_docs}

    if not bm_map:
        bookmarked_ids = set()
        return render_template("bookmarks.html", papers=[],
                               all_tags=[], all_confs=[],
                               tag_filter=tag_filter, conf_filter=conf_filter,
                               sort_by=sort_by,
                               bookmarked_ids=bookmarked_ids, bookmark_count=0)

    papers = list(papers_col.find({"id": {"$in": list(bm_map.keys())}}, {"_id": 0}))

    # 북마크 날짜 주입
    for p in papers:
        p["bookmarked_at"] = bm_map.get(p["id"], "")

    # 필터 옵션
    all_tags  = sorted(set(t for p in papers for t in p.get("tags", [])))
    all_confs = sorted(set(p["conference"] for p in papers if p.get("conference")))

    if tag_filter:
        papers = [p for p in papers if tag_filter in p.get("tags", [])]
    if conf_filter:
        papers = [p for p in papers if p.get("conference") == conf_filter]

    sort_key_map = {
        "bookmarked_at": lambda p: p.get("bookmarked_at", ""),
        "score":         lambda p: p.get("score", 0),
        "citation":      lambda p: p.get("citation_count", 0),
        "published":     lambda p: p.get("published", ""),
    }
    papers = sorted(papers, key=sort_key_map.get(sort_by, sort_key_map["bookmarked_at"]), reverse=True)

    bookmarked_ids = set(bm_map.keys())
    bookmark_count = len(bookmarked_ids)

    return render_template(
        "bookmarks.html",
        papers=papers, all_tags=all_tags, all_confs=all_confs,
        tag_filter=tag_filter, conf_filter=conf_filter, sort_by=sort_by,
        bookmarked_ids=bookmarked_ids, bookmark_count=bookmark_count,
    )


# ── 북마크 토글 API ───────────────────────────────────────────────────────────

@app.route("/api/bookmark/<path:paper_id>", methods=["POST"])
def toggle_bookmark(paper_id: str):
    col = get_collection()
    if not col.find_one({"id": paper_id}, {"_id": 1}):
        return jsonify({"error": "paper not found"}), 404

    bm_col = get_bookmarks_col()
    existing = bm_col.find_one({"paper_id": paper_id})

    if existing:
        bm_col.delete_one({"paper_id": paper_id})
        bookmarked = False
    else:
        bm_col.insert_one({
            "paper_id":      paper_id,
            "bookmarked_at": datetime.now().isoformat(),
        })
        bookmarked = True

    total = bm_col.count_documents({})
    return jsonify({"bookmarked": bookmarked, "total": total})


if __name__ == "__main__":
    port = int(os.getenv("WEBAPP_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
