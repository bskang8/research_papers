#!/usr/bin/env python3
"""MongoDB 저장 기능 테스트 스크립트"""

from dotenv import load_dotenv
load_dotenv()

from paper_briefing.arxiv_fetcher import fetch_recent_papers
from paper_briefing.state import load_seen, save_papers, reset_database

print("=== MongoDB 저장 기능 테스트 ===\n")

# 1. 기존 seen 상태 확인
print("1. 기존 seen 상태 확인")
seen = load_seen()
print(f"   기존 처리 논문: {len(seen)}편\n")

# 2. 테스트용 논문 수집 (소량)
print("2. 테스트용 논문 수집 (5편)")
# fetch_recent_papers는 25편을 가져오지만 테스트를 위해 5편만 사용
papers = fetch_recent_papers()[:5]
print(f"   수집된 논문: {len(papers)}편\n")

# 3. MongoDB에 저장
print("3. MongoDB에 논문 저장")
# 테스트를 위해 간단한 점수/태그 추가
for i, p in enumerate(papers):
    p.score = 5.0 + i * 0.5
    p.tags = ["테스트"]
    p.summary = f"테스트 요약 {i+1}"

save_papers(papers)
print("")

# 4. 다시 load_seen으로 확인
print("4. 저장 후 seen 상태 확인")
seen_after = load_seen()
print(f"   현재 처리 논문: {len(seen_after)}편")
print(f"   새로 추가된 논문: {len(seen_after) - len(seen)}편\n")

# 5. 저장된 논문 샘플 조회
print("5. MongoDB에 저장된 논문 샘플 (최대 3개):")
from pymongo import MongoClient
from paper_briefing.config import MONGODB_URI, MONGODB_DB_NAME, MONGODB_COLLECTION

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB_NAME]
collection = db[MONGODB_COLLECTION]

for doc in collection.find().limit(3):
    print(f"\n   ID: {doc['id']}")
    print(f"   제목: {doc['title'][:60]}")
    print(f"   점수: {doc.get('score', 0)}")
    print(f"   태그: {doc.get('tags', [])}")
    print(f"   저자: {', '.join(doc['authors'])}")

print("\n=== 테스트 완료 ===")
