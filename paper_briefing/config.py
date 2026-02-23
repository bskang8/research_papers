"""중앙 설정값 - 여기서 키워드/카테고리/모델 등을 조정합니다."""

# ── arXiv 검색 설정 ────────────────────────────────────────────────────────────
ARXIV_CATEGORIES = ["cs.RO", "cs.CV", "cs.LG", "cs.AI"]

# 5개 주제 키워드 (제목·초록 검색용)
TOPIC_KEYWORDS = {
    "AD":          ["autonomous driving", "self-driving", "motion planning",
                    "trajectory prediction", "end-to-end driving"],
    "VLA":         ["vision-language-action", "VLA", "language-conditioned",
                    "multimodal policy", "vision language model robot"],
    "Manipulation":["manipulation", "dexterous", "diffusion policy",
                    "imitation learning", "grasp"],
    "Sim":         ["sim-to-real", "domain randomization", "simulation",
                    "synthetic data", "digital twin"],
    "Safety":      ["safety", "verification", "runtime assurance",
                    "uncertainty", "out-of-distribution", "OOD"],
}

# arXiv API 쿼리 문자열
_cat_q = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
_kw_flat = [kw for kws in TOPIC_KEYWORDS.values() for kw in kws]
_kw_q = " OR ".join(f'abs:"{kw}"' for kw in _kw_flat)
SEARCH_QUERY = f"({_cat_q}) AND ({_kw_q})"

MAX_FETCH   = 60   # arXiv에서 가져올 후보 수 (seen 필터링 후 30편 확보 위해 여유 포함)
MAX_PROCESS = 30   # AI 트리아지·Slack 전송 대상 최대 논문 수

# ── AI 설정 ───────────────────────────────────────────────────────────────────
LLM_PROVIDER  = "gemini" ## os.getenv("LLM_PROVIDER", "openai").lower()  # "openai" or "gemini"
OPENAI_MODEL  = "gpt-4o-mini"
GEMINI_MODEL  = "models/gemini-2.5-flash"  # 빠르고 저렴 (alternatives: gemini-2.0-flash, gemini-flash-latest)
TRIAGE_BATCH  = 10          # 한 번에 트리아지할 논문 수 (품질·안정성 균형)
ABSTRACT_CHARS = 600        # 초록 잘라 보낼 최대 길이

# ── Zotero 설정 (선택) ────────────────────────────────────────────────────────
ZOTERO_SCORE_THRESHOLD = 4.0   # 이 점수 이상인 논문만 Zotero에 저장

# ── MongoDB 설정 ───────────────────────────────────────────────────────────────
import os
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "arxiv_papers")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "papers")

# ── 상태 파일 ─────────────────────────────────────────────────────────────────
STATE_FILE = "data/seen_papers.json"
