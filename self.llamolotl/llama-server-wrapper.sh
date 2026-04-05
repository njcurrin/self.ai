#!/bin/bash
# Wrapper for llama-server that reads extra arguments from a config file.
# This allows the API to dynamically configure LoRA adapters (and other
# flags) without modifying supervisord config.

EXTRA_ARGS_FILE="/app/llama-server.args"

EXTRA_ARGS=""
if [ -f "$EXTRA_ARGS_FILE" ]; then
    EXTRA_ARGS=$(cat "$EXTRA_ARGS_FILE")
fi

# Use fixed chat template if available (works around llama.cpp |items bug on string arguments)
CHAT_TEMPLATE_FILE="/app/chat-templates/qwen3.jinja"
TEMPLATE_ARGS=""
if [ -f "$CHAT_TEMPLATE_FILE" ]; then
    TEMPLATE_ARGS="--chat-template-file $CHAT_TEMPLATE_FILE"
fi

# shellcheck disable=SC2086
exec /app/llama-server --jinja $TEMPLATE_ARGS $EXTRA_ARGS "$@"
