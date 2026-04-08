#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW_DIR="$ROOT_DIR/n8n/workflows"
ACTIVATE=false
RESTART_ON_ACTIVATE=false
FORCE_REIMPORT=false

for arg in "$@"; do
  case "$arg" in
    --activate)
      ACTIVATE=true
      ;;
    --restart)
      RESTART_ON_ACTIVATE=true
      ;;
    --force-reimport)
      FORCE_REIMPORT=true
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: $0 [--activate] [--restart] [--force-reimport]"
      exit 1
      ;;
  esac
done

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "ERROR: docker compose (or docker-compose) is required."
  exit 1
fi

echo "==> Waiting for n8n container to be running..."
for _ in $(seq 1 30); do
  if "${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.yml" ps --status running --services 2>/dev/null | awk '$1=="n8n"{found=1} END{exit !found}'; then
    break
  fi
  sleep 2
done

if ! "${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.yml" ps --status running --services | awk '$1=="n8n"{found=1} END{exit !found}'; then
  echo "ERROR: n8n container is not running."
  exit 1
fi

if [ ! -d "$WORKFLOW_DIR" ]; then
  echo "No workflow directory found at: $WORKFLOW_DIR"
  exit 0
fi

run_n8n_cli_with_retry() {
  local max_attempts="${1:-20}"
  shift
  local attempt=1
  local wait_seconds=2
  local output

  while [ "$attempt" -le "$max_attempts" ]; do
    if output="$("${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.yml" exec -T n8n "$@" 2>&1)"; then
      printf "%s\n" "$output"
      return 0
    fi

    echo "WARN: n8n CLI attempt $attempt/$max_attempts failed: $output"
    sleep "$wait_seconds"
    attempt=$((attempt + 1))
  done

  echo "ERROR: command failed after $max_attempts attempts: $*"
  return 1
}

echo "==> Waiting for n8n CLI readiness (migrations/startup)..."
run_n8n_cli_with_retry 30 n8n list:workflow >/dev/null

echo "==> Reading existing workflows from n8n..."
existing="$(run_n8n_cli_with_retry 10 n8n list:workflow || true)"

imported_count=0
skipped_count=0
activated_count=0
activation_skipped_count=0

desired_names=""
for file in "$WORKFLOW_DIR"/*.json; do
  [ -e "$file" ] || continue
  wf_name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], "r", encoding="utf-8")).get("name","").strip())' "$file")"

  if [ -z "$wf_name" ]; then
    echo "WARN: skipping $(basename "$file") (missing workflow name)."
    skipped_count=$((skipped_count + 1))
    continue
  fi

  desired_names="${desired_names}${wf_name}"$'\n'
done

missing_count=0
while IFS= read -r wf_name; do
  [ -n "$wf_name" ] || continue
  if printf "%s\n" "$existing" | awk -F'|' -v name="$wf_name" '$2==name {found=1} END {exit !found}'; then
    skipped_count=$((skipped_count + 1))
  else
    missing_count=$((missing_count + 1))
  fi
done <<< "$desired_names"

if [ "$FORCE_REIMPORT" = true ]; then
  echo "FORCE IMPORT: reimporting all workflows from /opt/n8n/workflows..."
  run_n8n_cli_with_retry 15 n8n import:workflow --separate --input=/opt/n8n/workflows
  imported_count="$(printf "%s" "$desired_names" | awk 'NF{count++} END{print count+0}')"
elif [ "$missing_count" -gt 0 ]; then
  echo "IMPORT: $missing_count workflow(s) missing, running bulk import..."
  run_n8n_cli_with_retry 15 n8n import:workflow --separate --input=/opt/n8n/workflows
  imported_count="$missing_count"
else
  echo "SKIP IMPORT: all workflows already present."
fi

echo "==> Workflow import finished."
echo "Imported: $imported_count | Skipped: $skipped_count"

if [ "$ACTIVATE" = true ]; then
  echo "==> Activating workflows (publish)..."
  # Refresh workflow list to include newly imported ones.
  existing="$(run_n8n_cli_with_retry 10 n8n list:workflow || true)"

  for file in "$WORKFLOW_DIR"/*.json; do
    [ -e "$file" ] || continue
    wf_name="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], "r", encoding="utf-8")).get("name","").strip())' "$file")"
    [ -n "$wf_name" ] || continue

    # If duplicates exist, choose the newest one (last listed).
    wf_id="$(printf "%s\n" "$existing" | awk -F'|' -v name="$wf_name" '$2==name {id=$1} END {print id}')"
    if [ -z "$wf_id" ]; then
      echo "SKIP ACTIVATE: $wf_name (not found)"
      activation_skipped_count=$((activation_skipped_count + 1))
      continue
    fi

    echo "ACTIVATE: $wf_name ($wf_id)"
    run_n8n_cli_with_retry 15 n8n publish:workflow --id="$wf_id" >/dev/null
    activated_count=$((activated_count + 1))
  done

  echo "Activation: $activated_count | Skipped: $activation_skipped_count"

  if [ "$RESTART_ON_ACTIVATE" = true ]; then
    echo "==> Restarting n8n to apply published workflows..."
    "${COMPOSE_CMD[@]}" -f "$ROOT_DIR/docker-compose.yml" restart n8n >/dev/null
    echo "n8n restarted."
  fi
fi
