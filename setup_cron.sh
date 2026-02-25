#!/usr/bin/env bash
# 매일 오전 7시 브리핑 자동 실행 crontab 설정 스크립트

PYTHON="/home/bskang/miniconda3/envs/Papers/bin/python"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/logs/cron.log"

CRON_JOB="0 7 * * * cd $SCRIPT_DIR && $PYTHON run_briefing.py >> $LOG 2>&1"

# 기존에 같은 항목이 있으면 중복 추가하지 않음
if crontab -l 2>/dev/null | grep -qF "run_briefing.py"; then
    echo "crontab에 이미 등록되어 있습니다."
    echo "기존 등록 해제 후 재등록하려면 다음 명령을 실행하세요:"
    echo "  crontab -l | grep -v 'run_briefing.py' | crontab -"
    echo "  bash setup_cron.sh"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ crontab 등록 완료: 매일 07:00 실행"
    echo "$CRON_JOB"
fi
