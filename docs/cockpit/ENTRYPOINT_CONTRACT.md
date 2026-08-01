# Entrypoint contract

`index.html` loads `cockpit_bootstrap.js`. Live mode delegates to `live_bootstrap.js`, which installs `live_collection_adapter.js` before the live renderer. `shell_controls.js` owns only shell interactions.

Generation-prefixed entrypoint filenames are retired. Functional `v2-*` DOM identifiers are not presentation APIs and remain temporarily until every consumer is migrated together.
