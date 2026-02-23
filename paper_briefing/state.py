"""이미 처리한 논문을 MongoDB에 저장해 중복 전송을 막습니다."""

from __future__ import annotations

from datetime import datetime
from typing import List, Set

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from .config import MONGODB_URI, MONGODB_DB_NAME, MONGODB_COLLECTION


def _get_collection():
    """MongoDB 컬렉션을 반환합니다."""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # 연결 테스트
        client.admin.command('ping')
        db = client[MONGODB_DB_NAME]
        collection = db[MONGODB_COLLECTION]
        # ID에 인덱스 생성 (빠른 조회를 위해)
        collection.create_index("id", unique=True)
        return collection
    except ConnectionFailure as e:
        print(f"[MongoDB] 연결 실패: {e}")
        raise


def load_seen() -> Set[str]:
    """MongoDB에서 이미 처리된 논문 ID 집합을 반환합니다."""
    try:
        collection = _get_collection()
        # 모든 논문의 ID만 가져오기
        seen_ids = collection.distinct("id")
        return set(seen_ids)
    except Exception as e:
        print(f"[MongoDB] load_seen 오류: {e}")
        return set()


def save_papers(papers: List) -> None:
    """논문 전체 정보를 MongoDB에 저장합니다 (upsert).
    
    Args:
        papers: Paper 객체 리스트 (AI 트리아지 결과 포함)
    """
    if not papers:
        return
    
    try:
        collection = _get_collection()
        saved_at = datetime.now().isoformat()  # 저장 시각 기록
        
        for paper in papers:
            # Paper 객체를 딕셔너리로 변환
            paper_dict = {
                "id": paper.id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published": paper.published,
                "arxiv_url": paper.arxiv_url,
                "pdf_url": paper.pdf_url,
                "categories": paper.categories,
                "journal_ref": paper.journal_ref,
                "comment": paper.comment,
                "conference": paper.conference,
                "citation_count": paper.citation_count,  # 인용수
                "summary": paper.summary,
                "tags": paper.tags,
                "score": paper.score,
                "saved_at": saved_at,  # 저장 날짜/시각 추가
            }
            # upsert: id가 같으면 업데이트, 없으면 새로 추가
            collection.update_one(
                {"id": paper.id},
                {"$set": paper_dict},
                upsert=True
            )
        print(f"[MongoDB] {len(papers)}개 논문 저장 완료")
    except Exception as e:
        print(f"[MongoDB] save_papers 오류: {e}")
        raise


def filter_new(papers, seen: Set[str]):
    """seen에 없는 논문만 반환하고 seen을 갱신합니다."""
    new_papers = [p for p in papers if p.id not in seen]
    seen.update(p.id for p in new_papers)
    return new_papers


def reset_database() -> None:
    """MongoDB 컬렉션의 모든 데이터를 삭제합니다."""
    try:
        collection = _get_collection()
        result = collection.delete_many({})
        print(f"[MongoDB] {result.deleted_count}개 논문 삭제 완료")
    except Exception as e:
        print(f"[MongoDB] reset_database 오류: {e}")
        raise


# 하위 호환성을 위한 레거시 함수
def save_seen(ids: Set[str]) -> None:
    """레거시 호환성: save_papers()를 사용하세요."""
    print("[state] save_seen()은 deprecated. save_papers()를 사용하세요.")
