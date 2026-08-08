(() => {
  "use strict";

  function text(value, fallback = "—") {
    return value == null || value === "" ? fallback : String(value);
  }

  function entityId(ref) {
    return ref && typeof ref === "object" ? ref.entity_id || null : null;
  }

  function baseCard(input) {
    return {
      role: "entity",
      family: "project",
      presentation_family: "information",
      status: "neutral",
      summary: "",
      type_tags: [],
      subject_tags: [],
      limits: ["Projection en lecture seule"],
      available_actions: [],
      back: [],
      ...input,
    };
  }

  function rootCard(anatomy) {
    const summary = anatomy.summary || {};
    const coverage = anatomy.coverage || {};
    const hierarchy = anatomy.structure?.hierarchy || {};
    return baseCard({
      entity_id: `project-anatomy:${anatomy.project_ref}`,
      entity_type: "project_anatomy_projection",
      category: "Anatomie du projet",
      title: "Anatomie du projet",
      summary: `${summary.stable_object_count || 0} objet(s) · ${summary.source_representation_count || 0} source(s) · ${summary.unmapped_source_representation_count || 0} non mappée(s)`,
      type_tags: ["project-anatomy", `v${anatomy.model_version || 2}`],
      subject_tags: summary.attention_claim_count ? [`${summary.attention_claim_count} point(s) à qualifier`] : [],
      limits: [
        "Projection en lecture seule",
        coverage.status === "not_persisted" ? "Couverture d’observation non persistée" : null,
        hierarchy.status === "not_derived" ? "Hiérarchie non dérivée sans sémantique admise" : null,
      ].filter(Boolean),
      back: [
        ["Objets stables", text(summary.stable_object_count, "0")],
        ["Représentations source", text(summary.source_representation_count, "0")],
        ["Relations", text(summary.relation_claim_count, "0")],
        ["Claims d’attribut", text(summary.attribute_claim_count, "0")],
        ["Matériau non mappé", text(summary.unmapped_source_representation_count, "0")],
        ["Incertitudes à qualifier", text(summary.attention_claim_count, "0")],
        ["Couverture", coverage.status === "not_persisted" ? "Non persistée — aucune absence n’est déduite." : text(coverage.status)],
        ["Hiérarchie", hierarchy.status === "not_derived" ? "Non dérivée — relations exposées sans parentage inventé." : text(hierarchy.status)],
      ],
      source_project_id: anatomy.project_ref,
    });
  }

  function objectCard(item) {
    const relations = Array.isArray(item.relations) ? item.relations : [];
    const attributes = Array.isArray(item.attribute_claims) ? item.attribute_claims : [];
    const sources = Array.isArray(item.source_representation_refs) ? item.source_representation_refs : [];
    const phases = Array.isArray(item.phase_refs) ? item.phase_refs : [];
    const attention = Array.isArray(item.attention_claim_refs) ? item.attention_claim_refs : [];
    const relationLines = relations.map(relation => {
      const subject = entityId(relation.subject_ref);
      const object = entityId(relation.object_ref);
      const other = subject === item.object_id ? object : subject;
      return [relation.relation_type, other].filter(Boolean).join(" → ");
    });
    return baseCard({
      entity_id: `apu-object:${item.object_id}`,
      entity_type: "apu_object",
      category: item.object_family || "Objet du projet",
      title: item.display_name || item.internal_code || item.object_id,
      summary: `${attributes.length} attribut(s) · ${relations.length} relation(s) · ${sources.length} source(s)`,
      type_tags: [item.object_family].filter(Boolean),
      subject_tags: phases,
      limits: ["Projection en lecture seule", attention.length ? `${attention.length} claim(s) nécessitent une qualification` : null].filter(Boolean),
      back: [
        ["Identité stable", item.object_id],
        ["Famille", text(item.object_family)],
        ["Code", text(item.internal_code)],
        ["Phases", phases.join(" · ") || "Non renseignées"],
        ["Sources", sources.join("\n") || "Aucune représentation source reliée"],
        ["Relations", relationLines.join("\n") || "Aucune relation exposée"],
      ],
      source_object_id: item.object_id,
    });
  }

  function unmappedSourceCard(item) {
    const limitations = Array.isArray(item.limitations) ? item.limitations : [];
    return baseCard({
      entity_id: `apu-source:${item.representation_id}`,
      entity_type: "apu_source_representation",
      category: "Source non mappée",
      title: item.source_artifact_ref || item.representation_id,
      summary: [item.source_kind, item.source_artifact_ref, item.proof_status].filter(Boolean).join(" · "),
      type_tags: [item.source_kind].filter(Boolean),
      limits: ["Non mappé ≠ absent", "Projection en lecture seule", ...limitations],
      back: [
        ["Représentation", item.representation_id],
        ["Type de source", text(item.source_kind)],
        ["Source", text(item.source_artifact_ref)],
        ["Version source", text(item.source_version_ref)],
        ["État de preuve source", text(item.proof_status)],
        ["Limites", limitations.join("\n") || "Aucune limite explicitement déclarée"],
      ],
      source_representation_id: item.representation_id,
    });
  }

  function projectCards(anatomy) {
    if (!anatomy || !anatomy.project_ref) return null;
    const objects = Array.isArray(anatomy.structure?.objects) ? anatomy.structure.objects.map(objectCard) : [];
    const unmapped = Array.isArray(anatomy.unmapped_material) ? anatomy.unmapped_material.map(unmappedSourceCard) : [];
    return { root: rootCard(anatomy), children: [...objects, ...unmapped] };
  }

  window.PantheonProjectAnatomyProjection = Object.freeze({ projectCards });
})();
