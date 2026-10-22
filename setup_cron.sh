#!/bin/bash

PROJECT_DIR="/Users/rutikpatil/Documents/GitHub/Job_Apply"
RUNNER_SCRIPT="$PROJECT_DIR/daily_runner.sh"

chmod +x "$RUNNER_SCRIPT"

# Cron job entry: Run daily at 9:00 AM
CRON_SCHEDULE="0 9 * * * $RUNNER_SCRIPT"

# Add cron job if not already present
(crontab -l 2>/dev/null | grep -v "$RUNNER_SCRIPT" ; echo "$CRON_SCHEDULE") | crontab -

echo "✅ Daily Cron Job successfully scheduled for 9:00 AM every day!"
echo "Cron Entry: $CRON_SCHEDULE"
