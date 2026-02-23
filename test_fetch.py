#!/usr/bin/env python3
"""fetch_recent_papers 함수 테스트 스크립트"""

from dotenv import load_dotenv
load_dotenv()

from paper_briefing.arxiv_fetcher import fetch_recent_papers

print("=== fetch_recent_papers() 테스트 ===\n")

papers = fetch_recent_papers()

print(f"\n총 수집된 논문: {len(papers)}편\n")

# 년도별 분포 확인
from collections import Counter
year_dist = Counter([p.published[:4] for p in papers])
print("년도별 분포:")
for year in sorted(year_dist.keys(), reverse=True):
    print(f"  {year}: {year_dist[year]}편")

# 샘플 논문 몇 개 출력
print("\n샘플 논문 (최대 5개):")
for i, p in enumerate(papers[:5], 1):
    print(f"\n{i}. [{p.published}] {p.title[:70]}")
    print(f"   ID: {p.id}")
    print(f"   저자: {', '.join(p.authors)}")
