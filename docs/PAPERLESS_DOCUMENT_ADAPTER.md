# Paperless-ngx document adapter

Status: external executable candidate — implemented in this repository / not connected or adopted.

This adapter implements the bounded Paperless-ngx API surface required by the Pantheon document-source candidate defined in Pantheon Next PR #467.

```text
Paperless-ngx     stores source bytes, versions and operational metadata.
Docling           derives structured Markdown/JSON when selected.
Hermes            orchestrates analysis and candidate classification.
Pantheon          governs scope, gates, status, Evidence and Knowledge boundaries.
Cockpit/OpenWebUI exposes reviewed projections.
Human             approves consequential writes and activation.
```

## Implemented

`mvp_vertical.paperless.PaperlessClient` provides:

- authenticated document list and full-text search;
- document and metadata reads;
- exact-version original/preview download;
- immutable `PaperlessSourceCapture` material with SHA-256 and a stable `paperless://` storage reference;
- temporary local materialization for Docling/OCR without treating the temporary path as canonical;
- document upload and task observation;
- an allowlisted metadata update surface for classification mirrors;
- `governed_post_document` and `governed_update_document_metadata`, which route external writes through the existing Pantheon policy chokepoint.

The adapter requires an exact Paperless `version_id` before creating a governed Source Capture. Browsing "latest" may be useful to a human, but it is not sufficient provenance for immutable intake.

## Runtime configuration

The runtime reads:

```text
PAPERLESS_API_URL
PAPERLESS_API_TOKEN
PAPERLESS_API_TIMEOUT
```

The API token is an external runtime secret. It must not be committed, returned to the browser, stored in Pantheon governance records or copied into an Evidence Pack.

The optional `paperless` Docker Compose profile provides a local executable candidate using:

```text
paperless
paperless-db
paperless-broker
```

The Paperless image has no default. The operator must supply a reviewed pinned tag or digest through `PAPERLESS_IMAGE`. Database and application secrets are also required externally.

Example candidate invocation:

```bash
export PAPERLESS_IMAGE='ghcr.io/paperless-ngx/paperless-ngx:<reviewed-pin>'
export PAPERLESS_DB_PASSWORD='<external-secret>'
export PAPERLESS_SECRET_KEY='<external-secret>'
docker compose --profile paperless up -d paperless
```

This is an operator action. The repository does not run it automatically.

## Source identity

One exact external version is represented as:

```text
paperless document id
+ exact version id
+ original filename
+ byte size
+ media type
+ sha256
+ paperless://document/<id>/version/<version>
+ Task-Contract-safe relative source_ref
```

Example:

```text
paperless://document/42/version/7
paperless/42/versions/7/Lieurey-DCE-CCTP.pdf
```

The relative `source_ref` is suitable for declaration in the existing Task Contract without weakening its absolute-path or traversal guards. The mapping to the external Paperless identity remains adapter data, not a filesystem claim.

## Classification

Hermes may produce a Classification Candidate such as:

```text
project = Lieurey
phase = DCE
document_type = CCTP
subject = charpente
knowledge_publication = no
```

After the required Pantheon policy check and human decision, selected operational mirrors may be written to allowlisted Paperless fields:

```text
title
correspondent
document_type
storage_path
tags
archive_serial_number
custom_fields
```

The adapter refuses arbitrary document fields such as `content`, permission rewrites or file replacement through this metadata method.

```text
Paperless metadata != canonical business classification
Paperless OCR != source truth
Paperless task success != professional validation
```

## Paperless internals

Paperless may use its own PostgreSQL database, Valkey broker, workers and scheduler. Those are Paperless implementation details.

They are not:

```text
Pantheon queue
Pantheon scheduler
Hermes queue
Hermes workflow engine
Evidence
approval
```

The adapter observes Paperless task state through the documented `/api/tasks/` API; it does not reimplement Paperless workers or scheduling.

## AI and remote processing posture

The initial candidate does not configure Paperless AI/LLM/vector features or remote OCR. Their absence from this adapter is deliberate. Enabling any external model/provider or remote OCR path requires a separate capability review covering data exposure, provider identity, scope and approval.

Local Paperless OCR remains derived processing. Docling remains the preferred Pantheon candidate for structured document analysis.

## Current status

```text
adapter code                 implemented
unit tests                   implemented
optional compose profile     implemented as external candidate
live Paperless connection    not established
Cockpit projection           not connected by this change
Hermes skill                 not connected by this change
installation on target host  not established
health on target host        not established
adoption                     not decided
activation                   not authorized
production / real dossier    forbidden pending separate review
```
