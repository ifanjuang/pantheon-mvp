# PR scope — Document runtime live observations

Status: implementation note.

This branch is stacked on `agent/document-runtime-status` and adds only:

- source-attributed read-only observations for Paperless, Pantheon PDP, Docling and optional native Hermes inventory;
- an OpenWebUI read-only projection over those observations;
- an operator-run synthetic acceptance helper whose default mode is read-only;
- tests and documentation of non-equivalence boundaries.

It does not install, deploy, activate, update or restart any runtime and does not authorize real-dossier use.
