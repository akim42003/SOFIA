#!/usr/bin/env bash

session="sofia_start"

cmd_list=(
  "fastmcp run gmail_mcp.py"
  "ollama serve"
  "python chat_brain.py"
)

# If the session already exists just attach
if tmux has-session -t "$session" 2>/dev/null; then
  tmux attach-session -t "$session"
  exit 0
fi

# Create a new, detached session with one window
tmux new-session -d -s "$session" -n "win0"

# Send the first command into window 0
tmux send-keys -t "$session:0" \
  "conda activate sofia && ${cmd_list[0]} && exec bash" C-m

#For each remaining command, make a new window and send it there
for idx in 1 2; do
  tmux new-window -t "$session" -n "win$idx"
  tmux send-keys -t "$session:$idx" \
    "conda activate sofia && ${cmd_list[idx]} && exec bash" C-m
done

#Attach so you can switch between them
tmux attach-session -t "$session"
