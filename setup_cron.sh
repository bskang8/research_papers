#!/usr/bin/env bash
# 매일 오전 9시 브리핑 자동 실행 crontab 설정 스크립트

PYTHON="/home/bskang/miniconda3/envs/Papers/bin/python"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$SCRIPT_DIR/logs/cron.log"

CRON_JOB="0 9 * * * cd $SCRIPT_DIR && $PYTHON run_briefing.py >> $LOG 2>&1"

# 기존에 같은 항목이 있으면 중복 추가하지 않음
if crontab -l 2>/dev/null | grep -qF "run_briefing.py"; then
    echo "crontab에 이미 등록되어 있습니다."
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "crontab 등록 완료: 매일 09:00 실행"
    echo "$CRON_JOB"
fi
