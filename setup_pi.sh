#!/bin/bash
# Raspberry Pi setup for Food Tracker cron job.
# Run this once on the Pi after cloning the project.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_FILE="$PROJECT_DIR/cron.log"

echo "=== Food Tracker — Raspberry Pi Setup ==="
echo

# 1. Python venv
echo "[1/4] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" -q
echo "  Done."

# 2. Gemini API key check
echo "[2/4] Checking Gemini API key..."
GEMINI_KEY="$HOME/.config/gemini/api_key.txt"
if [ -f "$GEMINI_KEY" ]; then
    echo "  Found: $GEMINI_KEY"
else
    mkdir -p "$HOME/.config/gemini"
    echo "  Not found: $GEMINI_KEY"
    echo "  Get a free API key at: https://aistudio.google.com/apikey"
    echo "  Then save it:  echo 'YOUR_KEY' > $GEMINI_KEY"
fi

# 3. Credentials check
echo "[3/4] Checking Google credentials..."
CREDS="$HOME/.config/gcloud/food-tracker-sa.json"
if [ -f "$CREDS" ]; then
    echo "  Found: $CREDS"
else
    echo "  Not found: $CREDS"
    echo "  Place your service account JSON key at that path, or update config.py"
fi

# 4. Cron job
echo "[4/4] Installing cron job (daily at 4:00 AM)..."
CRON_CMD="0 4 * * * cd $PROJECT_DIR && $VENV_DIR/bin/python sync_and_estimate.py >> $LOG_FILE 2>&1"

# Remove any existing food tracker cron entry, then add the new one
(crontab -l 2>/dev/null | grep -v "sync_and_estimate.py"; echo "$CRON_CMD") | crontab -
echo "  Installed: 4:00 AM daily"
echo "  Logs: $LOG_FILE"

echo
echo "=== Setup complete ==="
echo
echo "Next steps:"
echo "  1. Ensure your service account JSON is at: $CREDS"
echo "  2. Ensure your Gemini API key is at: $GEMINI_KEY"
echo "  3. Upload the template:  $VENV_DIR/bin/python upload_template.py"
echo "  4. Test the sync:        $VENV_DIR/bin/python sync_and_estimate.py"
echo "  5. Share the Google Sheet with your personal Google account to view it"
