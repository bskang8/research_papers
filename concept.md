# 매일 논문 자동 브리핑(30편) + Slack 전달 + (선택) Zotero/NotebookLM 루틴

아래 구조는 “매일 최신 논문을 자동으로 모으고 → 중요한 포인트만 요약해서 Slack으로 보내고 → 관심 논문만 저장/오디오로 소비”하는 **가볍고 현실적인 자동화**입니다.  
(개인 PC에서 매일 1번 실행, OpenAI API 사용)

---

## 0) 한 줄 요약
**arXiv에서 30편 수집 → AI로 짧게 요약/점수/태그 생성 → Slack으로 카드 형태 전송 → (선택) Zotero 저장 → (선택) NotebookLM 오디오**.

---

## 1) 전체 흐름(매일 1회)
1. **수집(Discover)**: arXiv에서 “오늘 올라온” 논문 후보 최대 30편을 가져온다.
2. **선별(Triage)**: AI가 제목/초록 기반으로
   - 1~2줄 요약
   - 태그(자율주행/VLA/Manipulation/Sim/Safety)
   - 중요도 점수(0~5)
   를 만든다.
3. **전달(Deliver)**: Slack에 “오늘의 트렌드 + 논문 카드 30개”를 보낸다.
4. **저장(선택)**: 점수 높은 논문만 Zotero에 넣고 PDF를 정리한다.
5. **오디오(선택)**: 정말 중요한 1~2편은 NotebookLM에 넣어 Audio Overview로 듣는다.

---

## 2) arXiv 수집: 쿼리(5개 주제 반영)

### 추천: “혼합(전체)” 1개 쿼리로 30편 뽑기
- 카테고리: 로봇/비전/머신러닝/AI 범위를 기본으로 잡고
- 키워드: 자율주행, VLA, 매니퓰레이션, 시뮬, 세이프티를 제목/초록에서 찾는다

예시(사람이 읽기 쉬운 형태):
- 카테고리: `cs.RO, cs.CV, cs.LG, cs.AI`
- 키워드(제목/초록에 포함되면 포함):
  - 자율주행: autonomous driving, self-driving, motion planning, trajectory
  - VLA: vision-language-action, VLA, language-conditioned, multimodal policy
  - Manipulation: manipulation, grasp, dexterous, diffusion policy, imitation learning
  - Sim: simulation, simulator, sim-to-real, domain randomization
  - Safety: safety, verification, runtime assurance, uncertainty, OOD

운영 방식:
- “최신순 + 최대 30편”만 가져온다.
- 어제 본 논문은 다시 나오지 않도록 ID를 로컬 파일에 저장(state).

### (선택) 주제별로 따로 집계하고 싶다면
- Autonomous driving / VLA / Manipulation / Sim / Safety 쿼리를 각각 돌려서
- “오늘 주제별 몇 편인지”를 더 정확하게 만들 수 있다.
- 다만 처음엔 **혼합 1쿼리 + AI 태깅**이 가장 단순하다.

---

## 3) AI(1차 요약/점수/태그) 규칙(간단 버전)
각 논문마다 아래 4가지만 만들면 충분합니다.

- **요약 1~2줄**: “뭘 했는지 / 왜 중요한지”
- **태그**: (AD, VLA, Manipulation, Sim, Safety) 중 1~3개
- **점수 0~5**: 내 관심사 적합도 + 새로움 + 실험/근거 느낌
- **링크**: arXiv / PDF

이 단계의 목표는 “읽을 후보를 빠르게 걸러내기”입니다.  
깊은 분석은 점수 높은 것만 따로 합니다.

---

## 4) Slack 전송: blocks 메시지 템플릿(JSON)

아래 형태로 보내면 일반인이 봐도 한눈에 구조를 이해합니다.

- 상단: 오늘 브리핑 제목
- 트렌드 2~3줄
- 논문 카드 N개(각 카드: 제목 + 점수/태그 + 링크 + 요약)

예시 템플릿:
```json
{
  "text": "Daily Paper Briefing",
  "blocks": [
    { "type": "header", "text": { "type": "plain_text", "text": "Daily Paper Briefing (30 candidates)" } },
    { "type": "section", "text": { "type": "mrkdwn", "text": "*Trends*\n-  AD: ...\n-  VLA: ...\n-  Safety: ..." } },
    { "type": "divider" },

    { "type": "section", "text": { "type": "mrkdwn", "text": "*[4.5/5 | VLA, Manipulation]* Paper Title\n<https://arxiv.org/abs/XXXX.XXXXX|arXiv> | <https://arxiv.org/pdf/XXXX.XXXXX.pdf|PDF>" } },
    { "type": "context", "elements": [ { "type": "mrkdwn", "text": "1–2 line summary here. (Why it matters / limitation)" } ] },
    { "type": "divider" }

    // ... 논문 수만큼 반복 ...
  ]
}
