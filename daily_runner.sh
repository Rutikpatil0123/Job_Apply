#!/bin/bash

# Navigate to project directory
PROJECT_DIR="/Users/rutikpatil/Documents/GitHub/Job_Apply"
cd "$PROJECT_DIR" || exit 1

LOG_FILE="$PROJECT_DIR/automation.log"
echo "==========================================" >> "$LOG_FILE"
echo "Starting Daily LinkedIn Job Automation (40 India + 10 Intl Big Tech): $(date)" >> "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"

# Part 1: Collect 40 India + 10 International Big Tech jobs and export to CSV
echo "--- Part 1: Job Collection ---" >> "$LOG_FILE"
./venv/bin/python main.py --india-limit 40 --intl-limit 10 >> "$LOG_FILE" 2>&1

# Part 2: Auto-draft Gmail applications for top matches (top 10 by default)
echo "--- Part 2: Gmail Draft Applications ---" >> "$LOG_FILE"
./venv/bin/python draft_applications.py --limit 10 --min-score 70 >> "$LOG_FILE" 2>&1

echo "Finished Daily Run: $(date)" >> "$LOG_FILE"
