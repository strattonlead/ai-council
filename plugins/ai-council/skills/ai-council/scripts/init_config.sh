#!/usr/bin/env bash
# Create ~/.ai-council/config.env interactively.
#
# RUN THIS YOURSELF, IN YOUR OWN TERMINAL. The API key is read with a hidden
# prompt and written straight to a 0600 file, so it never passes through a model's
# context. If an agent offers to run this for you, decline — the key would end up
# in the transcript.

set -euo pipefail

CONFIG_DIR="${AI_COUNCIL_HOME:-$HOME/.ai-council}"
CONFIG_FILE="${AI_COUNCIL_CONFIG:-$CONFIG_DIR/config.env}"

echo "AI Council setup"
echo "Config file: $CONFIG_FILE"
echo

if [[ -f "$CONFIG_FILE" ]]; then
  read -r -p "Config already exists. Overwrite? [y/N] " overwrite
  [[ "$overwrite" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
fi

default_url="http://localhost:4000"
read -r -p "LiteLLM base URL [$default_url]: " base_url
base_url="${base_url:-$default_url}"
base_url="${base_url%/}"

# -s keeps the key off the screen and out of any captured output.
read -r -s -p "LiteLLM API key (input hidden): " api_key
echo
if [[ -z "$api_key" ]]; then
  echo "No key entered. Aborted." >&2
  exit 1
fi

default_models="gpt-5,gemini-2.5-pro,deepseek-chat,claude-sonnet-4-6"
read -r -p "Council roster, comma-separated [$default_models]: " models
models="${models:-$default_models}"

mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"

umask 177
cat > "$CONFIG_FILE" <<EOF
# AI Council configuration. Keep this file private; do not commit it.
AI_COUNCIL_BASE_URL=$base_url
AI_COUNCIL_API_KEY=$api_key
AI_COUNCIL_MODELS=$models
AI_COUNCIL_TIMEOUT=180
EOF
chmod 600 "$CONFIG_FILE"

unset api_key

echo
echo "Written to $CONFIG_FILE (mode 600)."
echo "Verify with:  python3 scripts/check_setup.py"
echo "The key is not printed by that script and should never be pasted into a chat."
