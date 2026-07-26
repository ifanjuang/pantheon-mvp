(() => {
  const provenanceLabels = {
    hermes_native_inventory: "Inventaire Hermes",
    hermes_dynamic_skill: "Skill Hermes dynamique",
    runtime_installed: "Runtime observé",
    pantheon_catalog: "Catalogue Pantheon",
    external_reference: "Référence externe",
    operator_declared: "Déclaré par l’opérateur",
    discovered_binding: "Binding découvert",
  };

  function normalizeObservation(raw) {
    return {
      tool_id: raw.tool_id || raw.skill_id || raw.native_identifier || raw.id,
      name: raw.name || raw.title || raw.tool_id || raw.skill_id || raw.native_identifier || "Outil Hermes",
      provenance_mode: raw.provenance_mode || "hermes_native_inventory",
      installation_state: raw.installation_state || raw.install_status || "discovered",
      native_state: raw.native_state || raw.native_enabled_state || "unknown",
      health_state: raw.health_state || raw.health_status || "unknown",
      update_state: raw.update_state || raw.update_status || "update_unknown",
      activation_state: raw.activation_state || raw.activation_status || "not_activated",
      governance_state: raw.governance_state || raw.pantheon_status || "unreviewed",
      observed_at: raw.observed_at || null,
      native_identifier: raw.native_identifier || raw.skill_id || raw.tool_id || raw.id || null,
      source_repository: raw.source_repository || raw.source || null,
      version: raw.version || raw.installed_version || null,
      capabilities: raw.capabilities || raw.skills_exposed || raw.functions_exposed || [],
      permissions: raw.permissions || [],
    };
  }

  function mergeCatalogAndHermes(catalogItems, observations) {
    const merged = new Map(catalogItems.map(item => [item.tool_id, { ...item, reconciliation: "catalog_only" }]));
    for (const incoming of observations.map(normalizeObservation)) {
      if (!incoming.tool_id) continue;
      const existing = merged.get(incoming.tool_id);
      if (!existing) {
        merged.set(incoming.tool_id, {
          ...incoming,
          category: "Hermes runtime capability",
          resource_type: "runtime_capability",
          short_description: "Capacité observée dynamiquement dans Hermes.",
          long_description: "Cette capacité provient de l’inventaire normalisé d’Hermes. Sa présence indique une observation runtime, pas une approbation Pantheon ni une activation pour tous les projets.",
          capability_slots: [],
          binding_role: "discovered",
          known_risks: [],
          forbidden: ["automatic approval", "automatic scope activation"],
          reconciliation: "runtime_only",
        });
        continue;
      }
      const versionDrift = Boolean(existing.version && incoming.version && existing.version !== incoming.version);
      merged.set(incoming.tool_id, {
        ...existing,
        ...incoming,
        provenance_mode: incoming.provenance_mode,
        reconciliation: versionDrift ? "version_drift" : "matched",
      });
    }
    return [...merged.values()];
  }

  function stateText(item) {
    return [
      `Installation : ${item.installation_state || "unknown"}`,
      `Runtime : ${item.native_state || "unknown"}`,
      `Health : ${item.health_state || "unknown"}`,
      `Pantheon : ${item.governance_state || "unreviewed"}`,
      `Activation : ${item.activation_state || "not_activated"}`,
      `Update : ${item.update_state || "update_unknown"}`,
    ];
  }

  function toolModel(item) {
    const provenance = provenanceLabels[item.provenance_mode] || item.provenance_mode || "Provenance inconnue";
    const slots = item.capability_slots || [];
    const capabilities = item.capabilities || [];
    const status = item.governance_state === "approved_for_production" ? "reviewed" : "partial";
    return {
      id: `tool-${item.tool_id}`,
      kind: "hermes",
      typeLabel: "Outil",
      title: item.name,
      summary: item.short_description || item.category || "Capacité outillée",
      status,
      signal: `${provenance} · ${item.reconciliation || "to_verify"}`,
      context: slots.length ? slots.join(" · ") : "Capability Slot à qualifier",
      event: null,
      attention: ["unreviewed", "candidate"].includes(item.governance_state) ? "human" : null,
      responsibilities: [
        { icon: "hermes", label: provenance },
        { icon: "scope", label: `Activation : ${item.activation_state || "not_activated"}` },
        { icon: "review", label: `Pantheon : ${item.governance_state || "unreviewed"}`, attention: ["unreviewed", "candidate"].includes(item.governance_state) },
      ],
      sections: [
        ["Description", [item.long_description || item.short_description || "Description non renseignée"]],
        ["Placement", [
          `Type : ${item.resource_type || "non renseigné"}`,
          `Catégorie : ${item.category || "non renseignée"}`,
          `Capability Slot : ${slots.length ? slots.join(", ") : "à qualifier"}`,
          `Rôle de binding : ${item.binding_role || "à qualifier"}`,
          `Provenance : ${provenance}`,
          `Réconciliation : ${item.reconciliation || "to_verify"}`,
        ]],
        ["États indépendants", stateText(item)],
        ["Hermes / runtime", [
          `Identifiant natif : ${item.native_identifier || "non observé"}`,
          `Version : ${item.version || "non observée"}`,
          `Source : ${item.source_repository || "non observée"}`,
          `Dernière observation : ${item.observed_at ? formatMoment(item.observed_at) : "aucune observation runtime"}`,
          ...(capabilities.length ? capabilities.map(value => `Capacité exposée : ${typeof value === "string" ? value : value.identifier || value.name || "non nommée"}`) : ["Aucune capacité runtime observée."]),
        ]],
        ["Risques / limites", [
          ...((item.known_risks || []).map(value => `Risque : ${value}`)),
          ...((item.forbidden || []).map(value => `Interdit : ${value}`)),
          "catalogued != installed != approved != activated",
          "runtime_success != evidence",
        ]],
      ],
    };
  }

  let catalog = [];
  let hermesObservations = [];

  const previousCurrentModels = currentModels;
  currentModels = function () {
    if (state.scene === "tools") {
      return mergeCatalogAndHermes(catalog, hermesObservations).map(toolModel);
    }
    return previousCurrentModels();
  };

  sceneCopy.tools = ["OUTILS", "Capacités, skills et bindings"];

  const rail = document.querySelector(".scene-rail");
  if (rail) {
    const button = document.createElement("button");
    button.className = "scene-tab";
    button.dataset.scene = "tools";
    button.type = "button";
    button.textContent = "Outils";
    button.addEventListener("click", () => {
      state.scene = "tools";
      document.querySelectorAll("[data-scene]").forEach(tab => tab.classList.toggle("is-active", tab === button));
      render();
    });
    rail.append(button);
  }

  window.PantheonToolCards = {
    setHermesObservations(observations) {
      hermesObservations = Array.isArray(observations) ? observations : [];
      if (state.scene === "tools") render();
    },
    getMergedRecords() {
      return mergeCatalogAndHermes(catalog, hermesObservations);
    },
  };

  fetch("tool_catalog.json")
    .then(response => {
      if (!response.ok) throw new Error(`catalogue ${response.status}`);
      return response.json();
    })
    .then(payload => {
      catalog = Array.isArray(payload.items) ? payload.items : [];
      if (state.scene === "tools") render();
    })
    .catch(error => {
      console.warn("Pantheon Tool Card catalogue unavailable", error);
      catalog = [];
    });
})();
