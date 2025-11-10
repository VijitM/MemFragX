#!/usr/bin/env bash
# Simple helper to trigger malloc_trim in a running process by sending SIGUSR1.
PID=$1
if [ -z "$PID" ]; then
  echo "usage: $0 <pid>"
  exit 1
fi
kill -USR1 $PID || echo "failed to send signal"
echo "Sent SIGUSR1 to $PID. Ensure the target process has the trim handler installed."
