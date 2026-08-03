# Hermes scoped context connection to EntityRef

Date: 2026-08-03

Status: implementation note — non-authoritative.

## Verified overlap

The immutable Context Pack reader previously repeated the same stable identity operations as the shared primitive:

- trim `entity_type` and `entity_id`;
- reject missing dimensions;
- deduplicate by `(entity_type, entity_id)` while preserving order;
- serialize the admitted identity as the existing dictionary shape.

These operations are now delegated to `EntityRef` and `unique_entity_refs`.

## Domain behavior retained

`hermes_scoped_context` remains responsible for:

- resolving the exact execution admission and run;
- requiring the run to be `running`;
- verifying immutable Task Contract and Context Pack identities;
- requiring at least one admitted entity;
- refusing any identity outside the exact Context Pack;
- deciding which entity types are materializable;
- re-reading current owner records;
- applying reviewed field projections;
- bounding rich text;
- keeping source dereference, global search, listing and writes unavailable.

The historical domain errors are preserved:

```text
stored Context Pack contains an invalid entity reference
stored Context Pack contains an incomplete entity reference
stored Context Pack contains no admitted entity
requested entity is outside the exact admitted Context Pack
```

## Non-equivalences

```text
valid EntityRef != admitted Context Pack membership
admitted membership != materializable entity
materialized current owner read != admission-time snapshot
Context Pack inclusion != Evidence
runtime success != Evidence
read access != write authority
```

## Compatibility

The manifest and entity response payloads continue to expose dictionary-shaped `entity_ref` values. `EntityRef` is internal representation only and does not become an authorization or persistence model.
