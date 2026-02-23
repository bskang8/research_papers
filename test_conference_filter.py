#!/usr/bin/env python3
"""학회 정보 추출 및 필터링 테스트"""

from dotenv import load_dotenv
load_dotenv()

from paper_briefing.arxiv_fetcher import fetch_recent_papers, filter_by_conference

print("=== 학회 정보 추출 테스트 ===\n")

# 1. 논문 수집
print("1. 논문 수집 중...")
papers = fetch_recent_papers()
print(f"   총 {len(papers)}편 수집\n")

# 2. 학회 정보 확인
print("2. 학회 정보가 있는 논문:")
conference_papers = [p for p in papers if p.conference]
print(f"   학회 정보 있음: {len(conference_papers)}편\n")

if conference_papers:
    print("   샘플 논문 (학회 정보 있음):")
    for p in conference_papers[:5]:
        print(f"   - [{p.conference}] {p.title[:50]}")
        if p.journal_ref:
            print(f"     journal_ref: {p.journal_ref}")
        if p.comment:
            print(f"     comment: {p.comment[:80]}")
        print()

# 3. 특정 학회 필터링 예시
print("\n3. 특정 학회 필터링 예시:")
target_conferences = ["NeurIPS", "ICML", "CVPR"]
filtered = filter_by_conference(papers, target_conferences)
print(f"   {', '.join(target_conferences)} 논문: {len(filtered)}편")

if filtered:
    for p in filtered[:3]:
        print(f"   - [{p.conference}] {p.title[:60]}")

# 4. 학회별 분포
print("\n4. 학회별 논문 분포:")
from collections import Counter
conf_dist = Counter([p.conference for p in papers if p.conference])
for conf, count in conf_dist.most_common():
    print(f"   {conf}: {count}편")

if not conference_papers:
    print("\n⚠️  학회 정보가 있는 논문이 없습니다.")
    print("   이는 정상이며, arXiv의 많은 논문들은 학회 정보가 없습니다.")
    print("   프리프린트(preprint)로만 공개되거나, 아직 학회에 제출되지 않은 논문일 수 있습니다.")
