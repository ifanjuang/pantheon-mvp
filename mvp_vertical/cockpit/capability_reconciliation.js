(() => {
  const previousModels = currentModels;

  function capabilityReconciliationModels() {
    return [
      simpleCapabilityModel({
        id: "capability-runtime-reconciled",
        kind: "hermes",
        typeLabel: "Gestion de capacités",
        title: "Lifecycle + exécuteur Hermes",
        summary: "Le lifecycle manager et l’adapter d’exécution native Hermes existent côté MVP. Le binding Cockpit de l’inventaire et des mutations reste à connecter.",
        status: "partial",
        signal: "Implémenté dans le repo · runtime cible non connecté",
        context: "Outils",
        sections: [
          ["Recto", [
            "Capability manager : implémenté.",
            "HermesCapabilityExecutor : implémenté.",
            "CapabilityRecord live : non exposé au Cockpit.",
            "Endpoint Hermes cible : non configuré par l’état du repo.",
          ]],
          ["Verso", [
            "Types : skill, function, workflow, runtime_agent, plugin, mcp_binding, connector.",
            "Axes : installation, enablement, activation_scope, health, update, source_ref.",
            "Une action conséquente passe par Pantheon preflight + Decision humaine valide avant l’exécuteur natif.",
            "Le chemin d’opération Hermes reste à vérifier contre un runtime Hermes 0.19 réel.",
            "installed ≠ approved ; enabled ≠ activated ; healthy ≠ safe ; technical receipt ≠ Evidence.",
          ]],
        ],
      }),
      simpleCapabilityModel({
        id: "document-runtime-candidates",
        kind: "gate",
        typeLabel: "Runtime documentaire",
        title: "Observations candidates",
        summary: "Les branches empilées #59/#61/#62 définissent Paperless, PDP, Docling et inventaire Hermes en lecture seule ; elles ne sont pas présentées comme état live du main.",
        status: "partial",
        signal: "Candidats empilés · adoption non établie",
        context: "Outils",
        sections: [
          ["Cibles read-only", [
            "Paperless / bounded gateway.",
            "Pantheon PDP.",
            "Docling Serve.",
            "Hermes native skill inventory.",
            "Synthetic acceptance status.",
          ]],
          ["Limites", [
            "Chaque observation conserve sa source et son horodatage.",
            "Aucun healthy global n’est synthétisé.",
            "Observation runtime ≠ activation ; synthetic pass ≠ production adoption.",
          ]],
        ],
      }),
    ];
  }

  function simpleCapabilityModel({ id, kind, typeLabel, title, summary, status, signal, context, sections }) {
    return {
      id,
      kind,
      typeLabel,
      title,
      summary,
      status,
      signal,
      context,
      frame: "tool",
      attention: null,
      responsibilities: [
        { icon: "scope", label: "Pantheon gouverne le scope et les gates" },
        { icon: "hermes", label: "Hermes exécute l’opération native bornée" },
        { icon: "review", label: "Effet conséquent = décision humaine" },
      ],
      sections,
      actions: [],
    };
  }

  currentModels = function reconciledInformationArchitectureModels() {
    if (state.space === "outils") return capabilityReconciliationModels();
    return previousModels();
  };

  window.render?.();
})();
