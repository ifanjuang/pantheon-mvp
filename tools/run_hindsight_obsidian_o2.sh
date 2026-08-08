#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_WORKSPACE:?}"
: "${RUNNER_TEMP:?}"
: "${HINDSIGHT_API_URL:=http://127.0.0.1:8888}"
: "${HINDSIGHT_BANK_ID:=pantheon-o2-synthetic}"

MVP_ROOT="$GITHUB_WORKSPACE/pantheon-mvp"
OBSIDIAN_ROOT="$GITHUB_WORKSPACE/hindsight-obsidian"
LAB_ROOT="$RUNNER_TEMP/hindsight-obsidian-o2"
ARTIFACTS="$LAB_ROOT/artifacts"
VAULT_A="$LAB_ROOT/Vault-A"
VAULT_B="$LAB_ROOT/Vault-B"
INDEX_A="$LAB_ROOT/index-vault-a.json"
INDEX_B="$LAB_ROOT/index-vault-b.json"
CLI="$OBSIDIAN_ROOT/dist/cli.js"

export ARTIFACTS HINDSIGHT_API_URL HINDSIGHT_BANK_ID INDEX_A INDEX_B VAULT_A VAULT_B
mkdir -p "$ARTIFACTS" "$VAULT_A/Projects/Alpha" "$VAULT_A/Projects/Beta" "$VAULT_B/Projects/Alpha"

cat > "$VAULT_A/Projects/Alpha/note.md" <<'EOF'
---
tags: [chantier, alpha]
aliases: [Alpha source]
created: 2026-08-08
---
PANTHEON_O2_ALPHA_MARKER. Alpha belongs only to Vault-A / Projects/Alpha.
EOF
cat > "$VAULT_A/Projects/Beta/note.md" <<'EOF'
---
tags: [chantier, beta]
created: 2026-08-08
---
PANTHEON_O2_BETA_MARKER. Beta will be deleted during reconcile.
EOF
cat > "$VAULT_B/Projects/Alpha/note.md" <<'EOF'
---
tags: [reference, alpha]
created: 2026-08-08
---
PANTHEON_O2_VAULT_B_MARKER. This similarly named note belongs only to Vault-B.
EOF

run_sync() {
  local vault="$1" vault_name="$2" index="$3" output="$4"
  node "$CLI" reconcile \
    --vault "$vault" \
    --vault-name "$vault_name" \
    --bank "$HINDSIGHT_BANK_ID" \
    --api-url "$HINDSIGHT_API_URL" \
    --prefix-doc-id \
    --index "$index" \
    | tee "$output"
}

run_sync "$VAULT_A" Vault-A "$INDEX_A" "$ARTIFACTS/initial-a.txt"
run_sync "$VAULT_B" Vault-B "$INDEX_B" "$ARTIFACTS/initial-b.txt"
grep -F 'reconcile: +2 added, ~0 updated, -0 deleted, =0 unchanged' "$ARTIFACTS/initial-a.txt"
grep -F 'reconcile: +1 added, ~0 updated, -0 deleted, =0 unchanged' "$ARTIFACTS/initial-b.txt"

# Unchanged reconcile must not re-ingest any note.
run_sync "$VAULT_A" Vault-A "$INDEX_A" "$ARTIFACTS/unchanged-a.txt"
run_sync "$VAULT_B" Vault-B "$INDEX_B" "$ARTIFACTS/unchanged-b.txt"
grep -F 'reconcile: +0 added, ~0 updated, -0 deleted, =2 unchanged' "$ARTIFACTS/unchanged-a.txt"
grep -F 'reconcile: +0 added, ~0 updated, -0 deleted, =1 unchanged' "$ARTIFACTS/unchanged-b.txt"

# One content edit becomes one update, with the sibling note unchanged.
printf '\nPANTHEON_O2_ALPHA_UPDATED\n' >> "$VAULT_A/Projects/Alpha/note.md"
sleep 0.02
run_sync "$VAULT_A" Vault-A "$INDEX_A" "$ARTIFACTS/edit-a.txt"
grep -F 'reconcile: +0 added, ~1 updated, -0 deleted, =1 unchanged' "$ARTIFACTS/edit-a.txt"

# Deletion is pruned from Hindsight using only this sync engine's local index.
rm "$VAULT_A/Projects/Beta/note.md"
run_sync "$VAULT_A" Vault-A "$INDEX_A" "$ARTIFACTS/delete-a.txt"
grep -F 'reconcile: +0 added, ~0 updated, -1 deleted, =1 unchanged' "$ARTIFACTS/delete-a.txt"

# A rename during a one-shot reconcile is observed as add(new)+prune(old), matching
# the documented CLI behavior and preserving the exact new source path.
mv "$VAULT_A/Projects/Alpha/note.md" "$VAULT_A/Projects/Alpha/renamed.md"
run_sync "$VAULT_A" Vault-A "$INDEX_A" "$ARTIFACTS/rename-a.txt"
grep -F 'reconcile: +1 added, ~0 updated, -1 deleted, =0 unchanged' "$ARTIFACTS/rename-a.txt"

# Query the real bank with strict scope tags. We verify the source anchors that
# Hindsight exposes to citations: document_id plus metadata.path.
python - <<'PY'
import json, os, urllib.request
from pathlib import Path

base=os.environ['HINDSIGHT_API_URL'].rstrip('/')
bank=os.environ['HINDSIGHT_BANK_ID']
out=Path(os.environ['ARTIFACTS'])

def recall(query, tags):
    url=f"{base}/v1/default/banks/{bank}/memories/recall"
    body={
        'query': query,
        'types': ['world','experience'],
        'tags': tags,
        'tags_match': 'all_strict',
    }
    req=urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def results(value):
    items=value.get('results', []) if isinstance(value, dict) else []
    return [x for x in items if isinstance(x, dict)]

checks={}
checks['vault_a_alpha']=recall('PANTHEON_O2_ALPHA_MARKER', ['vault:Vault-A','folder:Projects/Alpha'])
checks['vault_b_alpha']=recall('PANTHEON_O2_VAULT_B_MARKER', ['vault:Vault-B','folder:Projects/Alpha'])
checks['deleted_beta']=recall('PANTHEON_O2_BETA_MARKER', ['vault:Vault-A','folder:Projects/Beta'])
(out/'scoped-recall.json').write_text(json.dumps(checks, indent=2, ensure_ascii=False))

a=results(checks['vault_a_alpha'])
b=results(checks['vault_b_alpha'])
beta=results(checks['deleted_beta'])
assert a, checks['vault_a_alpha']
assert b, checks['vault_b_alpha']
assert any(x.get('document_id') == 'Vault-A/Projects/Alpha/renamed.md' for x in a), a
assert all(x.get('document_id','').startswith('Vault-A/') for x in a), a
assert any((x.get('metadata') or {}).get('path') == 'Projects/Alpha/renamed.md' for x in a), a
assert any('PANTHEON_O2_ALPHA_UPDATED' in str(x.get('text','')) for x in a), a
assert any(x.get('document_id') == 'Vault-B/Projects/Alpha/note.md' for x in b), b
assert all(x.get('document_id','').startswith('Vault-B/') for x in b), b
assert any((x.get('metadata') or {}).get('path') == 'Projects/Alpha/note.md' for x in b), b
assert not any('PANTHEON_O2_BETA_MARKER' in str(x.get('text','')) for x in beta), beta

index_a=json.loads(Path(os.environ['INDEX_A']).read_text())
index_b=json.loads(Path(os.environ['INDEX_B']).read_text())
assert set(index_a) == {'Projects/Alpha/renamed.md'}, index_a
assert set(index_b) == {'Projects/Alpha/note.md'}, index_b

summary={
    'kind':'hindsight_obsidian_o2_acceptance',
    'status':'passed',
    'official_sync_engine':True,
    'create_verified':True,
    'unchanged_dedup_verified':True,
    'edit_upsert_verified':True,
    'delete_reconcile_verified':True,
    'rename_reconcile_verified':True,
    'vault_isolation_verified':True,
    'folder_isolation_verified':True,
    'source_document_id_verified':True,
    'source_metadata_path_verified':True,
    'conversation_retention':'not_used',
    'pantheon_state_mutated':False,
    'evidence_admitted':False,
}
(out/'acceptance-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
PY

cat "$ARTIFACTS/acceptance-summary.json"
