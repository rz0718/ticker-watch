#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p docs/assets
python docs/demo_cache.py

tmux -L ticker-watch-demo kill-server >/dev/null 2>&1 || true

cleanup() {
  tmux -L ticker-watch-demo kill-server >/dev/null 2>&1 || true
}
trap cleanup EXIT

tmux -L ticker-watch-demo new-session -d -s demo
tmux -L ticker-watch-demo set -g status on
tmux -L ticker-watch-demo set -g status-position bottom
tmux -L ticker-watch-demo set -g status-style bg=green,fg=black
tmux -L ticker-watch-demo set -g status-left " ticker-watch "
tmux -L ticker-watch-demo set -g status-left-length 16
tmux -L ticker-watch-demo set -g status-right "#(TICKER_WATCH_CACHE_DIR=/tmp/ticker-watch-demo-cache ticker-watch status --compact --marquee --marquee-width 90)"
tmux -L ticker-watch-demo set -g status-right-length 200
tmux -L ticker-watch-demo set -g status-interval 1

vhs docs/ticker-watch-tmux.tape
