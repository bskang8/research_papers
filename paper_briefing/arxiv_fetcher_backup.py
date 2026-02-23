"""arXiv에서 최신 논문을 수집합니다."""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import arxiv

from .config import SEARCH_QUERY, MAX_FETCH

# 주요 학회 목록
MAJOR_CONFERENCES = [
    "NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI",
    "CVPR", "ICCV", "ECCV", "ACL", "EMNLP", "NAACL"
]


@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    authors: List[str]
    published: str          # "YYYY-MM-DD"
    arxiv_url: str
    pdf_url: str
    categories: List[str]
    # 학회 정보
    journal_ref: str = ""   # 예: "NeurIPS 2024"
    comment: str = ""       # 예: "Accepted at ICML 2024"
    conference: str = ""    # 추출된 학회명
    # AI 트리아지 결과 (나중에 채워짐)
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    score: float = 0.0


def extract_conference(journal_ref: str, comment: str) -> str:
    """journal_ref와 comment에서 주요 학회명을 추출합니다.
    
    Args:
        journal_ref: 예) "NeurIPS 2024", "ICML"
        comment: 예) "Accepted at CVPR 2025", "To appear in ICLR"
    
    Returns:
        추출된 학회명 (없으면 빈 문자열)
    """
    text = f"{journal_ref} {comment}".upper()
    
    for conf in MAJOR_CONFERENCES:
        # 대소문자 구분 없이 학회명 검색
        if re.search(rf"\b{conf}\b", text, re.IGNORECASE):
            return conf
    
    return ""


def filter_by_conference(papers: List[Paper], conferences: List[str] = None) -> List[Paper]:
    """특정 학회에 등록된 논문만 필터링합니다.
    
    Args:
        papers: 논문 리스트
        conferences: 필터링할 학회명 리스트 (None이면 모든 주요 학회)
    
    Returns:
        학회에 등록된 논문만 포함된 리스트
    """
    if conferences is None:
        conferences = MAJOR_CONFERENCES
    
    filtered = []
    for paper in papers:
        if paper.conference and paper.conference in conferences:
            filtered.append(paper)
    
    return filtered


def fetch_recent_papers(max_results: int = MAX_FETCH) -> List[Paper]:
    """arXiv API로 최근 논문을 풍부하게 가져옵니다.
    
    각 년도별로 충분한 수의 논문을 가져와서, 
    이후 select_papers_with_criteria()에서 조건에 맞게 선택할 수 있도록 합니다.
    """
    current_year = datetime.now().year
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)
    
    all_papers: List[Paper] = []
    
    # ── 최근 (올해, 최대 50개) ──
    year0_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year}0101 TO {current_year}1231]"
    year0_search = arxiv.Search(
        query=year0_query,
        max_results=50,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year0_papers = []
    for result in client.results(year0_search):
        year0_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year0_papers)
    print(f"[fetch] 최근 ({current_year}년): {len(year0_papers)}개 수집")
    
    # ── 1년전 (최대 50개) ──
    year1_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year-1}0101 TO {current_year-1}1231]"
    year1_search = arxiv.Search(
        query=year1_query,
        max_results=50,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year1_papers = []
    for result in client.results(year1_search):
        year1_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year1_papers)
    print(f"[fetch] 1년전 ({current_year-1}년): {len(year1_papers)}개 수집")
    
    # ── 2년전 (최대 50개) ──
    year2_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year-2}0101 TO {current_year-2}1231]"
    year2_search = arxiv.Search(
        query=year2_query,
        max_results=50,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year2_papers = []
    for result in client.results(year2_search):
        year2_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year2_papers)
    print(f"[fetch] 2년전 ({current_year-2}년): {len(year2_papers)}개 수집")
    
    # ── 3~4년전 (최대 50개) ──
    year34_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year-4}0101 TO {current_year-3}1231]"
    year34_search = arxiv.Search(
        query=year34_query,
        max_results=50,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year34_papers = []
    for result in client.results(year34_search):
        year34_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year34_papers)
    print(f"[fetch] 3~4년전 ({current_year-4}-{current_year-3}년): {len(year34_papers)}개 수집")
    
    return all_papers


def select_papers_with_criteria(papers: List[Paper]) -> List[Paper]:
    """조건에 맞게 논문을 선택합니다.
    
    조건:
    1. 년도별 할당: 최근 6편, 1년전 7편, 2년전 6편, 3~4년전 9편 (총 28편)
    2. 학회지 논문 최소 20편 이상
    
    Returns:
        조건을 만족하는 논문 리스트
    """
    current_year = datetime.now().year
    
    # 년도별 논문 분류
    year_groups = {
        current_year: [],      # 최근
        current_year - 1: [],  # 1년전
        current_year - 2: [],  # 2년전
        "3-4": []              # 3~4년전
    }
    
    for p in papers:
        year = int(p.published[:4])
        if year == current_year:
            year_groups[current_year].append(p)
        elif year == current_year - 1:
            year_groups[current_year - 1].append(p)
        elif year == current_year - 2:
            year_groups[current_year - 2].append(p)
        elif year in [current_year - 3, current_year - 4]:
            year_groups["3-4"].append(p)
    
    # 년도별 할당량
    allocations = {
        current_year: 6,
        current_year - 1: 7,
        current_year - 2: 6,
        "3-4": 9
    }
    
    selected = []
    conference_count = 0
    
    # 각 년도별로 학회지 논문 우선 선택
    for year_key, quota in allocations.items():
        year_papers = year_groups[year_key]
        
        # 학회지 논문과 일반 논문 분리
        conf_papers = [p for p in year_papers if p.conference]
        non_conf_papers = [p for p in year_papers if not p.conference]
        
        # 랜덤 섞기
        random.shuffle(conf_papers)
        random.shuffle(non_conf_papers)
        
        # 학회지 논문 우선 선택
        selected_from_year = []
        
        # 먼저 학회지 논문 선택 (할당량까지)
        for p in conf_papers[:quota]:
            selected_from_year.append(p)
        
        # 부족하면 일반 논문으로 채움
        remaining = quota - len(selected_from_year)
        if remaining > 0:
            selected_from_year.extend(non_conf_papers[:remaining])
        
        selected.extend(selected_from_year)
        conf_in_year = sum(1 for p in selected_from_year if p.conference)
        conference_count += conf_in_year
        
        year_label = f"{year_key}년" if isinstance(year_key, int) else f"{current_year-4}-{current_year-3}년"
        print(f"[select] {year_label}: {len(selected_from_year)}편 선택 (학회지: {conf_in_year}편)")
    
    print(f"[select] 총 {len(selected)}편 선택 (학회지: {conference_count}편)")
    
    # 학회지 논문이 20편 미만이면 추가 선택 필요
    if conference_count < 20:
        print(f"[select] ⚠️ 학회지 논문이 {conference_count}편으로 부족합니다 (목표 20편).")
        print(f"[select] 추가 학회지 논문 선택 시도 중...")
        
        # 이미 선택된 논문 ID
        selected_ids = {p.id for p in selected}
        
        # 선택되지 않은 학회지 논문 찾기
        remaining_conf_papers = [
            p for p in papers 
            if p.conference and p.id not in selected_ids
        ]
        
        # 필요한 만큼 추가 (일반 논문을 학회지 논문으로 교체)
        needed = 20 - conference_count
        if remaining_conf_papers and needed > 0:
            random.shuffle(remaining_conf_papers)
            additional = remaining_conf_papers[:needed]
            
            # 일반 논문 중에서 같은 수만큼 제거
            non_conf_selected = [p for p in selected if not p.conference]
            if len(non_conf_selected) >= needed:
                # 제거할 논문 선택 (랜덤)
                to_remove = random.sample(non_conf_selected, needed)
                selected = [p for p in selected if p not in to_remove]
                
                # 학회지 논문 추가
                selected.extend(additional)
                conference_count += len(additional)
                print(f"[select] {len(additional)}편의 학회지 논문 추가 (총 학회지: {conference_count}편)")
    
    return selected
    
    all_papers.extend(year34_papers)
    print(f"[fetch] 3~4년전 ({current_year-4}-{current_year-3}년): {len(year34_papers)}개 수집")
    
    return all_papers


def _create_paper_from_result(result) -> Paper:
    """arxiv.Result 객체를 Paper 객체로 변환합니다."""
    journal_ref = result.journal_ref or ""
    comment = result.comment or ""
    conference = extract_conference(journal_ref, comment)
    
    return Paper(
        id=result.get_short_id(),
        title=result.title.replace("\n", " ").strip(),
        abstract=result.summary.replace("\n", " ").strip(),
        authors=[a.name for a in result.authors[:3]],
        published=result.published.strftime("%Y-%m-%d"),
        arxiv_url=result.entry_id,
        pdf_url=result.pdf_url,
        categories=list(result.categories),
        journal_ref=journal_ref,
        comment=comment,
        conference=conference,
    )
