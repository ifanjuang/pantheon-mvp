# Governance Status

Status: external executable candidate — implemented and tested / not adopted.

This repository is not Pantheon Next.

It is an external executable candidate intended to host the MVP vertical slice and bounded runtime adapters for governed task-loop testing.

## Boundary

```text
executed_by: this external repository and Hermes, only when explicitly installed/run
exposed_by: terminal decision stand-in, read-only OpenWebUI Document Card, optional Paperless Source Inbox, Document Runtime Status and Document Runtime Live Status candidates, mobile Knowledge editor candidate; not installed
governed_by: Pantheon Next doctrine and adoption gates
approved_by: human decision only; authenticated issuer verification is available when the PDP registry and signed decision path are configured
forbidden: self-approval, external send bypass, memory promotion, provider routing by Pantheon, scheduling by Pantheon, unrestricted source access
```

## Current status

```text
implementation_status: blocks_1_2_3_plus_work_issues_and_document_vertical_complete_as_candidates
binding_status: candidate
installation_status: not installed by Pantheon Next
activation_status: not activated
health_status: acceptance_tests_pass    # test_pass != adoption
ci_status: branch_ci_required_after_code_push
production_status: forbidden
knowledge_publication_status: candidate_implemented_and_schema_validated
mobile_editor_status: candidate_implemented_not_installed
hermes_intelligent_edit_binding: polling_seam_implemented_not_connected

policy_chokepoint_seam: implemented_not_connected
policy_client_http: implemented_not_connected
capability_management_slice: implemented_not_connected
knowledge_update_chokepoint: wired_not_connected
capability_executor_http: implemented_transport_requires_verified_binding
# HermesCapabilityExecutor no longer invents /v1/capabilities:operate as a default.
# A caller must provide an explicitly reviewed native capability-operation endpoint.
# The verified Hermes Runs API is work execution, not install/enable/update semantics.

hermes_runs_api_observer: implemented_candidate_merged_not_connected
hermes_run_launch_reservation: implemented_candidate_merged_not_connected
hermes_runs_external_binding: implemented_candidate_merged_not_connected
hermes_active_context_bridge: implemented_candidate_merged_not_connected
hermes_context_plugin: implemented_candidate_merged_not_installed
hermes_run_launch_junction_ci: green_on_merged_candidate
hermes_live_binding_acceptance: implemented_candidate_not_run
# These merged Hermes Runs/launch/context/live-acceptance slices remain external
# execution candidates. Their existence does not authorize target installation,
# activation, retry, provider routing or real-dossier use.

human_issuer_signing: implemented_not_connected

local_document_ingestion: implemented_candidate_not_deployed
# Governed local/NAS source ingestion remains available without Paperless through
# declared source paths, path-boundary checks, digests, Docling when selected and
# Project Document candidate creation.

document_source_management_slot: optional
preferred_document_source_binding: paperless_ngx
paperless_profile: implemented_optional_not_selected_by_default
# compose.phase-b.yaml places Paperless, its DB/broker and bounded gateway behind
# the `paperless` profile. Their absence is a supported baseline state.

paperless_document_adapter: implemented_optional_not_deployed
paperless_gateway: implemented_optional_not_deployed
paperless_source_inbox: implemented_optional_not_installed

phase_b_portainer_compose: implemented_candidate_not_deployed
# Core Phase B starts without Paperless. `--profile paperless` adds the preferred
# document_source_management binding. Existing OpenWebUI/SearXNG remain external.

document_runtime_network_observer: implemented_candidate_not_deployed
# When Paperless is not selected, it returns binding_status=not_selected and
# reachability/health=not_applicable without probing the gateway.

document_runtime_status: implemented_read_only_not_installed
document_runtime_live_observations: implemented_read_only_not_deployed
synthetic_document_runtime_check: implemented_candidate_not_run
hermes_pantheon_document_intake_skill: implemented_candidate_not_installed
human_decision_issuer_authentication: implementation_available_not_connected
```

None of these statuses establishes target health, installed Hermes skills/plugins, live PDP/PEP enforcement, authenticated target issuer, adopted Runs binding, adoption, activation or real-dossier authorization.

## Required non-equivalence rules

```text
Paperless absent != Pantheon degraded
Paperless absent != document ingestion unavailable
Paperless installed != Paperless binding selected
Paperless binding selected != activated
runtime_success != evidence
test_pass != adoption
candidate != approval
retrieved != truth
Knowledge != Evidence
source_declared != path_safe
reachable != healthy
healthy != safe
Runs API available != run authorized
toolset configured != toolset approved
Hermes API observation != runtime execution
launch reservation != dispatch
launch reservation != Hermes run
session_id correlation != memory promotion
plugin installed != approved
plugin enabled != activated
Paperless metadata != canonical business classification
Paperless OCR != source truth
Paperless task success != professional validation
Paperless exact capture != Evidence
unsigned_or_asserted_decision_fields != authenticated_human_issuer
issuer_authenticated != approval
Hermes skill installed != capability approved
Hermes /v1/skills listing != task authorization
runtime observation != activation decision
synthetic check pass != production adoption
live binding acceptance pass != production adoption
compose present != target deployed
external_repo != Pantheon runtime
```

## Adoption gates

```text
Task Contract schema alignment               -> met as candidate evidence
source path boundary                         -> met as candidate evidence
local/NAS document ingestion                 -> implemented candidate / live proof OPEN
Hermes Runs API observation                  -> implementation merged / live target proof OPEN
reviewed restricted Hermes tool surface      -> OPEN / deployment-owned
Hermes launch reservation + snapshot         -> implementation merged / live target proof OPEN
Hermes external /v1/runs binding             -> implementation merged / live target proof OPEN
Hermes context plugin                        -> implementation merged / install + live target proof OPEN
Hermes live acceptance helper                -> implemented / target run OPEN
network-native Hermes skill observation      -> implemented candidate / live proof OPEN
Phase B core composition                     -> implemented candidate / live deployment OPEN
optional Paperless profile                   -> implemented candidate / selection optional
Paperless synthetic path                     -> applies only when Paperless binding selected
target issuer registry + signed decision     -> OPEN / implementation available, live proof absent
human approval for activation                -> OPEN
```

## Final rule

```text
This repository may execute an external proof loop.
Paperless is an optional source-management binding, not a prerequisite for document ingestion.
Pantheon Next governs the status of that loop.
The human decides.
```
