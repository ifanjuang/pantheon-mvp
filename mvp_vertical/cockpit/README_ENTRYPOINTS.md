# Cockpit entrypoints

The canonical browser entrypoint is `cockpit_bootstrap.js`.

Live mode continues through `live_bootstrap.js`, which loads `live_collection_adapter.js` before the live schema renderer so the collection boundary exists before cards are presented.

`shell_controls.js` owns only menu and Hermès shell interactions.

Historical generation names are not part of the public contract. Functional DOM identifiers are migrated separately because they are still consumed by live modules.
