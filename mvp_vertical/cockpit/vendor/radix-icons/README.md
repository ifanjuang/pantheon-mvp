# Radix Icons — vendored MVP subset

This directory is a pinned, read-only copy of the Radix Icons assets selected for the Pantheon MVP cockpit.

Upstream: `radix-ui/icons`
Upstream commit: `112af91ad275a63c3a29b0da2588342af74ef9bf`
Source directory: `packages/radix-icons/icons/`
License: MIT, Copyright (c) 2022 WorkOS. See `LICENSE`.

## Boundary

These files are presentation assets only.

```text
icon displayed != governed status
healthy icon != safe
check icon != approval
runtime success != evidence
```

Pantheon governs the semantic meaning exposed by the Cockpit. The Cockpit renders these assets. Hermes does not execute them. Human decisions remain explicit records rather than icon states.

## Snapshot policy

The copy is deliberately limited to the icons used or immediately required by the MVP cockpit instead of importing the Radix monorepo, build tooling, CI or package-management files. Files retain their upstream names and SVG contents. Adding or updating an icon is a reviewed re-vendoring change; an upstream update is not automatically authorized.

Current selection covers the existing Cockpit concepts: document, knowledge, work, questionnaire, source, review, scope, memory, history, decision, Hermes/runtime indication, comment, project, evidence and gate.

This vendored snapshot is not itself an npm installation and does not activate any runtime capability.