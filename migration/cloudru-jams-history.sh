#!/usr/bin/env bash
set -uo pipefail
cd /opt/jams-src
echo "=== текущая версия/коммит ==="
git log -1 --format='%h %ad %s' --date=short 2>/dev/null
echo
echo "=== теги JAMS ==="
git ls-remote --tags origin 2>/dev/null | tail -12
echo
echo "=== история package.json фронта (когда меняли @mui) ==="
git fetch --unshallow --quiet 2>&1 | tail -2 || echo "  (unshallow не удался, пробую deepen)"
git fetch --deepen=500 --quiet 2>&1 | tail -2 || true
echo "--- последние изменения package.json ---"
git log --oneline -12 -- jams-react-client/package.json 2>/dev/null
echo
echo "--- когда появился @mui/material ^9 ---"
git log -S'"@mui/material": "^9' --oneline --date=short --format='%h %ad %s' -- jams-react-client/package.json 2>/dev/null | head -5
echo "--- когда был @mui/material v5/v6 ---"
git log -S'"@mui/material": "^5' --oneline --date=short --format='%h %ad %s' -- jams-react-client/package.json 2>/dev/null | head -3
echo
echo "=== состояние package.json на 30.09.2026 ==="
C=$(git rev-list -1 --before=2026-09-30 main 2>/dev/null || git rev-list -1 --before=2026-09-30 HEAD 2>/dev/null)
echo "коммит: $C"
if [ -n "$C" ]; then
  git show "$C:jams-react-client/package.json" 2>/dev/null | grep -E '"(react|@mui/[a-z-]+|@material-ui/[a-z-]+|react-scripts)"' | head -12
fi
echo DONE
