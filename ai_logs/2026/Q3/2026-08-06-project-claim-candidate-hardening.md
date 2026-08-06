# ProjectClaim candidate transition hardening

Date: 2026-08-06
Status: implementation candidate under review; automated validation pending
Scope: pantheon-mvp tranche F only

## Objective

Harden the existing transition without adding another authority:

```text
Execution Result project_claim_candidate
→ human accepted_for_claim disposition
→ separate append-only ProjectClaim
```

The Execution Result remains immutable and non-authoritative. The Claim remains a
separate Agency Data record. No Evidence, Decision, WorkIssue, Project mutation,
memory promotion or external effect is inferred.

## Observed defects

Review found six concrete gaps in the first implementation candidate:

1. the disposition route used the read key although recording a review is a
   consequential write;
2. `accepted_for_claim` could be recorded for a non-Claim result or by a system
   reviewer at the persistence owner;
3. two concurrent Claim creations could both pass the replay lookup before the
   unique index arbitrated them;
4. a later review could race Claim creation without a single order between the
   two append-only events;
5. expanded CHECK constraints and provenance foreign keys could remain
   `NOT VALID`, and one migration guard identified a constraint by broad text
   rather than by its owner name;
6. a direct SQL insert could cite the accepted candidate while changing the
   Project, claim type, value, unit, dates or supporting basis.

These were implementation defects, not reasons to introduce a Derivation,
Consequence or parallel Claim model.

## Corrections

- review disposition writes now require the editor key and an explicit human
  actor;
- the Execution Result owner admits `accepted_for_claim` only for a
  `project_claim_candidate` reviewed by a human;
- Python and SQL share the immutable result-row lock, establishing one order
  between review and Claim creation;
- Claim replay is checked after the lock with a fresh READ COMMITTED statement;
- migration constraints are found by exact owner name and validated when their
  catalog state is not validated;
- the SQL Claim trigger verifies the exact execution/result/review identity,
  Project scope, candidate kind, claim type, value, unit, observation/effective
  dates and selected basis reference;
- the first implementation remains bounded to Project and Information backing
  resolution while the upstream semantic schema stays open.

## Validation added

The branch now covers:

- read key refusal on the review route;
- system and wrong-kind `accepted_for_claim` refusal;
- absence of Claim creation without the latest human acceptance;
- deterministic replay under concurrent Claim creation;
- serialization of a later review against in-flight Claim creation;
- exact migration constraint presence, validation and replay;
- direct SQL refusal for false acceptance, changed candidate value and backing
  outside the candidate basis;
- acceptance of one exact, fully matching reviewed candidate identity.

## Boundaries retained

```text
candidate stored != ProjectClaim created
accepted_for_claim != Decision
ProjectClaim created != Evidence admitted
runtime success != professional validation
certainty != status
observed_at != effective_at
read access != review authority
Project cache != Claim authority
```

No generic reasoning graph, scheduler, queue, runtime, automatic approval or
memory path is added.

## Verification status

Static repository review is complete for this hardening pass. The pull request
workflows have not run on the current head because GitHub requires manual
approval for the automation-created workflow runs. No passing CI claim is made
until those required jobs execute successfully.
