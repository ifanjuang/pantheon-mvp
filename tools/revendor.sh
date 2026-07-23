#!/usr/bin/env bash
# Re-vendor the governance schemas from Pantheon-Next at a given commit.
#
# One command to refresh mvp_vertical/vendor/pantheon/ from upstream and record
# the new pin. Re-vendoring is a REVIEWED change, never automatic: after running
# this, review the diff, re-check the derived decision vocabulary, and run the
# tests + the drift monitor before committing.
#
# Usage:
#   tools/revendor.sh <commit-sha>
#
# It fetches only the files listed below (schemas/<name>). It does NOT touch
# decision_vocabulary.stand_in.yaml — that file is DERIVED from the schema's
# $defs.decision_value enum and is re-synced by hand when the enum changes;
# tools/check_schema_drift.py will tell you if it drifted.
set -euo pipefail

SHA="${1:-}"
if [[ -z "$SHA" ]]; then
  echo "usage: tools/revendor.sh <commit-sha>" >&2
  exit 2
fi

REPO="ifanjuang/Pantheon-Next"
RAW="https://raw.githubusercontent.com/${REPO}/${SHA}/schemas"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="${HERE}/mvp_vertical/vendor/pantheon"

# The schemas this repo pins. Keep this list == the *.schema.yaml in VENDOR/.
SCHEMAS=(
  "mvp_governed_loop_objects.schema.yaml"
  "document_knowledge_slice.schema.yaml"
  "work_issue_slice.schema.yaml"
)

echo "Re-vendoring from ${REPO}@${SHA}"
for name in "${SCHEMAS[@]}"; do
  echo "  fetch schemas/${name}"
  curl -fsSL "${RAW}/${name}" -o "${VENDOR}/${name}"
done

printf '%s\n' "$SHA" > "${VENDOR}/UPSTREAM_COMMIT"
echo "Pinned UPSTREAM_COMMIT -> ${SHA}"

echo
echo "Next steps (not automated — this is a reviewed change):"
echo "  1. git diff mvp_vertical/vendor/pantheon/   # inspect what moved"
echo "  2. re-sync decision_vocabulary.stand_in.yaml if \$defs.decision_value changed"
echo "  3. python tools/check_schema_drift.py        # should report COHERENT"
echo "  4. pytest -q                                 # reconcile any emitted-shape changes"
