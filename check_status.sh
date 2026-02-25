#!/usr/bin/env bash
# Cron 작업 상태 및 최근 실행 결과 확인 스크립트

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          📊 Daily Paper Briefing 상태 확인                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. Cron 등록 확인
echo "【1】 Cron 작업 등록"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if crontab -l 2>/dev/null | grep -q "run_briefing.py"; then
    echo "✅ 등록됨"
    crontab -l | grep "run_briefing.py"
else
    echo "❌ 미등록"
fi
echo ""

# 2. Cron 서비스 상태
echo "【2】 Cron 서비스"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if systemctl is-active --quiet cron; then
    echo "✅ 활성화"
else
    echo "❌ 비활성화"
fi
echo ""

# 3. 현재 시간 및 다음 실행 예정
echo "【3】 실행 스케줄"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "현재 시각: $(date '+%Y-%m-%d %H:%M:%S')"
current_hour=$(date '+%H')
if [ "$current_hour" -lt 7 ]; then
    echo "다음 실행: 오늘 07:00"
else
    echo "다음 실행: 내일 07:00"
fi
echo ""

# 4. 최근 실행 로그
echo "【4】 최근 실행 로그"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f logs/cron.log ]; then
    log_size=$(du -h logs/cron.log | cut -f1)
    echo "✅ 로그 파일: logs/cron.log ($log_size)"
    echo ""
    echo "마지막 20줄:"
    tail -20 logs/cron.log
else
    echo "⏳ 아직 실행 기록 없음"
fi
echo ""

# 5. 생성된 논문 로그 파일
echo "【5】 논문 로그 파일"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ls logs/2026-*.json >/dev/null 2>&1; then
    echo "최근 3개 파일:"
    ls -lht logs/2026-*.json | head -3
    echo ""
    latest=$(ls -t logs/2026-*.json | head -1)
    paper_count=$(python3 -c "import json; print(len(json.load(open('$latest'))))" 2>/dev/null || echo "0")
    echo "최신 파일: $latest ($paper_count편)"
else
    echo "⏳ 논문 로그 없음"
fi
echo ""

# 6. MongoDB 저장 상태
echo "【6】 MongoDB 저장 상태"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
total_papers=$(python3 -c "from paper_briefing.state import load_seen; print(len(load_seen()))" 2>/dev/null || echo "확인 불가")
echo "누적 처리 논문: $total_papers편"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 실시간 모니터링: tail -f logs/cron.log"
echo "💡 수동 실행: python run_briefing.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
