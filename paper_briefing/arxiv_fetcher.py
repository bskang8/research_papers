"""arXiv에서 최신 논문을 수집합니다."""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Set

import arxiv
import requests

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
    # 인용 정보
    citation_count: int = 0  # Semantic Scholar 기반 인용수
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


def fetch_citation_count(arxiv_id: str) -> int:
    """Semantic Scholar API로 논문의 인용수를 가져옵니다.
    
    Args:
        arxiv_id: arXiv ID (예: "2401.12345v1")
    
    Returns:
        인용수 (실패 시 0)
    """
    # arXiv ID에서 버전 제거 (예: 2401.12345v1 → 2401.12345)
    clean_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
    
    url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{clean_id}"
    params = {"fields": "citationCount"}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("citationCount", 0) or 0
        elif response.status_code == 404:
            # Semantic Scholar에 아직 인덱싱되지 않은 논문
            return 0
        else:
            return 0
    except Exception as e:
        print(f"[citation] {arxiv_id} 인용수 가져오기 실패: {e}")
        return 0


def fetch_citations_batch(papers: List[Paper], delay: float = 0.1) -> None:
    """여러 논문의 인용수를 배치로 가져와 Paper 객체에 채웁니다.
    
    Args:
        papers: Paper 객체 리스트 (in-place로 수정됨)
        delay: API 호출 간 지연 시간 (초)
    """
    for i, paper in enumerate(papers):
        paper.citation_count = fetch_citation_count(paper.id)
        if (i + 1) % 10 == 0:
            print(f"[citation] {i + 1}/{len(papers)}편 처리 중...")
        time.sleep(delay)  # API rate limit 준수


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
    
    학회지 논문 확보를 위해 각 년도당 100개씩 수집합니다.
    """
    current_year = datetime.now().year
    client = arxiv.Client(page_size=50, delay_seconds=10, num_retries=3)
    
    all_papers: List[Paper] = []
    
    # ── 최근 (올해, 최대 100개) ──
    year0_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year}0101 TO {current_year}1231]"
    year0_search = arxiv.Search(
        query=year0_query,
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year0_papers = []
    for result in client.results(year0_search):
        year0_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year0_papers)
    print(f"[fetch] 최근 ({current_year}년): {len(year0_papers)}개 수집")
    time.sleep(10)  # arXiv API rate limit 방지
    
    # ── 1년전 (최대 100개) ──
    year1_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year-1}0101 TO {current_year-1}1231]"
    year1_search = arxiv.Search(
        query=year1_query,
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year1_papers = []
    for result in client.results(year1_search):
        year1_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year1_papers)
    print(f"[fetch] 1년전 ({current_year-1}년): {len(year1_papers)}개 수집")
    time.sleep(10)  # arXiv API rate limit 방지
    
    # ── 2년전 (최대 100개) ──
    year2_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year-2}0101 TO {current_year-2}1231]"
    year2_search = arxiv.Search(
        query=year2_query,
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year2_papers = []
    for result in client.results(year2_search):
        year2_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year2_papers)
    print(f"[fetch] 2년전 ({current_year-2}년): {len(year2_papers)}개 수집")
    time.sleep(10)  # arXiv API rate limit 방지
    
    # ── 3~4년전 (최대 100개) ──
    year34_query = f"{SEARCH_QUERY} AND submittedDate:[{current_year-4}0101 TO {current_year-3}1231]"
    year34_search = arxiv.Search(
        query=year34_query,
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    
    year34_papers = []
    for result in client.results(year34_search):
        year34_papers.append(_create_paper_from_result(result))
    
    all_papers.extend(year34_papers)
    print(f"[fetch] 3~4년전 ({current_year-4}-{current_year-3}년): {len(year34_papers)}개 수집")
    
    return all_papers


def select_papers_with_criteria(papers: List[Paper], seen_ids: Set[str] = None) -> List[Paper]:
    """조건에 맞게 논문을 선택합니다.
    
    조건:
    1. 년도별 할당: 최근 6편, 1년전 9편, 2년전 6편, 3~4년전 9편 (총 30편)
    2. 중복 없음 (이미 filter_new로 처리된 papers를 받음)
    
    Args:
        papers: 후보 논문 리스트 (이미 중복 제거됨)
        seen_ids: 참조용 (사용하지 않음, 호환성 유지)
    
    Returns:
        조건을 만족하는 논문 리스트
    """
    # 선택 과정에서 사용할 ID 추적용 세트
    selected_ids = set()
    
    current_year = datetime.now().year
    
    # 년도별 논문 분류 (papers는 이미 중복 제거됨)
    year_groups = {
        'recent': [],   # 최근 (올해)
        '1year': [],    # 1년전
        '2year': [],    # 2년전
        '34year': []    # 3~4년전
    }
    
    for p in papers:
        year = int(p.published[:4])
        if year == current_year:
            year_groups['recent'].append(p)
        elif year == current_year - 1:
            year_groups['1year'].append(p)
        elif year == current_year - 2:
            year_groups['2year'].append(p)
        elif year in [current_year - 3, current_year - 4]:
            year_groups['34year'].append(p)
    
    # 각 년도별로 섞기
    for key in year_groups.keys():
        random.shuffle(year_groups[key])
    
    print(f"[select] 년도별 후보 논문 수:")
    print(f"  최근: {len(year_groups['recent'])}편 (학회지: {sum(1 for p in year_groups['recent'] if p.conference)}편)")
    print(f"  1년전: {len(year_groups['1year'])}편 (학회지: {sum(1 for p in year_groups['1year'] if p.conference)}편)")
    print(f"  2년전: {len(year_groups['2year'])}편 (학회지: {sum(1 for p in year_groups['2year'] if p.conference)}편)")
    print(f"  3~4년전: {len(year_groups['34year'])}편 (학회지: {sum(1 for p in year_groups['34year'] if p.conference)}편)")
    
    all_selected = []
    
    # ═══ 최근: 6편 선택 ═══
    print("\n[select] === 최근 논문 선택 ===")
    recent_selected = _select_papers_simple(year_groups['recent'], quota=6, year_label="최근")
    all_selected.extend(recent_selected)
    
    # ═══ 1년전: 9편 선택 ═══
    print("\n[select] === 1년전 논문 선택 ===")
    year1_selected = _select_papers_simple(year_groups['1year'], quota=9, year_label="1년전")
    all_selected.extend(year1_selected)
    
    # ═══ 2년전: 6편 선택 ═══
    print("\n[select] === 2년전 논문 선택 ===")
    year2_selected = _select_papers_simple(year_groups['2year'], quota=6, year_label="2년전")
    all_selected.extend(year2_selected)
    
    # ═══ 3~4년전: 9편 선택 ═══
    print("\n[select] === 3~4년전 논문 선택 ===")
    year34_selected = _select_papers_simple(year_groups['34year'], quota=9, year_label="3~4년전")
    all_selected.extend(year34_selected)
    
    # 최종 통계
    total_conf = sum(1 for p in all_selected if p.conference)
    print(f"\n[select] ✅ 최종 선택: 총 {len(all_selected)}편, 학회지 {total_conf}편")
    
    return all_selected


def _select_papers_simple(candidates: List[Paper], quota: int, year_label: str) -> List[Paper]:
    """할당량만큼 논문을 선택합니다 (학회지 우선).
    
    전략:
    1. 학회지 논문을 먼저 선택
    2. 부족하면 일반 논문으로 채움
    
    Args:
        candidates: 후보 논문
        quota: 선택할 개수
        year_label: 년도 레이블 (로그용)
    
    Returns:
        선택된 논문 리스트
    """
    # 학회지/일반 논문 분리
    conf_papers = [p for p in candidates if p.conference]
    non_conf_papers = [p for p in candidates if not p.conference]
    
    # 각각 섞기
    random.shuffle(conf_papers)
    random.shuffle(non_conf_papers)
    
    selected = []
    
    # 학회지부터 선택
    for p in conf_papers:
        if len(selected) >= quota:
            break
        selected.append(p)
    
    # 부족하면 일반 논문으로 채움
    for p in non_conf_papers:
        if len(selected) >= quota:
            break
        selected.append(p)
    
    conf_count = sum(1 for p in selected if p.conference)
    print(f"  선택: {len(selected)}/{quota}편 (학회지: {conf_count}편)")
    
    if len(selected) < quota:
        print(f"  ⚠️ 경고: 충분한 논문 없음 ({len(selected)}/{quota}편)")
    
    return selected


def fetch_and_select_papers(seen: Set[str]) -> List[Paper]:
    """arXiv 수집 + 중복 필터링 + 조건 선택을 통합 실행합니다.

    각 년도별로 순차적으로:
      1) 주요 학회지 우선 순위로 정렬
      2) 중복(seen) 확인하며 선택
      3) 할당량 채울 때까지 반복

    할당량: 최근 6편 / 1년전 9편 / 2년전 6편 / 3~4년전 9편 (총 30편)

    Args:
        seen: 이미 처리된 논문 ID 집합 (선택된 논문 ID가 in-place로 추가됨)

    Returns:
        조건을 만족하는 논문 리스트
    """
    current_year = datetime.now().year
    client = arxiv.Client(page_size=50, delay_seconds=10, num_retries=3)

    # (레이블, 검색 시작 연도, 검색 종료 연도, 할당량)
    year_configs = [
        ("최근",    current_year,     current_year,     6),
        ("1년전",   current_year - 1, current_year - 1, 9),
        ("2년전",   current_year - 2, current_year - 2, 6),
        ("3~4년전", current_year - 4, current_year - 3, 9),
    ]

    all_selected: List[Paper] = []

    for label, year_start, year_end, quota in year_configs:
        print(f"\n[fetch+select] === {label} ({year_start}~{year_end}년) 목표 {quota}편 ===")

        # ── 1. 해당 연도 논문 수집 ──
        query = (
            f"{SEARCH_QUERY} AND "
            f"submittedDate:[{year_start}0101 TO {year_end}1231]"
        )
        search = arxiv.Search(
            query=query,
            max_results=100,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers: List[Paper] = []
        for result in client.results(search):
            papers.append(_create_paper_from_result(result))

        conf_total = sum(1 for p in papers if p.conference)
        print(f"  수집: {len(papers)}편 (학회지: {conf_total}편)")

        # ── 2. 주요 학회지 우선 순위로 정렬 ──
        # MAJOR_CONFERENCES 리스트 인덱스가 낮을수록 우선순위 높음
        # 동일 우선순위 내에서는 제출일 최신순(arxiv 검색 결과 순) 유지
        def _conf_priority(paper: Paper) -> int:
            if paper.conference and paper.conference in MAJOR_CONFERENCES:
                return MAJOR_CONFERENCES.index(paper.conference)
            return len(MAJOR_CONFERENCES)   # 비학회지는 맨 뒤

        sorted_papers = sorted(papers, key=_conf_priority)

        # ── 3. 중복 확인하며 할당량까지 순차 선택 (반복) ──
        selected: List[Paper] = []
        skipped = 0
        for paper in sorted_papers:
            if len(selected) >= quota:
                break
            if paper.id in seen:
                skipped += 1
                continue
            selected.append(paper)
            seen.add(paper.id)   # 이후 연도 그룹에서 중복 방지

        conf_count = sum(1 for p in selected if p.conference)
        print(
            f"  선택: {len(selected)}/{quota}편 "
            f"(학회지: {conf_count}편 / 중복 건너뜀: {skipped}편)"
        )
        if len(selected) < quota:
            print(f"  ⚠️ 경고: 후보 부족으로 {len(selected)}/{quota}편만 확보")

        all_selected.extend(selected)
        
        # arXiv API rate limit 방지를 위해 다음 연도 검색 전 대기
        if label != year_configs[-1][0]:  # 마지막 연도가 아닌 경우
            print("  (다음 연도 검색 전 10초 대기...)")
            time.sleep(10)

    total_conf = sum(1 for p in all_selected if p.conference)
    print(
        f"\n[fetch+select] ✅ 최종 선택: 총 {len(all_selected)}편 "
        f"(학회지: {total_conf}편)"
    )
    
    # ── 4. 인용수 가져오기 ──
    if all_selected:
        print(f"\n[citation] Semantic Scholar에서 인용수 조회 중...")
        fetch_citations_batch(all_selected)
    
    return all_selected


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
