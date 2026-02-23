# arXiv Paper Briefing System

매일 arXiv에서 로봇/AI 논문을 자동으로 수집하고, AI로 분석하여 MongoDB에 저장하는 시스템입니다.

## 📋 주요 기능

- **자동 논문 수집**: arXiv API로 조건에 맞는 논문 검색
- **AI 트리아지**: OpenAI/Gemini API로 논문 요약, 태그 분류, 점수 평가
- **인용수 추적**: Semantic Scholar API로 인용수 자동 수집
- **중복 방지**: MongoDB 기반 논문 ID 추적
- **데이터 저장**: MongoDB + JSON 로그 파일

---

## 🚀 빠른 시작

### 1. 환경 설정

#### 1-1. 프로젝트 클론 및 가상환경 생성

```bash
cd /home/bskang/papers
conda create -n Papers python=3.13
conda activate Papers
```

#### 1-2. 패키지 설치

```bash
pip install -r requirements.txt
```

**requirements.txt 내용:**
```
arxiv>=2.1.0
openai>=1.30.0
google-genai>=0.3.0
python-dotenv>=1.0.0
requests>=2.31.0
pyzotero>=1.5.0
pymongo>=4.6.0
```

### 2. MongoDB Docker 컨테이너 생성

#### 2-1. Docker 컨테이너 실행

```bash
docker run -d \
  --name arxiv-mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo:latest
```

**옵션 설명:**
- `-d`: 백그라운드 실행
- `--name arxiv-mongodb`: 컨테이너 이름
- `-p 27017:27017`: 호스트 27017 포트를 컨테이너 27017에 매핑 (외부 접속 가능)
- `-v mongodb_data:/data/db`: 데이터 영구 저장 (볼륨)
- `mongo:latest`: MongoDB 최신 이미지

#### 2-2. MongoDB 컨테이너 상태 확인

```bash
# 실행 중인 MongoDB 컨테이너 확인
docker ps | grep mongo

# 컨테이너 로그 확인
docker logs arxiv-mongodb

# MongoDB 버전 확인
docker exec arxiv-mongodb mongosh --quiet --eval "db.version()"
```

#### 2-3. MongoDB 컨테이너 관리 명령어

```bash
# 컨테이너 시작
docker start arxiv-mongodb

# 컨테이너 중지
docker stop arxiv-mongodb

# 컨테이너 재시작
docker restart arxiv-mongodb

# 컨테이너 삭제 (데이터는 볼륨에 보존)
docker rm arxiv-mongodb

# 데이터까지 완전 삭제
docker rm arxiv-mongodb
docker volume rm mongodb_data
```

### 3. API 키 설정

#### 3-1. .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성하거나 `.env.example`을 복사:

```bash
cp .env.example .env
nano .env
```

#### 3-2. .env 파일 내용 작성

```bash
# ── AI Provider 설정 ──────────────────────
# "openai" 또는 "gemini" 선택
LLM_PROVIDER=gemini

# Gemini API Key (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=AIzaSyD_your_actual_key_here

# OpenAI API Key (https://platform.openai.com/api-keys)
# OPENAI_API_KEY=sk-your_openai_key_here

# ── MongoDB 설정 ───────────────────────────
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=arxiv_papers
MONGODB_COLLECTION=papers

# ── Slack (선택) ───────────────────────────
# SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# ── Zotero (선택) ──────────────────────────
# ZOTERO_API_KEY=
# ZOTERO_USER_ID=
# ZOTERO_COLLECTION_KEY=
```

**API 키 발급 방법:**
- **Gemini**: https://aistudio.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys

---

## 💻 사용 방법

### 기본 실행

```bash
conda activate Papers
cd /home/bskang/papers

# 전체 파이프라인 실행
python run_briefing.py

# Slack/Zotero 전송 없이 결과만 확인 (테스트용)
python run_briefing.py --dry-run

# MongoDB 초기화 후 실행
python run_briefing.py --reset --dry-run

# Zotero 저장 건너뛰기
python run_briefing.py --no-zotero
```

### 실행 단계 설명

```
1. MongoDB에서 이미 처리된 논문 ID 로드 (중복 방지)
   ↓
2. arXiv API로 논문 수집 (연도별 100편씩)
   - 최근: 6편 / 1년전: 9편 / 2년전: 6편 / 3~4년전: 9편
   ↓
3. 중복 필터링 및 학회지 우선순위 정렬
   ↓
4. Semantic Scholar에서 인용수 조회
   ↓
5. AI 트리아지 (OpenAI/Gemini)
   - 3-5문장 한글 요약
   - 태그 분류 (AD, VLA, Manipulation, Sim, Safety)
   - 관련성 점수 (0~5)
   ↓
6. 로그 파일 저장 (logs/YYYY-MM-DD.json)
   ↓
7. MongoDB에 저장 (id, title, summary, citation_count, saved_at 등)
   ↓
8. (선택) Slack 전송
   ↓
9. (선택) Zotero 저장 (점수 4.0 이상)
```

---

## 🗄️ MongoDB 데이터 관리

### MongoDB Shell로 확인

```bash
# MongoDB Shell 접속
docker exec -it arxiv-mongodb mongosh arxiv_papers

# Shell 내부에서 명령 실행
db.papers.countDocuments()                        # 전체 논문 수
db.papers.find().limit(5)                         # 최근 5개 논문
db.papers.distinct("id")                          # 모든 논문 ID
db.papers.find({score: {$gte: 4.0}})             # 점수 4.0 이상
db.papers.find({citation_count: {$gt: 0}})       # 인용수 있는 논문
db.papers.find({saved_at: {$regex: "^2026-02"}}) # 2월에 저장된 논문
```

### Python으로 확인

```bash
# 전체 논문 수
python -c "from paper_briefing.state import load_seen; print(f'총 {len(load_seen())}편')"

# 인용수 상위 10개
python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
collection = client['arxiv_papers']['papers']

print('인용수 TOP 10:')
for p in collection.find().sort('citation_count', -1).limit(10):
    print(f\"  [{p['citation_count']:3d} 인용] {p['title'][:50]}\")
"

# 오늘 저장된 논문
python -c "
from pymongo import MongoClient
from datetime import datetime
client = MongoClient('mongodb://localhost:27017/')
collection = client['arxiv_papers']['papers']

today = datetime.now().strftime('%Y-%m-%d')
count = collection.count_documents({'saved_at': {'\$regex': f'^{today}'}})
print(f'오늘({today}) 저장: {count}편')
"
```

### MongoDB 데이터 삭제

```bash
# 프로그램의 reset 옵션 사용 (추천)
python run_briefing.py --reset --dry-run

# Python으로 직접 삭제
python -c "from paper_briefing.state import reset_database; reset_database()"

# mongosh로 직접 삭제
docker exec -it arxiv-mongodb mongosh arxiv_papers --eval "db.papers.deleteMany({})"

# 특정 조건 삭제 (예: Score 0인 논문)
docker exec -it arxiv-mongodb mongosh arxiv_papers --eval "db.papers.deleteMany({score: 0.0})"
```



## 📊 데이터 구조

### MongoDB Document 스키마

```javascript
{
  "id": "2401.12345v1",              // arXiv ID (고유 키)
  "title": "Paper Title",             // 논문 제목
  "abstract": "Full abstract...",     // 초록
  "authors": ["Author1", "Author2"],  // 저자 목록 (최대 3명)
  "published": "2024-01-15",          // 논문 발표일
  "arxiv_url": "http://arxiv.org/abs/2401.12345v1",
  "pdf_url": "https://arxiv.org/pdf/2401.12345v1",
  "categories": ["cs.RO", "cs.LG"],   // arXiv 카테고리
  "journal_ref": "NeurIPS 2024",      // 학회지 정보
  "comment": "Accepted at ...",       // 코멘트
  "conference": "NeurIPS",            // 추출된 학회명
  "citation_count": 14,               // Semantic Scholar 인용수
  "summary": "3-5문장 한글 요약...",  // AI 생성 요약
  "tags": ["VLA", "Manipulation"],    // AI 분류 태그
  "score": 4.5,                       // AI 평가 점수 (0-5)
  "saved_at": "2026-02-23T14:18:19.123456"  // 저장 시각
}
```

### 로그 파일 (logs/YYYY-MM-DD.json)

매일 실행 시 해당 날짜의 JSON 파일에 처리된 논문 목록 저장:
- 같은 날 여러 번 실행하면 마지막 실행 결과로 덮어씌워짐
- MongoDB와 동일한 정보 포함

---

## ⚙️ 설정 파일 (config.py)

주요 설정값들:

```python
# arXiv 검색 카테고리
ARXIV_CATEGORIES = ["cs.RO", "cs.CV", "cs.LG", "cs.AI"]

# 주제 키워드 (5개 주제)
TOPIC_KEYWORDS = {
    "AD": ["autonomous driving", "self-driving", ...],
    "VLA": ["vision-language-action", "VLA", ...],
    "Manipulation": ["manipulation", "dexterous", ...],
    "Sim": ["sim-to-real", "simulation", ...],
    "Safety": ["safety", "verification", ...],
}

# 수집/처리 수량
MAX_FETCH = 60      # arXiv 후보 수
MAX_PROCESS = 30    # 최종 처리 대상 (할당량: 6+9+6+9=30)

# AI 설정
LLM_PROVIDER = "gemini"  # "openai" or "gemini"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "models/gemini-2.5-flash"
TRIAGE_BATCH = 10   # 배치당 논문 수
```

---

## 🔍 논문 수집 로직

### 연도별 할당량

- **최근 (2026년)**: 6편
- **1년전 (2025년)**: 9편
- **2년전 (2024년)**: 6편
- **3~4년전 (2022~2023년)**: 9편
- **총 30편**

### 수집 과정

각 연도별로:
1. **수집**: arXiv에서 최대 100편 다운로드
2. **정렬**: 주요 학회지(NeurIPS, CVPR, ICML 등) 우선순위
3. **중복 필터링**: MongoDB에 이미 있는 논문 ID 제외
4. **선택**: 할당량에 도달할 때까지 순차 선택

---

## 📈 인용수 추출 (Semantic Scholar)

### 동작 방식

1. arXiv ID로 Semantic Scholar API 호출
2. 각 논문마다 0.1초 지연 (rate limit 준수)
3. 404 응답 시 0으로 처리 (아직 인덱싱 안 된 최신 논문)

### API 세부사항

- **Endpoint**: `https://api.semanticscholar.org/graph/v1/paper/ARXIV:{id}`
- **무료**: API 키 불필요
- **Rate Limit**: 분당 100 요청 (30편 = 약 3초 소요)

### 코드 위치

```python
# paper_briefing/arxiv_fetcher.py
def fetch_citation_count(arxiv_id: str) -> int
def fetch_citations_batch(papers: List[Paper], delay: float = 0.1) -> None
```

---

## 🤖 AI 트리아지

### OpenAI 사용

```bash
# .env 파일
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**모델**: `gpt-4o-mini` (저렴하고 빠름)

### Gemini 사용

```bash
# .env 파일
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
```

**모델**: `models/gemini-2.5-flash` (최신, 안정적)

### AI가 생성하는 정보

각 논문마다:
- **summary**: 3-5문장 한글 요약 (문제, 방법론, 결과, 의의)
- **tags**: 1-3개 태그 (AD, VLA, Manipulation, Sim, Safety)
- **score**: 0~5점 (자율주행/VLA/로봇/sim2real/안전성 관련성)

---

## 📁 파일 구조

```
/home/bskang/papers/
├── .env                    # API 키 및 환경변수 (Git 제외)
├── .env.example            # 환경변수 템플릿
├── requirements.txt        # Python 패키지
├── run_briefing.py         # 메인 실행 스크립트
├── setup_cron.sh           # cron 설정 스크립트
├── concept.md              # 프로젝트 컨셉 문서
├── README.md               # 이 파일
│
├── paper_briefing/         # 핵심 모듈
│   ├── __init__.py
│   ├── config.py           # 중앙 설정 (키워드, 모델 등)
│   ├── arxiv_fetcher.py    # arXiv 수집 + 인용수 조회
│   ├── triage.py           # AI 트리아지 (OpenAI/Gemini)
│   ├── state.py            # MongoDB 관리
│   ├── logger.py           # JSON 로그 저장
│   ├── slack_sender.py     # Slack 전송
│   └── zotero_saver.py     # Zotero 저장
│
├── data/
│   └── seen_papers.json    # (레거시) 처리된 논문 ID
│
├── logs/
│   └── YYYY-MM-DD.json     # 일별 실행 로그
│
└── test_*.py               # 테스트 스크립트
```

---

## 🔧 문제 해결

### MongoDB 연결 실패

```bash
# Docker 컨테이너 상태 확인
docker ps | grep mongo

# 컨테이너가 없으면 시작
docker start arxiv-mongodb

# 로그 확인
docker logs arxiv-mongodb --tail 50

# Python으로 연결 테스트
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/'); print('연결 성공:', client.server_info()['version'])"
```

### Gemini API 오류

```bash
# 사용 가능한 모델 확인
python -c "
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
models = [m.name for m in client.models.list() if 'gemini' in m.name.lower()]
print('사용 가능한 모델:')
for m in models[:10]:
    print(f'  - {m}')
"

# 패키지 확인
pip list | grep genai
```

### 인용수 조회 실패

```bash
# Semantic Scholar API 테스트
curl "https://api.semanticscholar.org/graph/v1/paper/ARXIV:2401.12345?fields=citationCount"

# Python으로 테스트
python -c "
from paper_briefing.arxiv_fetcher import fetch_citation_count
count = fetch_citation_count('2401.12345v1')
print(f'인용수: {count}')
"
```

### 캐시 문제

```bash
# Python 캐시 삭제
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
```

---

## 📊 데이터 분석 예제

### MongoDB 쿼리 예제

```javascript
// 태그별 논문 수
db.papers.aggregate([
  {$unwind: "$tags"},
  {$group: {_id: "$tags", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

// Score와 인용수 상관관계
db.papers.find({
  score: {$gte: 4.0},
  citation_count: {$gte: 5}
}, {
  title: 1,
  score: 1,
  citation_count: 1
}).sort({score: -1})

// 학회지별 논문 수
db.papers.aggregate([
  {$match: {conference: {$ne: ""}}},
  {$group: {_id: "$conference", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

// 최근 30일 논문 추이
db.papers.aggregate([
  {$project: {
    date: {$substr: ["$saved_at", 0, 10]}
  }},
  {$group: {
    _id: "$date",
    count: {$sum: 1}
  }},
  {$sort: {_id: -1}},
  {$limit: 30}
])
```

---

## 🔄 자동화 (Cron)

매일 자동 실행하려면:

```bash
# cron 설정 실행
bash setup_cron.sh

# 또는 직접 crontab 편집
crontab -e

# 추가할 내용 (매일 오전 9시 실행)
0 9 * * * cd /home/bskang/papers && /home/bskang/miniconda3/envs/Papers/bin/python run_briefing.py
```

---

## 📝 로그 파일 형식

`logs/2026-02-23.json`:

```json
[
  {
    "id": "2401.12345v1",
    "title": "Paper Title",
    "score": 4.5,
    "tags": ["VLA", "Manipulation"],
    "summary": "3-5문장의 한글 요약...",
    "authors": ["Author1", "Author2"],
    "published": "2024-01-15",
    "citation_count": 14,
    "arxiv_url": "http://arxiv.org/abs/2401.12345v1",
    "pdf_url": "https://arxiv.org/pdf/2401.12345v1"
  }
]
```

---

## 🧪 테스트

### 개별 모듈 테스트

```bash
# arXiv 수집 테스트
python test_fetch.py

# MongoDB 연결 테스트
python test_mongodb.py

# 학회지 필터 테스트
python test_conference_filter.py

# 조건 선택 테스트
python test_criteria.py
```

---

## 🎯 주요 명령어 요약

```bash
# === 실행 ===
python run_briefing.py                    # 전체 실행
python run_briefing.py --dry-run          # 테스트 (Slack/Zotero 제외)
python run_briefing.py --reset --dry-run  # MongoDB 초기화 후 실행

# === MongoDB Docker ===
docker ps | grep mongo                    # 상태 확인
docker start arxiv-mongodb                # 시작
docker stop arxiv-mongodb                 # 중지
docker logs arxiv-mongodb                 # 로그
docker exec -it arxiv-mongodb mongosh     # Shell 접속

# === 데이터 확인 ===
python -c "from paper_briefing.state import load_seen; print(len(load_seen()))"
docker exec arxiv-mongodb mongosh arxiv_papers --eval "db.papers.countDocuments()"

# === 데이터 삭제 ===
python -c "from paper_briefing.state import reset_database; reset_database()"
docker exec -it arxiv-mongodb mongosh arxiv_papers --eval "db.papers.deleteMany({})"
```

---

## 📚 참고 문서

- [arXiv API](https://info.arxiv.org/help/api/index.html)
- [Semantic Scholar API](https://api.semanticscholar.org/)
- [OpenAI API](https://platform.openai.com/docs)
- [Google Gemini API](https://ai.google.dev/)
- [MongoDB Manual](https://www.mongodb.com/docs/manual/)
- [DBeaver](https://dbeaver.io/)

---

## 💡 팁

### 비용 절감
- Gemini 2.5 Flash는 무료 할당량이 크고 빠름 (추천)
- OpenAI gpt-4o-mini는 저렴 (30편 = 약 $0.05)

### 성능 최적화
- `TRIAGE_BATCH` 조정 (기본: 10편/배치)
- 인용수 조회 지연 시간 조정 (`delay=0.1`)

### 데이터 백업
```bash
# MongoDB 백업
docker exec arxiv-mongodb mongodump --db arxiv_papers --out /tmp/backup

# 볼륨 백업
docker run --rm -v mongodb_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mongodb_backup.tar.gz /data
```

---

## 📞 지원

문제가 발생하면:
1. 로그 확인: `docker logs arxiv-mongodb`
2. Python 오류: 터미널 출력 확인
3. API 한도: API 키 및 할당량 확인

---

**Last Updated**: 2026-02-23
