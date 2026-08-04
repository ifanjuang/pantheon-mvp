(() => {
  "use strict";

  // Pure, read-only projection of the Cockpit card graph into map nodes/links.
  //
  // Boundary (see map/README.md):
  //   map view != data model      — this only reshapes existing projected cards
  //   projection != authority     — `origin` records where a card came from,
  //                                 it is NOT an authority/Evidence claim
  // No fetch, no mutation, no runtime. Input is the already-normalised
  // `state.cards` (Map<entity_id, cardModel>) and `state.children`
  // (Map<parentId, entity_id[]>) produced by cockpit_projection.js.

  // Factual source of a card (where it was read from), never an authority level.
  const ORIGIN_BY_TYPE = Object.freeze({
    project: "agency",
    information: "agency",
    document: "agency",
    project_contacts: "agency",
    project_change_candidate: "agency",
    knowledge: "knowledge",
    work_issue: "hermes",
    work_decision: "hermes",
    hermes_run: "hermes",
  });

  function primarySubject(card) {
    const tags = Array.isArray(card.subject_tags) ? card.subject_tags : [];
    return tags.length ? String(tags[0]) : null;
  }

  function nodeFrom(card) {
    return {
      id: card.entity_id,
      entity_type: card.entity_type || null,
      family: card.presentation_family || card.family || "information",
      title: card.title || card.entity_id,
      status: card.status || null,
      date: card.date || null,
      subject: primarySubject(card),
      subject_tags: Array.isArray(card.subject_tags) ? card.subject_tags.slice() : [],
      type_tags: Array.isArray(card.type_tags) ? card.type_tags.slice() : [],
      origin: ORIGIN_BY_TYPE[card.entity_type] || "agency",
      series_id: card.series_id || null,
      base_acted_id: card.base_acted_id || null,
      source_run_id: card.source_run_id || null,
      // Optional magnitude hint (pages/chunks) for node sizing; null when absent.
      magnitude: card.magnitude != null ? card.magnitude
        : card.page_count != null ? card.page_count
        : card.chunk_count != null ? card.chunk_count : null,
    };
  }

  function groupInto(map, key, value) {
    let bucket = map.get(key);
    if (!bucket) { bucket = []; map.set(key, bucket); }
    bucket.push(value);
    return bucket;
  }

  function build(cards, children) {
    const cardEntries = cards instanceof Map ? [...cards.entries()] : Object.entries(cards || {});
    const childEntries = children instanceof Map ? [...children.entries()] : Object.entries(children || {});

    const nodes = [];
    const present = new Set();
    for (const [id, card] of cardEntries) {
      if (!card) continue;
      nodes.push(nodeFrom(card));
      present.add(id);
    }

    const links = [];

    // Containment (parent -> child), only between present nodes.
    for (const [parent, kids] of childEntries) {
      if (!present.has(parent) || !Array.isArray(kids)) continue;
      for (const child of kids) {
        if (present.has(child)) links.push({ source: parent, target: child, kind: "containment" });
      }
    }

    // Version lineage: chain items sharing a series_id (best-effort insertion order).
    const bySeries = new Map();
    for (const n of nodes) if (n.series_id) groupInto(bySeries, n.series_id, n);
    for (const arr of bySeries.values()) {
      for (let i = 1; i < arr.length; i += 1) {
        links.push({ source: arr[i - 1].id, target: arr[i].id, kind: "lineage" });
      }
    }

    // Explicit acted-base lineage when the referenced base is present.
    for (const n of nodes) {
      if (n.base_acted_id && present.has(n.base_acted_id)) {
        links.push({ source: n.base_acted_id, target: n.id, kind: "lineage" });
      }
    }

    return { nodes, links };
  }

  window.PantheonMapGraphModel = Object.freeze({ build, ORIGIN_BY_TYPE });
})();
