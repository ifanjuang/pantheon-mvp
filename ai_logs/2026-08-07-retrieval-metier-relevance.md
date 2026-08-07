# Retrieval métier relevance cases

Date: 2026-08-07

## Objective

Add a small executable relevance set for the current bounded PostgreSQL retrieval candidate without creating a benchmark platform, changing the engine or claiming production semantic quality.

## Observed implementation

```text
PostgreSQL full-text retrieval with the simple configuration;
pgvector retrieval with the deterministic local feature-hashing embedder;
weighted deterministic RRF;
Task Contract dossier and source filters before ranking;
contract, ingestion, source and structural provenance on returned chunks.
```

The active embedder is intentionally a local placeholder. Therefore the first asserted relevance cases are exact lexical and technical-term cases. Accentless French and semantic paraphrase cases are recorded as observations with known limits, not as a production SLA.

## Change

```text
tests/fixtures/retrieval_metier_cases.yaml
  eight labelled or observation-only métier queries over the existing synthetic dossier;

tests/test_retrieval_metier_relevance.py
  real PostgreSQL lexical and hybrid calls;
  expected source ranking for six exact cases;
  scope and provenance checks for every returned candidate;
  duplicate and deterministic-order checks;
  planted undeclared-source and other-dossier marker checks.
```

## Completion criteria

```text
expected exact-case source at the declared rank;
zero source outside the Task Contract;
contract, ingestion and source provenance retained;
no duplicate fused candidate;
repeatable hybrid ordering.
```

## Boundary

```text
labelled fixture != production benchmark
vector path implemented != semantic quality established
hybrid score != confidence
retrieved != Evidence
test passed != binding adopted
```

No dependency, reranker, embedding provider, PostgreSQL extension, API, Hermes tool, activation, Evidence admission or production-weight change is introduced.

## Verification posture

The available local execution environment could not resolve GitHub and did not provide the repository checkout or PostgreSQL service. No local test pass is claimed. The pull-request CI with its pgvector service is the required executable validation for this branch.
