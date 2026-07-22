# Static cockpit demo

Status: implemented external demo artifact — not deployed, not adopted, not production-authorized.

`demo.html` loads the canonical cockpit stylesheet and renderer scripts directly from this directory:

```text
styles/index.css
app.js
resources.js
effects.js
knowledge_updates.js
```

`demo.js` supplies synthetic project projections and intercepts only `/v1/` requests. It performs no network request for demo data, persists nothing and refuses Knowledge update preview/apply calls and any other non-explicit mutation.

The runtime serves the page at `/cockpit/demo.html` when the external MVP service is installed and started. This repository does not claim that a public deployment exists.

```text
static demo != deployed service
synthetic fixture != professional source
preview != applied effect
runtime success != Evidence
```
