# Governance Status

Status: external executable candidate — implemented and tested / not adopted.

This repository is not Pantheon Next.

It is an external executable candidate intended to host the MVP vertical slice and bounded runtime adapters for governed task-loop testing.

## Boundary

```text
executed_by: this external repository and Hermes, only when explicitly installed/run
exposed_by: terminal decision stand-in, read-only OpenWebUI Document Card, Paperless Source Inbox and Document Runtime Status candidates, mobile Knowledge editor candidate; not installed
governed_by: Pantheon Next doctrine and adoption gates
approved_by: human decision reference only; authenticated issuer remains to verify
forbidden: self-approval, external send bypass, memory promotion, provider routing by Pantheon, scheduling by Pantheon, unrestricted source access
```

## Current status

```text
implementation_status: blocks_1_2_3_plus_work_issues_and_document_vertical_complete_as_candidates
# The executable candidate remains aligned to the vendored Pantheon governed-loop
# schema at UPSTREAM_COMMIT f8bc3bde142d1e105b7c9a966d8e0d62b39918c4.
# The offline drift guard keeps this cited pin equal to
# mvp_vertical/vendor/pantheon/UPSTREAM_COMMIT; newer upstream commits are a
# separate drift signal and do not silently change this executable contract.
binding_status: candidate
installation_status: not installed by Pantheon Next
activation_status: not activated
health_status: acceptance_tests_pass    # test_pass != adoption
ci_status: green_on_main                # branch CI reported separately when run
production_status: forbidden
knowledge_publication_status: candidate_implemented_and_schema_validated
mobile_editor_status: candidate_implemented_not_installed
hermes_intelligent_edit_binding: polling_seam_implemented_not_connected

policy_chokepoint_seam: implemented_not_connected
# policy_gate normalizes runtime effects to the Pantheon request+gate_signals HTTP
# contract, fails closed and binds decision validation to PEP-derived effect facts
# when a new adapter supplies decision_expectation. No live PDP round-trip is
# proven by repository tests alone.

policy_client_http: implemented_not_connected
# real HTTP client for Pantheon PDP; transport exists, target deployment unknown.

capability_management_slice: implemented_not_connected
# bounded lifecycle seam; native executor remains external.

paperless_document_adapter: implemented_not_deployed
# read/search, exact-version Source Capture, existing Document->Knowledge intake,
# upload/task observation and allowlisted metadata primitives.

paperless_gateway: implemented_not_deployed
# server-side read projection plus Hermes-only governed Project Document intake
# and metadata mirror mutation. Exact source, Task Contract scope, effect identity
# and digest are bound before the write executor can run.

paperless_source_inbox: implemented_not_installed
# read-only OpenWebUI source discovery/inspection and exact-capture display.

document_runtime_status: implemented_read_only_not_installed
# OpenWebUI card reads only the bounded gateway health projection. It reports
# Paperless reachability separately from health/safety and leaves Hermes skill,
# Pantheon PDP and Docling status as not_observed unless their own observation
# source is connected. It changes no activation or authority state.

paperless_runtime_profile: implemented_candidate_not_installed
# Paperless + dedicated DB + internal broker + bounded gateway; external secrets
# and a reviewed pinned Paperless image are required before an operator can run it.

hermes_pantheon_document_intake_skill: implemented_candidate_not_installed
# AgentSkills-compatible SKILL.md + transport-only Python client. The client sees
# only the Hermes gateway key, never Paperless or Pantheon policy secrets. It
# supports read/search/capture/task, governed intake and governed metadata mirror.

human_decision_issuer_authentication: not_implemented_or_proven
# PEP binds object/digest/scope/ceiling and PDP validates supplied fields, but the
# current candidate does not cryptographically authenticate the human issuer.
```

None of these Paperless/Hermes statuses establishes a live Paperless instance, target health, installed Hermes skill, live PDP/PEP enforcement, adoption, activation or real-dossier authorization.

## Stand-in rule

Any file occupying another actor's role must declare its status.

```text
runner.py -> explicit Hermes stand-in header (met: stand_in_runner != Hermes Agent)
gate.py   -> terminal_gate_standin.py (met: terminal_gate != OpenWebUI cockpit)
```

The actual `pantheon-document-intake` artifact is a Hermes skill candidate, not a stand-in for Pantheon policy or human approval.

## Required non-equivalence rules

```text
runtime_success != evidence
test_pass != adoption
candidate != approval
retrieved != truth
Knowledge != Evidence
offline replay != overwrite permission
queued edit request != Hermes proposal
source_declared != path_safe
reachable != healthy
healthy != safe
Paperless metadata != canonical business classification
Paperless OCR != source truth
Paperless task success != professional validation
Paperless exact capture != Evidence
validated decision fields != authenticated human issuer
Hermes skill installed != capability approved
runtime observation != activation decision
stand_in_runner != Hermes Agent
terminal_gate != OpenWebUI cockpit
external_repo != Pantheon runtime
```

## Adoption gates

Before adoption, visible review evidence is still required. Existing gates 1–7 are candidate evidence only; Gate 8 remains a human decision.

```text
Task Contract schema alignment               -> met as candidate evidence
source path boundary                         -> met as candidate evidence
fixture-independent drafting seam             -> met as candidate evidence
human gate decision semantics                -> met as candidate evidence
system-signer refusal                        -> met as candidate evidence
external-send refusal                        -> met as candidate evidence
CI result after code push                    -> required for each new branch/PR
live Paperless + PDP + Hermes synthetic path -> OPEN
human decision issuer authentication         -> OPEN / architecture to verify
human approval for activation                -> OPEN
```

## Final rule

```text
This repository may execute an external proof loop.
Pantheon Next governs the status of that loop.
The human decides.
```
