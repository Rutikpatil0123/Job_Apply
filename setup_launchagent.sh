#!/bin/bash

PLIST_NAME="com.rutik.jobapply.plist"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PLIST="$PROJECT_DIR/$PLIST_NAME"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$PLIST_NAME"

mkdir -p "$TARGET_DIR"

# Unload if previously loaded
launchctl unload "$TARGET_PLIST" 2>/dev/null

# Copy plist to LaunchAgents
cp "$SOURCE_PLIST" "$TARGET_PLIST"

# Load new LaunchAgent
launchctl load "$TARGET_PLIST"

echo "✅ macOS Native LaunchAgent successfully registered and active!"
echo "It will run daily at 9:00 AM (and catches up automatically if your laptop was asleep)."
