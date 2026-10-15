#!/bin/bash
# Daily NotebookLM login check for a headless server, with a Telegram warning when it has expired.
# Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment (or in the file given as $ENV_FILE).
# With --confirm it also sends a message when the login works (login-and-push.ps1 uses it).
#
#   check-auth.sh             # from a systemd timer or cron, every morning
#   check-auth.sh --confirm   # right after copying a fresh login to the server
[ -n "$ENV_FILE" ] && source "$ENV_FILE"
LECTURE_NOTES=${LECTURE_NOTES:-lecture-notes}

send() {
  [ -z "$TELEGRAM_BOT_TOKEN" ] && { echo "$1"; return; }
  curl -s -o /dev/null "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode chat_id="$TELEGRAM_CHAT_ID" --data-urlencode "text=$1"
}

if "$LECTURE_NOTES" auth >/dev/null 2>&1; then
  [ "$1" = "--confirm" ] && send "✅ NotebookLM login OK on the server: /lecture is ready."
  exit 0
fi
send "⚠️ The NotebookLM login on the server has expired, so /lecture can't run. On your PC run login-and-push.ps1 (sign in, press Enter) and it will copy the new login here."
exit 1
