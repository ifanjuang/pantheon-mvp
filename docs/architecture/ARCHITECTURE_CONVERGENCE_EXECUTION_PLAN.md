# Pantheon architecture convergence execution plan

Status: active working implementation plan — non-authoritative, non-runtime, removable after completion.

Date: 2026-08-02

Canonical governance remains in `Pantheon-Next`. This document owns only the implementation sequence for `pantheon-mvp` and the coordinated cross-repository cleanup.

Primary references:

```text
Pantheon-Next/docs/governance/ROADMAP.md
Pantheon-Next/docs/governance/authority/PANTHEON_SYSTEM_OWNERSHIP_REGISTRY.json
Pantheon-Next/ai_logs/2026-08-02-architecture-convergence-plan.md
docs/architecture/PANTHEON_CROSS_REPOSITORY_AUDIT.md
```

## 1. Purpose

Converge the existing implementation before adding more layers.

The program must:

- remove active generation-named modules, routes, schemas, tests and projections;
- eliminate competing implementation paths and obsolete compatibility surfaces;
- identify and remove proven dead code;
- place doctrine, implementation, runtime behavior and projection in their correct repositories;
- make `pantheon-mvp` easier to extend with new governed rules;
- improve startup, request, database and Cockpit performance from measured baselines;
- preserve Evidence, approval, scope, task authorization and human-decision boundaries.

The target is not fewer files at any cost. The target is one clear owner and one canonical path for each responsibility.

```text
one governed concept
-> one semantic owner
-> one canonical implementation path
-> replaceable adapters
-> simple projections
```

## 2. Current baseline

The calibrated cross-repository audit is already merged and executable. The previous reliable run identified:

- no demonstrated P0 authority conflict;
- active generation-named identities and paths;
- internal routes using generation prefixes;
- one governance document located in the implementation repository;
- Python modules without a statically detected consumer;
- vendored schemas that must remain references with drift detection rather than being treated as ordinary duplicates.

The baseline must be regenerated because the contradictory-review doctrine, compiler, persistence and API slices were merged after the previous report.

### Current open-PR gate

`pantheon-mvp#163` is draft and currently declares new contradictory-review routes under `/v1`.

It must not merge in that form.

Permitted resolutions:

1. rename the routes to stable responsibility-based paths inside #163; or
2. keep #163 draft until the route-migration tranche establishes the canonical project-review route family.

A compatibility alias must not be added merely to allow the PR to merge.

## 3. Permanent boundaries

```text
Pantheon-Next
-> semantic governance, schemas, states, gates, Evidence, scope and approvals

pantheon-mvp
-> PostgreSQL, APIs, application services, projections and bounded adapters

Hermes / external runtime
-> task execution, tools, provider routing and runtime-local state

Cockpit / OpenWebUI
-> interaction, display and human-decision surfaces

Human
-> consequential decision
```

Every tranche must preserve:

```text
semantic owner != implementation owner
implementation owner != runtime owner
projection owner != authorization authority
installed != approved
healthy != safe
runtime_success != Evidence
retrieved != truth
binding_selected != dependency_adopted
activated != task_authorized
UI status != authorization
```

## 4. Modularity target

The implementation must become modular in two distinct senses.

### 4.1 Code modularity

Each module has one reason to change and belongs to one layer:

```text
domain
-> immutable concepts, invariants and state transitions

application
-> commands, queries and deterministic orchestration

api
-> HTTP request/response translation and authentication dependencies

persistence
-> PostgreSQL transactions, repositories and migrations

adapters
-> Hermes, Paperless, Docling, OpenWebUI and other replaceable bindings

projections
-> Cockpit and read-model composition

registries
-> validated declarative definitions and startup indexes

bootstrap
-> configuration and explicit static wiring
```

Dependency direction:

```text
api -> application -> domain
persistence -> domain
adapters -> application/domain contracts
projections -> application query results
bootstrap -> all concrete implementations
```

Forbidden directions:

```text
domain -> FastAPI
 domain -> PostgreSQL
 domain -> Cockpit
 domain -> Hermes client
 adapter -> approval authority
 projection -> semantic state mutation
```

The folder structure is introduced progressively. Empty architectural folders are not created in advance.

### 4.2 Rule modularity

A new governed rule must be integrable without editing unrelated domains or adding another central conditional chain.

Canonical addition path:

```text
1. governed definition in Pantheon-Next
2. stable rule identifier and revision
3. vendored/reference contract in pantheon-mvp when execution requires it
4. pure deterministic evaluator
5. explicit static registration in one composition root
6. typed RuleResult or Observation
7. focused tests
8. optional Cockpit projection
```

The evaluator must:

- accept explicit typed input;
- return a deterministic candidate result;
- avoid network and database access;
- avoid external action;
- avoid Evidence or approval promotion;
- avoid hidden dependency lookup;
- expose unsupported or inconclusive states explicitly.

Example implementation shape:

```python
@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    revision: int
    input_type: str
    result_type: str

class RuleEvaluator(Protocol):
    definition: RuleDefinition

    def evaluate(self, subject: object, context: object) -> object:
        ...

RULE_EVALUATORS = {
    evaluator.definition.rule_id: evaluator,
}
```

`RULE_EVALUATORS` is static application composition, not dynamic plugin discovery.

```text
registry != plugin manager
registered != approved
rule available != task authorized
rule evaluated != action permitted
```

### 4.3 Extension classification

Before implementation, classify every proposed addition:

| Addition | Semantic owner | Implementation location | Expected extension point |
|---|---|---|---|
| Governed rule or status | Pantheon-Next | pure evaluator in `pantheon-mvp` if needed | rule registry |
| Application use case | Pantheon-Next contract | `application/` | command/query handler |
| Persistence | Pantheon-Next data semantics | `persistence/` | repository protocol |
| External integration | Pantheon-Next boundary | `adapters/` | adapter protocol and binding |
| Cockpit display | Pantheon-Next presentation constraints | `projections/` and Cockpit | projection builder |
| Runtime capability | Hermes/external runtime | outside Pantheon | bounded Task Contract and return adapter |

A new permanent concept is rejected until existing Context, Trace, Knowledge, Evidence, Claim, ChangeCandidate, Competence, Governed Resource and Observation concepts have been tested against the need.

## 5. Change-unit rules

Each PR must satisfy all of the following:

- one architectural responsibility;
- one stated semantic owner;
- one explicit list of consumers;
- no hidden state or authorization change;
- audit before and after;
- focused tests plus full CI;
- reversible through one PR revert;
- no permanent compatibility alias;
- no simultaneous broad rename and behavior rewrite;
- no new dependency unless the existing stack cannot perform the work.

A PR that both moves a module and changes its business behavior must be split unless the behavior change is necessary to preserve the existing contract.

## 6. Program sequence

## Stage A — Refresh the baseline

### Objective

Create a trustworthy snapshot after the latest merged work.

### Steps

1. run the cross-repository audit against both current `main` branches;
2. archive Markdown and JSON outputs;
3. generate the Python import graph;
4. enumerate FastAPI routers and mounted routes from the composed applications;
5. enumerate JavaScript inclusion, import, dynamic load, global production/consumption and CSS selector dependencies;
6. record test duration and startup duration;
7. record Cockpit snapshot latency and SQL query count where measurable;
8. compare the result with the previous audit.

### Deliverables

```text
architecture inventory Markdown
architecture inventory JSON
route catalogue
Python dependency graph
Cockpit dependency graph
performance baseline
```

### Entry condition

All intended preceding PRs are merged or explicitly excluded.

### Exit criteria

- every P0–P2 finding has a stable identifier;
- open PRs that add debt are listed;
- baseline metrics are reproducible in CI or a documented local command.

### Rollback

No runtime change. Remove only generated reports if necessary.

## Stage B — Freeze new architectural debt

### Objective

Prevent the codebase from growing new generation-named or compatibility paths while existing debt is removed.

### Steps

1. add a checked baseline for current generation-name findings;
2. fail CI when a PR increases the baseline;
3. detect active internal route prefixes separately from external protocol paths;
4. allow explicit exceptions only for:
   - ordered migrations;
   - source, Information, ChangeCandidate and schema revisions;
   - external protocol versions isolated in adapters;
5. classify `legacy`, `compat`, `deprecated`, `obsolete` and `old` paths;
6. require a removal condition for every retained compatibility path.

### Exit criteria

- new debt cannot merge;
- the baseline can only decrease;
- #163 either uses stable paths or remains draft.

### Rollback

Revert the guard PR. No production behavior is affected.

## Stage C — Remove passive generation names

### Objective

Clean names that do not require a public API migration.

### First target

```text
mvp_vertical/cockpit/v3/materials.json
-> mvp_vertical/cockpit/registries/materials.json
```

Replace the generation identity:

```json
{"schema_version": "cockpit.materials.v1"}
```

with a stable identity and technical revision:

```json
{"schema_id": "cockpit.materials", "revision": 1}
```

### Additional targets

- active tests named after Cockpit generations;
- active docs named after generations where the name no longer represents history;
- active CSS classes or JavaScript globals whose dependency graph is proven;
- package, schema or fixture identities that use generation as architecture.

### Required dependency proof

For Cockpit assets, check:

```text
HTML inclusion
static import
dynamic import
ordered script load
global producer
global consumer
CSS selector usage
test dependency
published regression surface
```

### Exit criteria

- no active file path is named by generation;
- technical revisions remain data, not product identities;
- visual output and behavior remain unchanged.

## Stage D — Correct repository placement

### Objective

Remove semantic authority from the implementation repository.

### Known target

```text
pantheon-mvp/docs/governance/PROFESSIONAL_DUTY_OF_CARE.md
```

### Steps

1. compare it with existing mission/responsibility doctrine in `Pantheon-Next`;
2. merge into an existing owner document when possible;
3. create a new governed document only when no current owner can express the rule;
4. index the resulting authority correctly;
5. replace the MVP copy with a short implementation reference or remove it;
6. rerun the cross-repository duplicate and ownership checks.

### Exit criteria

- one semantic source remains;
- `pantheon-mvp` does not carry competing governance;
- implementation tests point to a pinned or vendored contract where needed.

## Stage E — Remove internal route generation prefixes

### Objective

Use stable responsibility-based API paths without permanent aliases.

### Migration rule

Each domain tranche updates atomically:

```text
server route
-> Python clients
-> JavaScript clients
-> scripts
-> tests
-> examples
-> documentation
```

The old path is removed in the same PR.

### E1 — Read-only MCP HTTP projection

Use as the migration pilot because the surface is bounded and read-only.

Exit criteria:

- stable paths only;
- MCP stdio names remain unchanged unless separately justified;
- no compatibility alias.

### E2 — Agency and Work

Candidate families:

```text
/agency/projects
/agency/claims
/agency/change-candidates
/work/decisions
/projects/{project_id}/contradictory-reviews
/contradictory-reviews/{review_id}
```

The contradictory-review routes in #163 must align in this tranche or before it.

### E3 — Cockpit

Update together:

- Cockpit routers and shell;
- `cockpit_data_loader.js`;
- card actions;
- editors;
- child collection sources;
- static and behavioral tests.

Cockpit registry source names remain abstract projection identifiers and must not become endpoint declarations.

### E4 — Documents and governed resources

Candidate families:

```text
/documents/observations
/documents/network-observations
/resources/paperless
/resources/openwebui
```

Do not collapse installation, health, activation, safety and task authorization into one route status.

### E5 — Hermes

Migrate last because the surface touches admissions, context and returns.

Candidate families:

```text
/hermes/handoffs
/hermes/executions
/hermes/project-change-candidates
```

### Exit criteria for Stage E

- no active internal route begins with a generation prefix;
- no duplicate route family remains;
- clients and tests use only stable paths;
- external protocol versions remain isolated in adapters.

## Stage F — Prove use before deleting modules

### Objective

Classify every apparently unconsumed Python module without guessing.

### Consumer classes

For each suspect module, inspect:

```text
absolute import
relative import
FastAPI include_router
console-script entrypoint
python -m entrypoint
Docker CMD or entrypoint
shell invocation
dynamic import
path-based invocation
test import
Hermes skill or tool invocation
migration loader
framework reflection
```

### Decision record

Each module receives one decision:

```text
retain
simplify
merge
move
remove
```

Required evidence for removal:

- no consumer in any class above;
- no deployment reference;
- no documented compatibility obligation;
- no vendored-reference role;
- full tests remain green after deletion.

### Exit criteria

No module remains labelled merely “possibly unused”.

## Stage G — Consolidate shared primitives

### Objective

Stop redefining the same technical concepts across domains.

Candidate primitives:

```text
EntityRef
SourceRef
ActorRef
Provenance
Revision
Observation
Pagination
ApplicationError
IdempotencyKey
ExpectedRevision
```

### Rules

- domain-specific data stays domain-specific;
- HTTP models do not become domain models;
- a primitive is introduced only after at least two genuine compatible uses are demonstrated;
- generic repositories or universal base classes are prohibited unless they remove real repeated behavior;
- semantic status enums remain governed by their owning concept.

### Exit criteria

- one internal representation per accepted primitive;
- no circular imports introduced;
- no loss of domain meaning through over-generalization.

## Stage H — Establish modular domain boundaries

### Objective

Move from historical vertical slices toward a modular monolith without a big-bang rewrite.

### Initial target shape

```text
pantheon_mvp/
  domain/
  application/
  api/
  persistence/
  adapters/
  projections/
  registries/
  bootstrap/
```

### Migration method

For one domain at a time:

1. identify its current API, persistence, service and projection files;
2. define its domain contract without moving behavior;
3. move deterministic behavior first;
4. move persistence behind a protocol;
5. reduce the router to translation and dependency calls;
6. wire concrete implementations in one composition root;
7. remove the former path immediately after consumers migrate.

### Composition-root rule

Application wiring belongs in explicit bootstrap modules such as:

```text
bootstrap/cockpit.py
bootstrap/documents.py
bootstrap/hermes.py
```

Composition modules may instantiate and register components. They must not contain domain decisions.

### Exit criteria

- dependency direction is testable;
- domains do not import routers or concrete adapters;
- a new rule can be registered without editing unrelated modules.

## Stage I — Consolidate Hermes boundaries

### Objective

Reduce historical fragmentation while keeping execution outside Pantheon.

### Canonical use cases

```text
admission
launch preparation
context access
return capture
human reconciliation
```

### Target split

```text
domain/hermes
-> immutable identities, states and invariants

application/hermes
-> admission, preparation, context and return use cases

adapters/hermes
-> transport client and runtime observations

api/hermes
-> HTTP translation only
```

### Forbidden ownership

Pantheon must not implement:

- scheduling;
- queues;
- provider routing;
- autonomous retries;
- tool selection;
- runtime memory;
- execution approval by runtime success.

### Exit criteria

- one canonical chain from admission to result candidate;
- no duplicated validation across routers and adapters;
- runtime transport is replaceable;
- result capture remains candidate-only.

## Stage J — Normalize observations and governed resources

### Objective

Replace multiple status families with one observation envelope while preserving distinct dimensions.

Candidate envelope:

```python
@dataclass(frozen=True)
class Observation:
    subject: EntityRef
    dimension: str
    status: str
    observed_at: datetime
    source: SourceRef
    details: Mapping[str, object]
```

Dimensions may include:

```text
installation
reachability
health
native_state
update
activation
governance
task_authorization
compatibility
```

Adapters produce observations. Application queries compose them. Cockpit projects them.

### Exit criteria

- Paperless, Docling, Hermes and OpenWebUI observations share one envelope;
- no status dimension implies another;
- Governed Resource projections do not own semantic truth.

## Stage K — Performance optimization

### Objective

Improve measured behavior only after canonical paths are established.

### Measures

Record before and after:

- application startup duration;
- registry loading duration;
- Cockpit snapshot latency;
- SQL query count per major endpoint;
- p50 and p95 endpoint duration in controlled tests;
- full test-suite duration;
- memory footprint of the Cockpit initial payload;
- document-list and run-list pagination behavior.

### Candidate optimizations

1. validate and compile registries once at startup;
2. publish immutable in-memory indexes atomically;
3. share one HTTP client and connection pool per adapter;
4. keep network calls outside PostgreSQL transactions;
5. use short reserve/record transactions around external effects;
6. batch related reads and remove N+1 queries;
7. create bounded read projections for Cockpit snapshots;
8. paginate documents, chunks, runs, observations and ChangeCandidates;
9. remove repeated full-payload validation between trusted internal layers;
10. retain invariant checks at entry and effect boundaries.

### Exit criteria

- each optimization has a measured gain or documented correctness benefit;
- no cache becomes an authorization or truth source;
- no performance work reintroduces duplicate data ownership.

## Stage L — Close the convergence program

### Objective

Remove temporary controls and leave a stable maintenance model.

### Steps

1. rerun the full cross-repository audit;
2. review every remaining finding;
3. require zero unreviewed P0, P1 and P2 findings;
4. reduce the temporary debt baseline to zero;
5. remove baseline exceptions no longer needed;
6. update the architecture inventory and developer documentation;
7. record final metrics;
8. close or remove temporary working plans according to repository cleanup rules.

### Final exit criteria

```text
no active generation-named architecture
no internal generation-prefixed routes
one semantic owner per governed concept
one canonical implementation path per responsibility
no unclassified suspected dead code
replaceable adapters
static reviewable composition
new rule integration limited to definition + evaluator + registration + tests + optional projection
```

## 7. Planned PR sequence

```text
A  refresh architecture and performance baseline
B  freeze new versioned identities and route debt
C  remove passive generation-named Cockpit paths and identities
D  move misplaced governance material
E  migrate read-only MCP HTTP routes
F  migrate Agency, Work and contradictory-review routes
G  migrate Cockpit routes and clients
H  migrate Documents and governed-resource routes
I  migrate Hermes routes
J  classify and remove proven dead modules
K  consolidate accepted shared primitives
L  establish domain modules and composition roots
M  consolidate Hermes application seams
N  normalize observations and governed-resource projections
O  optimize PostgreSQL, API and Cockpit performance
P  close the audit baseline and temporary plan
```

The letters express order only. They are not architecture generations or permanent identifiers.

## 8. Rule-addition checklist after convergence

A new rule is ready for implementation only when all answers are explicit:

1. Which existing Pantheon concept owns the rule?
2. Is a new concept genuinely required?
3. What is the stable rule identifier?
4. What revision changed and why?
5. What exact input does the evaluator accept?
6. What typed candidate result does it return?
7. Can the evaluator run deterministically without I/O?
8. Where is it statically registered?
9. Which use case invokes it?
10. Which human or gate remains authoritative?
11. Does Cockpit only project the result?
12. Which tests prove unsupported, inconclusive and rejected states?
13. Which adapter is optional and replaceable?
14. Does the addition create any scheduler, queue, provider router, plugin manager, memory engine or automatic approval behavior?

Failure to answer one item blocks implementation or sends the proposal back to architecture review.

## 9. Definition of done for each PR

```text
scope documented
canonical owner identified
consumers enumerated
focused tests green
full CI green
audit finding reduced or intentionally classified
no new generation identity
no hidden compatibility path
no authority boundary regression
rollback documented
```

## 10. Non-goals

This plan does not authorize:

- microservices;
- event-bus adoption;
- a framework-driven CQRS implementation;
- a dynamic plugin system;
- runtime tool installation;
- provider selection;
- automatic retries or scheduling;
- memory promotion;
- automatic Evidence admission;
- automatic approval;
- broad ontology expansion.

The intended result is a disciplined modular monolith, not a new platform layer.