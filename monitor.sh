#!/bin/bash
# VTT App Build Monitor
BACKEND_WT="/Users/appuram/Downloads/vttapp-wt-backend"
RECORDING_WT="/Users/appuram/Downloads/vttapp-wt-frontend-recording"
UI_WT="/Users/appuram/Downloads/vttapp-wt-frontend-ui"
MAIN_REPO="/Users/appuram/Downloads/vttapp"
CMUX="/Applications/cmux.app/Contents/Resources/bin/cmux"

check_done() {
  local wt=$1
  [ -f "$wt/DONE.txt" ] && echo "✅ $(cat $wt/DONE.txt)" || echo "⏳ In progress..."
}

while true; do
  clear
  echo "════════════════════════════════════════"
  echo "   VoiceToText App — Build Monitor"
  echo "   $(date '+%H:%M:%S')"
  echo "════════════════════════════════════════"
  echo ""

  B1=$(check_done "$BACKEND_WT")
  B2=$(check_done "$RECORDING_WT")
  B3=$(check_done "$UI_WT")

  echo "  Agent 1 — Backend API:       $B1"
  echo "  Agent 2 — Frontend Recording: $B2"
  echo "  Agent 3 — Frontend UI:        $B3"
  echo ""

  # Show last 3 lines of each agent pane
  echo "── Agent 1 (pane:34) ─────────────────"
  $CMUX read-screen --surface surface:51 --lines 5 2>/dev/null | tail -3
  echo ""
  echo "── Agent 2 (pane:35) ─────────────────"
  $CMUX read-screen --surface surface:52 --lines 5 2>/dev/null | tail -3
  echo ""
  echo "── Agent 3 (pane:36) ─────────────────"
  $CMUX read-screen --surface surface:53 --lines 5 2>/dev/null | tail -3
  echo ""

  if [[ -f "$BACKEND_WT/DONE.txt" && -f "$RECORDING_WT/DONE.txt" && -f "$UI_WT/DONE.txt" ]]; then
    echo "🎉 All agents done! Starting merge..."
    break
  fi

  echo "  [refreshes every 20s — Ctrl+C to stop]"
  sleep 20
done

echo ""
echo "════ MERGING BRANCHES ════"
cd "$MAIN_REPO"

echo "→ Merging feature/backend..."
git merge feature/backend --no-edit -m "merge: feature/backend" && echo "  ✅ backend merged"

echo "→ Merging feature/frontend-recording..."
git merge feature/frontend-recording --no-edit -m "merge: feature/frontend-recording" && echo "  ✅ recording merged"

echo "→ Merging feature/frontend-ui..."
git merge feature/frontend-ui --no-edit -m "merge: feature/frontend-ui" && echo "  ✅ ui merged"

echo ""
echo "════ FINAL STATE ════"
git log --oneline -8
echo ""
echo "✅ All branches merged. VTT App ready!"
echo "   Backend:  cd backend && uvicorn main:app --reload --port 8000"
echo "   Frontend: cd frontend && npm run dev"
