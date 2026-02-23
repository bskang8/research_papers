#!/usr/bin/env python3
"""논문 선택 조건 테스트 (fetch_and_select_papers 통합 검증)"""

from dotenv import load_dotenv
load_dotenv()

from collections import Counter
from datetime import datetime

from paper_briefing.arxiv_fetcher import fetch_and_select_papers

current_year = datetime.now().year

print("=== 논문 선택 조건 테스트 ===\n")

# ── 0. seen 로드 ──────────────────────────────────────────────────────────────
print("0. 기존 처리 이력 로드 (MongoDB)")
try:
    from paper_briefing.state import load_seen
    seen = load_seen()
    print(f"   처리된 논문: {len(seen)}편\n")
except Exception as e:
    print(f"   ⚠️  MongoDB 사용 불가 ({e}) → seen 없이 진행\n")
    seen = set()

# ── 1+2+2-1. 통합: arXiv 수집 + 중복 필터링 + 연도별 조건 선택 ──────────────
print("1+2+2-1. arXiv 수집 / 중복 필터링 / 연도별 조건 선택 (통합)")
selected = fetch_and_select_papers(seen)
print()

# ── 최종 검증 ────────────────────────────────────────────────────────────────
print("=" * 50)
print("=== 최종 검증 ===")
print("=" * 50)

year_dist = Counter()
year_conf_count = {"최근": 0, "1년전": 0, "2년전": 0, "3~4년전": 0}

for p in selected:
    year = int(p.published[:4])
    if year == current_year:
        label = "최근"
    elif year == current_year - 1:
        label = "1년전"
    elif year == current_year - 2:
        label = "2년전"
    elif year in [current_year - 3, current_year - 4]:
        label = "3~4년전"
    else:
        label = "기타"
    year_dist[label] += 1
    if label in year_conf_count and p.conference:
        year_conf_count[label] += 1

total_conf = sum(year_conf_count.values())

print(f"총 논문: {len(selected)}편\n")
print("년도별 분포:")
print(f"  최근    ({current_year}년)      : {year_dist['최근']}편 / 목표 6편  (학회지: {year_conf_count['최근']}편)")
print(f"  1년전   ({current_year-1}년)      : {year_dist['1년전']}편 / 목표 9편  (학회지: {year_conf_count['1년전']}편)")
print(f"  2년전   ({current_year-2}년)      : {year_dist['2년전']}편 / 목표 6편  (학회지: {year_conf_count['2년전']}편)")
print(f"  3~4년전 ({current_year-4}~{current_year-3}년) : {year_dist['3~4년전']}편 / 목표 9편  (학회지: {year_conf_count['3~4년전']}편)")
print(f"\n총 학회지 논문: {total_conf}편")

# 조건 충족 여부
print("\n=== 조건 충족 여부 ===")
checks = [
    ("총 논문 수 30편",    len(selected) == 30),
    ("최근 6편",          year_dist["최근"] == 6),
    ("1년전 9편",         year_dist["1년전"] == 9),
    ("2년전 6편",         year_dist["2년전"] == 6),
    ("3~4년전 9편",       year_dist["3~4년전"] == 9),
    ("중복 없음",         len(selected) == len({p.id for p in selected})),
]
all_pass = True
for condition, passed in checks:
    status = "✅" if passed else "❌"
    print(f"  {status} {condition}")
    if not passed:
        all_pass = False

print(f"\n{'✅ 모든 조건 통과' if all_pass else '❌ 일부 조건 미충족'}")

# 선택 논문 목록
print("\n=== 선택된 논문 목록 ===")
label_order = ["최근", "1년전", "2년전", "3~4년전"]

def get_label(p):
    year = int(p.published[:4])
    if year == current_year:        return "최근"
    if year == current_year - 1:    return "1년전"
    if year == current_year - 2:    return "2년전"
    if year in [current_year-3, current_year-4]: return "3~4년전"
    return "기타"

for label in label_order:
    group = [p for p in selected if get_label(p) == label]
    if not group:
        continue
    print(f"\n[{label}] {len(group)}편")
    for i, p in enumerate(group, 1):
        conf_tag = f"[{p.conference}] " if p.conference else "[비학회지] "
        print(f"  {i:2d}. {conf_tag}{p.title[:65]}")
        print(f"      {p.published}  {p.arxiv_url}")
