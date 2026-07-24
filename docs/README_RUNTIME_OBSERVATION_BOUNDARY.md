# Runtime observation boundary

Status: support note — implemented candidate surfaces / not deployed.

This tranche intentionally keeps observation separate from governance conclusions.

```text
observation source -> technical fact candidate
technical fact candidate != safety
technical fact candidate != approval
technical fact candidate != activation
technical receipt != Evidence
```

The observer never writes to Pantheon governance state. The Cockpit may display the result; Pantheon governance decides whether a later human-reviewed gate can rely on that result.
