"""OpenAI API로 논문 목록을 일괄 트리아지합니다 (요약 / 태그 / 점수)."""

from __future__ import annotations

import json
import os
from typing import List

from openai import OpenAI

from .arxiv_fetcher import Paper
from .config import (
    ABSTRACT_CHARS,
    OPENAI_MODEL,
    GEMINI_MODEL,
    LLM_PROVIDER,
    TOPIC_KEYWORDS,
    TRIAGE_BATCH,
)

_openai_client: OpenAI | None = None
_gemini_client = None


def _get_openai_client() -> OpenAI | None:
    global _openai_client
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    if _openai_client is None:
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_gemini_client():
    global _gemini_client
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    if _gemini_client is None:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            _gemini_client = client
        except ImportError:
            print("[triage] google-genai 패키지가 설치되지 않았습니다.")
            print("[triage] 설치: pip install google-genai")
            return None
    return _gemini_client


_TAGS = list(TOPIC_KEYWORDS.keys())  # ["AD", "VLA", "Manipulation", "Sim", "Safety"]

_SYSTEM_PROMPT = f"""You are a robotics/AI research assistant.
For each paper, return ONLY a JSON array. Each element must have:
  - "id": paper arxiv short id (e.g. "2401.12345")
  - "summary": 3-5 sentence detailed summary in Korean (연구의 핵심 문제, 제안하는 방법론, 주요 실험 결과, 그리고 실용적 의의를 포함)
  - "tags": list (1-3) from {_TAGS}
  - "score": float 0-5 (relevance to autonomous driving, VLA, robot manipulation, sim-to-real, safety)

Return valid JSON only, no markdown fences."""


def _build_user_prompt(papers: List[Paper]) -> str:
    items = []
    for p in papers:
        abstract_trunc = p.abstract[:ABSTRACT_CHARS]
        items.append(
            f'id: {p.id}\ntitle: {p.title}\nabstract: {abstract_trunc}'
        )
    return "\n\n---\n\n".join(items)


def triage_papers(papers: List[Paper]) -> List[Paper]:
    """papers 리스트에 summary/tags/score를 채워 반환합니다."""
    if not papers:
        return papers

    # Provider에 따라 적절한 함수 호출
    if LLM_PROVIDER == "gemini":
        return _triage_with_gemini(papers)
    else:
        return _triage_with_openai(papers)


def _triage_with_openai(papers: List[Paper]) -> List[Paper]:
    """OpenAI API를 사용한 논문 트리아지."""
    client = _get_openai_client()
    if client is None:
        print("[triage] OPENAI_API_KEY 미설정 → 트리아지 건너뜀.")
        return papers

    results: dict[str, dict] = {}

    # 배치 처리
    for i in range(0, len(papers), TRIAGE_BATCH):
        batch = papers[i : i + TRIAGE_BATCH]
        user_msg = _build_user_prompt(batch)

        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            parsed = json.loads(raw)

            # 응답이 배열 직접이거나 {"papers": [...]} 형태 모두 처리
            if isinstance(parsed, list):
                items = parsed
            else:
                items = next(
                    (v for v in parsed.values() if isinstance(v, list)), []
                )

            for item in items:
                pid = str(item.get("id", "")).strip()
                results[pid] = item

        except Exception as exc:
            print(f"[triage] OpenAI batch {i//TRIAGE_BATCH + 1} 실패: {exc}")

    # 결과 주입
    for paper in papers:
        info = results.get(paper.id, {})
        paper.summary = info.get("summary", "요약 없음")
        paper.tags = info.get("tags", [])
        try:
            paper.score = float(info.get("score", 0.0))
        except (TypeError, ValueError):
            paper.score = 0.0

    return papers


def _triage_with_gemini(papers: List[Paper]) -> List[Paper]:
    """Gemini API를 사용한 논문 트리아지."""
    client = _get_gemini_client()
    if client is None:
        print("[triage] GEMINI_API_KEY 미설정 또는 패키지 미설치 → 트리아지 건너뜀.")
        return papers

    results: dict[str, dict] = {}

    # 배치 처리
    for i in range(0, len(papers), TRIAGE_BATCH):
        batch = papers[i : i + TRIAGE_BATCH]
        user_msg = _build_user_prompt(batch)
        full_prompt = f"{_SYSTEM_PROMPT}\n\n{user_msg}"

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=full_prompt,
                config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                }
            )
            raw = response.text
            parsed = json.loads(raw)

            # 응답이 배열 직접이거나 {"papers": [...]} 형태 모두 처리
            if isinstance(parsed, list):
                items = parsed
            else:
                items = next(
                    (v for v in parsed.values() if isinstance(v, list)), []
                )

            for item in items:
                pid = str(item.get("id", "")).strip()
                results[pid] = item

        except Exception as exc:
            print(f"[triage] Gemini batch {i//TRIAGE_BATCH + 1} 실패: {exc}")

    # 결과 주입
    for paper in papers:
        info = results.get(paper.id, {})
        paper.summary = info.get("summary", "요약 없음")
        paper.tags = info.get("tags", [])
        try:
            paper.score = float(info.get("score", 0.0))
        except (TypeError, ValueError):
            paper.score = 0.0

    return papers
