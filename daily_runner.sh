#!/bin/bash

# Navigate to project directory
PROJECT_DIR="/Users/rutikpatil/Documents/GitHub/Job_Apply"
cd "$PROJECT_DIR" || exit 1

LOG_FILE="$PROJECT_DIR/automation.log"
echo "==========================================" >> "$LOG_FILE"
echo "Starting Daily LinkedIn Job Automation (40 India + 10 Intl Big Tech): $(date)" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"

# Run Python Job Extraction & Profile Matching (40 India + 10 International Big Tech = 50 total)
./venv/bin/python main.py --india-limit 40 --intl-limit 10 >> "$LOG_FILE" 2>&1

echo "Finished Daily Run: $(date)" >> "$LOG_FILE"
