(() => {
  const SPACES = [
    ["pantheon", "Pantheon"],
    ["affaires", "Affaires"],
    ["connaissances", "Connaissances"],
    ["outils", "Outils"],
    ["decisions", "Décisions"],
  ];

  const SPACE_COPY = {
    pantheon: ["PANTHEON", "Contexte et attention"],
    affaires: ["AFFAIRES", "Dossiers, travail et documents"],
    connaissances: ["CONNAISSANCES", "Knowledge réutilisable"],
    outils: ["OUTILS", "Capacités et état opérationnel"],
    decisions: ["DÉCISIONS", "Questions, validations et arbitrages"],
  };

  const PHASES = [
    ["00_Gestion", "Gestion"],
    ["10_Conception", "Conception"],
    ["20_Autorisations", "Autorisations"],
    ["30_DCE", "DCE"],
    ["40_Marche", "Marché"],
    ["50_Chantier", "Chantier"],
    ["60_Reception", "Réception"],
    ["90_Sinistres", "Sinistres"],
  ];

  const legacyRenderCard = renderCard;
  const legacyOpenDetail = openDetail;

  state.space = "pantheon";
  state.affaireView = "root";
  state.knowledgeFolder = null;

  const compact = value => value || "non exposé par ce vertical";

  function projectColor(project) {
    const palette = [
      ["#35544a", "#f7fbf9"],
      ["#55446d", "#fbf8ff"],
      ["#6a4a3c", "#fff9f5"],
      ["#36556f", "#f6fbff"],
      ["#5f5634", "#fffdf4"],
      ["#524f5b", "#fbfaff"],
    ];
    let hash = 0;
    for (const char of project || "pantheon") hash = ((hash << 5) - hash + char.charCodeAt(0)) | 0;
    return palette[Math.abs(hash) % palette.length];
  }

  function projectDocumentPhase(item) {
    const value = item.naming?.phase_folder || item.naming?.phase_code || "";
    return PHASES.find(([folder]) => value === folder || value.startsWith(folder.slice(0, 2)))?.[0] || value;
  }

  function action(label, run, { primary = false, disabled = false, note = "" } = {}) {
    return { label, run, primary, disabled, note };
  }

  function closeDetail() {
    const dialog = $("detail-dialog");
    if (dialog?.open) dialog.close();
  }

  function go(space, mutate = null) {
    closeDetail();
    state.space = space;
    if (mutate) mutate();
    render();
  }

  function simpleModel({
    id,
    kind = "document",
    typeLabel,
    title,
    summary,
    status = "partial",
    signal,
    context,
    frame = "gradient",
    attention = null,
    responsibilities = [],
    sections = [],
    actions = [],
    color = null,
    foreground = null,
  }) {
    return {
      id,
      kind,
      typeLabel,
      title,
      summary,
      status,
      signal,
      context,
      frame,
      attention,
      responsibilities,
      sections,
      actions,
      color,
      foreground,
    };
  }

  function activeProjectModel() {
    const project = state.project || "Affaire non ouverte";
    const [color, foreground] = projectColor(project);
    const openWork = state.workIssues.filter(item => !["done", "cancelled"].includes(item.work_issue?.status)).length;
    const reviewWork = state.workIssues.filter(item => item.work_issue?.status === "review").length;
    const observedPhases = [...new Set(state.documents.map(projectDocumentPhase).filter(Boolean))];

    return simpleModel({
      id: `project-${project}`,
      kind: "project",
      typeLabel: "Affaire",
      title: project,
      summary: state.project
        ? `${state.documents.length} document(s) · ${state.knowledge.length} Knowledge · ${openWork} sujet(s) ouvert(s)`
        : "Sélectionnez une affaire pour charger ses projections.",
      status: state.project ? "ready" : "partial",
      signal: reviewWork ? `${reviewWork} revue(s) humaine(s) ouverte(s)` : "Contexte projet borné",
      context: "Affaire active",
      frame: "project",
      color,
      foreground,
      attention: reviewWork ? "human" : null,
      responsibilities: [
        { icon: "scope", label: "Une identité de projet, plusieurs projections" },
        { icon: "source", label: "Les cartes ne remplacent pas les sources" },
        ...(reviewWork ? [{ icon: "decision", label: `${reviewWork} revue(s) à traiter`, attention: true }] : []),
      ],
      sections: [
        ["Recto", [
          `Nom / code : ${project}`,
          `Dossiers documentaires observés : ${observedPhases.length ? observedPhases.join(", ") : "aucun"}`,
          `Documents : ${state.documents.length}`,
          `Knowledge projet : ${state.knowledge.length}`,
          `Work Issues : ${state.workIssues.length}`,
        ]],
        ["Verso · identité à enrichir", [
          "Type de projet : non exposé par l’API actuelle.",
          "Commune / adresse : non exposées par l’API actuelle.",
          "Phase projet : ne pas la déduire automatiquement de la seule présence de documents.",
          "Mission, client principal, surface typée, parcelles, PLU / PLUi et contraintes réglementaires : à brancher sur le Project Profile gouverné.",
          "Toute valeur future devra rester sourcée, datée et qualifiée.",
        ]],
      ],
      actions: [
        action("Voir les documents", () => go("affaires", () => { state.affaireView = "documents"; }), { primary: true }),
        action("Voir le travail", () => go("affaires", () => { state.affaireView = "work"; })),
        action("Knowledge liée", () => go("affaires", () => { state.affaireView = "knowledge"; })),
        action("Décisions", () => go("decisions")),
      ],
    });
  }

  function phaseFolderModel(folder, label) {
    const documents = state.documents.filter(item => projectDocumentPhase(item) === folder);
    return simpleModel({
      id: `phase-${folder}`,
      kind: "document",
      typeLabel: "Dossier",
      title: folder,
      summary: `${label} · ${documents.length} document(s) observé(s)`,
      status: documents.length ? "ready" : "partial",
      signal: documents.length ? "Ouvrir la vue documentaire" : "Dossier logique vide",
      context: state.project || "Affaire non ouverte",
      frame: "folder",
      responsibilities: [
        { icon: "document", label: "Navigation documentaire logique" },
        { icon: "source", label: "Dossier Cockpit ≠ déplacement de fichiers NAS" },
      ],
      sections: [
        ["Recto", [folder, label, `${documents.length} document(s)`]],
        ["Verso", [
          `Affaire : ${state.project || "non ouverte"}`,
          "Le dossier est une vue de navigation ; il ne constitue pas une source ni une permission.",
          ...documents.slice(0, 8).map(item => item.naming?.object_name || item.title || item.document_id),
        ]],
      ],
      actions: [
        action("Ouvrir", () => go("affaires", () => { state.affaireView = `phase:${folder}`; }), { primary: true }),
      ],
    });
  }

  function directoryModel(type) {
    const contacts = type === "contacts";
    return simpleModel({
      id: `directory-${type}`,
      kind: "project",
      typeLabel: "Répertoire projet",
      title: contacts ? "Intervenants & contacts" : "Entreprises",
      summary: contacts
        ? "Clients, agence, BET et autres participants du projet."
        : "Entreprises, artisans et fournisseurs organisés par lot.",
      status: "partial",
      signal: "Contrat UX implémenté · données métier non branchées",
      context: state.project || "Affaire non ouverte",
      frame: "directory",
      responsibilities: [
        { icon: "project", label: "Répertoire scoped à l’Affaire" },
        { icon: "review", label: "Identités et engagements à confirmer", attention: true },
      ],
      sections: contacts ? [
        ["Recto", ["Nombre de contacts : non exposé", "BET actifs : non exposé", "Client principal : non exposé"]],
        ["Verso attendu", [
          "Personne et organisation stables.",
          "Rôle projet, mission, email, téléphone, période active, statut de participation, source et dernière vérification.",
          "Catégories : maîtrise d’ouvrage, équipe agence, architectes, BET, géotechnicien, géomètre, thermique, acoustique, contrôle, SPS, AMO, notaire, assureur/expert.",
        ]],
      ] : [
        ["Recto", ["Lots : non exposés", "Entreprises sélectionnées : non exposées", "Marchés enregistrés : non exposés", "Alertes assurance : non exposées"]],
        ["Verso attendu", [
          "Identité entreprise stable + engagement projet séparé.",
          "Lot, consultation, devis, sélection, marché, assurance, travaux, réserves, source et dernière vérification.",
          "Sélectionnée ≠ contractualisée ; nommée dans un document ≠ engagée sur le projet.",
        ]],
      ],
      actions: [
        action("Consulter", () => {}, { primary: true }),
        action("Ajouter / modifier", null, { disabled: true, note: "Endpoint métier non branché dans ce vertical." }),
      ],
    });
  }

  function knowledgeFolderModels() {
    const groups = new Map();
    for (const item of state.knowledge) {
      const family = item.family || "Sans famille";
      if (!groups.has(family)) groups.set(family, []);
      groups.get(family).push(item);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b, "fr")).map(([family, items]) => simpleModel({
      id: `knowledge-folder-${family}`,
      kind: "knowledge",
      typeLabel: "Dossier Knowledge",
      title: family,
      summary: `${items.length} carte(s) Knowledge`,
      status: "ready",
      signal: "Collection logique · sources inchangées",
      context: "Connaissances",
      frame: "knowledge-folder",
      responsibilities: [
        { icon: "knowledge", label: "Conteneur de navigation" },
        { icon: "source", label: "Appartenance au dossier ≠ propriété de la source" },
      ],
      sections: [
        ["Recto", [family, `${items.length} carte(s)`]],
        ["Verso", [
          "Le dossier organise la navigation et peut devenir imbriqué sans imposer une arborescence physique.",
          ...items.slice(0, 10).map(item => item.title || item.knowledge_id),
        ]],
      ],
      actions: [
        action("Ouvrir", () => go("connaissances", () => { state.knowledgeFolder = family; }), { primary: true }),
        action("Nouveau sous-dossier", null, { disabled: true, note: "Persistance des dossiers Knowledge non exposée par ce vertical." }),
        action("Ajouter une source", null, { disabled: true, note: "Utiliser un adapter d’intake gouverné lorsqu’il est branché." }),
      ],
    }));
  }

  function pantheonContextModel() {
    const reviewCount = state.workIssues.filter(item => item.work_issue?.status === "review").length;
    const unreviewedKnowledge = state.knowledge.filter(item => ["generated_unreviewed", "needs_review"].includes(item.review_status)).length;
    return simpleModel({
      id: "pantheon-context",
      kind: "hermes",
      typeLabel: "Pantheon",
      title: state.project ? `Contexte · ${state.project}` : "Choisir une affaire",
      summary: state.project
        ? "Contexte professionnel explicite avant toute mobilisation de source ou de capacité."
        : "Ouvrez une affaire pour charger ses documents, Knowledge et sujets de travail.",
      status: state.project ? "ready" : "partial",
      signal: state.project ? `${reviewCount + unreviewedKnowledge} élément(s) à examiner` : "Aucun périmètre actif",
      context: "Conversation contextuelle",
      frame: "gradient",
      attention: reviewCount + unreviewedKnowledge ? "human" : null,
      responsibilities: [
        { icon: "scope", label: "Affaire et périmètre explicites" },
        { icon: "hermes", label: "Hermes exécute ; le cockpit n’est pas le runtime" },
        ...(reviewCount ? [{ icon: "decision", label: `${reviewCount} revue(s)`, attention: true }] : []),
      ],
      sections: [
        ["Recto", [
          `Affaire active : ${state.project || "aucune"}`,
          `Documents sélectionnables : ${state.documents.length}`,
          `Knowledge projet : ${state.knowledge.length}`,
          `Revues de travail : ${reviewCount}`,
        ]],
        ["Verso · contexte", [
          "Conversation active : surface de conversation non branchée dans ce vertical.",
          "Profil Hermes / binding modèle : non exposés par l’API cockpit actuelle.",
          "Le contexte visible ne vaut ni autorisation, ni Evidence, ni mémoire gouvernée.",
          "Les suggestions restent réversibles avant un effet conséquent.",
        ]],
      ],
      actions: [
        action("Ouvrir l’Affaire", () => go("affaires"), { primary: true }),
        action("Préciser la demande", () => openDetail(questionnaireModel())),
        action("Voir les décisions", () => go("decisions")),
      ],
    });
  }

  function decisionRequestModels() {
    return state.workIssues
      .filter(projection => projection.work_issue?.status === "review")
      .map(projection => {
        const issue = projection.work_issue || {};
        const returnSummary = projection.hermes_runs?.at(-1)?.normalized_return?.summary;
        return simpleModel({
          id: `decision-request-${issue.issue_id}`,
          kind: "gate",
          typeLabel: "Validation",
          title: issue.title || "Revue humaine",
          summary: returnSummary || issue.description || "Un résultat candidat attend une détermination humaine.",
          status: "review",
          signal: "Decision Request / Gate · pas encore une Decision",
          context: issue.case_ref || state.project,
          frame: "decision",
          attention: "human",
          responsibilities: [
            { icon: "decision", label: "Détermination humaine requise", attention: true },
            { icon: "scope", label: `Effet demandé : ${compact(issue.requested_effect)}` },
          ],
          sections: [
            ["Recto", [
              "Type : Validation",
              `Affaire : ${issue.case_ref || state.project || "non renseignée"}`,
              `Work Issue : ${issue.issue_id || "non renseigné"}`,
              `Priorité : ${issue.priority || "non renseignée"}`,
            ]],
            ["Verso", [
              `Question / résultat à examiner : ${returnSummary || issue.description || "non exposé"}`,
              `Action conditionnée : ${compact(issue.requested_effect)}`,
              `Task Contract : ${compact(issue.task_contract_ref)}`,
              "Cette carte est un Gate dérivé d’un Work Issue en revue. Le vertical actuel n’expose pas encore un objet Decision séparé avec son propre endpoint.",
            ]],
          ],
          actions: [
            action("Ouvrir le sujet", () => {
              closeDetail();
              openDetail(workIssueModel(projection));
            }, { primary: true }),
            action("Enregistrer une Decision", null, { disabled: true, note: "Le Decision record séparé n’est pas exposé par l’API actuelle." }),
          ],
        });
      });
  }

  function toolsModels() {
    const manager = simpleModel({
      id: "capability-manager",
      kind: "hermes",
      typeLabel: "Gestion de capacités",
      title: "Catalogue gouverné",
      summary: "Skills, functions, workflows, runtime agents, plugins, MCP et connecteurs.",
      status: "partial",
      signal: "Lifecycle manager implémenté · inventaire Cockpit non connecté",
      context: "Outils",
      frame: "tool",
      responsibilities: [
        { icon: "scope", label: "Activation par scope distincte de l’installation" },
        { icon: "gate", label: "Actions conséquentes derrière le chokepoint" },
      ],
      sections: [
        ["Recto", [
          "Types supportés : skill, function, workflow, runtime_agent, plugin, mcp_binding, connector.",
          "Inventaire live : non exposé au navigateur.",
        ]],
        ["Verso · axes à afficher par ressource", [
          "Source et version.",
          "Installation, configuration, enablement, activation par scope.",
          "Health observation, update signal, risque, dépendances et rollback.",
          "installed ≠ approved ; healthy ≠ safe ; update_available ≠ update_authorized.",
        ]],
      ],
      actions: [
        action("Inspecter l’inventaire", null, { disabled: true, note: "Aucun endpoint d’inventaire CapabilityRecord n’est encore exposé par le Cockpit." }),
        action("Proposer installation", null, { disabled: true, note: "Le manager backend peut planifier l’action mais le binding UI/API n’est pas encore branché." }),
        action("Activer / suspendre / update", null, { disabled: true, note: "Effets conséquents : préflight + décision humaine + exécuteur natif requis." }),
      ],
    });

    const runtime = simpleModel({
      id: "policy-runtime-seam",
      kind: "gate",
      typeLabel: "Control plane",
      title: "PDP / PEP",
      summary: "Le seam de policy HTTP et le lifecycle manager existent dans le repo, sans observation runtime cible dans cette vue.",
      status: "partial",
      signal: "Implémenté dans le repo ≠ déployé / adopté",
      context: "Outils",
      frame: "tool",
      responsibilities: [
        { icon: "gate", label: "Fail-closed pour les effets conséquents" },
        { icon: "history", label: "Receipt technique ≠ Evidence" },
      ],
      sections: [
        ["État", [
          "HttpPolicyClient : implémenté côté MVP.",
          "Capability manager : implémenté côté MVP.",
          "Déploiement, health cible, adoption et activation : non établis par cette vue.",
        ]],
      ],
      actions: [],
    });
    return [manager, runtime];
  }

  function affairesModels() {
    if (!state.project) return [activeProjectModel()];

    if (state.affaireView === "documents") {
      return [activeProjectModel(), ...state.documents.map(documentModel)];
    }
    if (state.affaireView === "work") {
      return [activeProjectModel(), ...state.workIssues.map(workIssueModel)];
    }
    if (state.affaireView === "knowledge") {
      return [activeProjectModel(), ...state.knowledge.map(knowledgeModel)];
    }
    if (state.affaireView.startsWith("phase:")) {
      const phase = state.affaireView.split(":", 2)[1];
      const docs = state.documents.filter(item => projectDocumentPhase(item) === phase).map(documentModel);
      return [phaseFolderModel(phase, PHASES.find(([folder]) => folder === phase)?.[1] || phase), ...docs];
    }

    const reviews = state.workIssues.filter(item => item.work_issue?.status === "review").map(workIssueModel).slice(0, 3);
    const recentDocs = state.documents.map(documentModel).slice(0, 4);
    const linkedKnowledge = state.knowledge.map(knowledgeModel).slice(0, 3);
    return [
      activeProjectModel(),
      directoryModel("contacts"),
      directoryModel("companies"),
      ...PHASES.map(([folder, label]) => phaseFolderModel(folder, label)),
      ...reviews,
      ...recentDocs,
      ...linkedKnowledge,
    ];
  }

  function knowledgeModels() {
    if (state.knowledgeFolder) {
      const items = state.knowledge.filter(item => (item.family || "Sans famille") === state.knowledgeFolder).map(knowledgeModel);
      return [...knowledgeFolderModels().filter(model => model.title === state.knowledgeFolder), ...items];
    }
    const folders = knowledgeFolderModels();
    const unreviewed = state.knowledge
      .filter(item => ["generated_unreviewed", "needs_review"].includes(item.review_status))
      .map(knowledgeModel)
      .slice(0, 5);
    return [...folders, ...unreviewed];
  }

  function pantheonModels() {
    const attention = [
      ...state.workIssues.filter(item => item.work_issue?.status === "review").map(workIssueModel),
      ...state.knowledge.filter(item => ["generated_unreviewed", "needs_review"].includes(item.review_status)).map(knowledgeModel),
      ...state.documents.filter(item => (item.analysis_status || "partial") !== "ready").map(documentModel),
    ].slice(0, 8);
    return [pantheonContextModel(), ...attention];
  }

  currentModels = function informationArchitectureModels() {
    if (state.space === "affaires") return affairesModels();
    if (state.space === "connaissances") return knowledgeModels();
    if (state.space === "outils") return toolsModels();
    if (state.space === "decisions") return decisionRequestModels();
    return pantheonModels();
  };

  function appendActions(model) {
    const actions = model.actions || [];
    if (!actions.length) return;
    const section = document.createElement("section");
    section.className = "detail-actions";
    const heading = document.createElement("h3");
    heading.textContent = "Actions";
    const row = document.createElement("div");
    row.className = "detail-action-row";
    for (const spec of actions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = spec.primary ? "primary-action" : "secondary-action";
      button.textContent = spec.label;
      button.disabled = Boolean(spec.disabled);
      if (spec.note) button.title = spec.note;
      if (!spec.disabled && spec.run) button.addEventListener("click", spec.run);
      row.append(button);
      if (spec.disabled && spec.note) {
        const note = document.createElement("p");
        note.className = "action-note";
        note.textContent = `${spec.label} : ${spec.note}`;
        row.append(note);
      }
    }
    section.append(heading, row);
    $("detail-content").append(section);
  }

  openDetail = function informationArchitectureDetail(model) {
    legacyOpenDetail(model);
    appendActions(model);
  };

  renderCard = function informationArchitectureCard(model) {
    const card = legacyRenderCard(model);
    card.dataset.frame = model.frame || card.dataset.frame || "gradient";
    if (model.color) card.style.setProperty("--project-color", model.color);
    if (model.foreground) card.style.setProperty("--project-foreground", model.foreground);
    return card;
  };

  function breadcrumbText() {
    if (state.space === "affaires") {
      if (!state.project) return "Affaires";
      if (state.affaireView.startsWith("phase:")) return `Affaires / ${state.project} / ${state.affaireView.split(":", 2)[1]}`;
      if (state.affaireView !== "root") return `Affaires / ${state.project} / ${state.affaireView}`;
      return `Affaires / ${state.project}`;
    }
    if (state.space === "connaissances" && state.knowledgeFolder) return `Connaissances / ${state.knowledgeFolder}`;
    return SPACE_COPY[state.space]?.[0] || "Pantheon";
  }

  function renderBreadcrumb() {
    let node = document.querySelector(".cockpit-breadcrumb");
    if (!node) {
      node = document.createElement("p");
      node.className = "cockpit-breadcrumb";
      document.querySelector(".scene-heading")?.before(node);
    }
    node.textContent = breadcrumbText();
    node.hidden = state.space === "pantheon";
  }

  function rebuildRail() {
    const rail = document.querySelector(".scene-rail");
    if (!rail) return;
    rail.replaceChildren();
    rail.setAttribute("aria-label", "Espaces du cockpit");
    for (const [space, label] of SPACES) {
      const button = document.createElement("button");
      button.className = "scene-tab";
      button.dataset.space = space;
      button.type = "button";
      button.textContent = label;
      button.classList.toggle("is-active", state.space === space);
      button.addEventListener("click", () => {
        state.space = space;
        if (space !== "affaires") state.affaireView = "root";
        if (space !== "connaissances") state.knowledgeFolder = null;
        render();
      });
      rail.append(button);
    }
  }

  render = function informationArchitectureRender() {
    const [eyebrow, title] = SPACE_COPY[state.space] || SPACE_COPY.pantheon;
    $("scene-eyebrow").textContent = eyebrow;
    $("scene-title").textContent = title;
    const models = currentModels();
    const scoped = state.project ? ` · ${state.project}` : "";
    const statusCopy = {
      pantheon: state.project ? `${models.length} projection(s) de contexte et d’attention${scoped}.` : "Ouvrez une affaire pour construire un contexte explicite.",
      affaires: state.project ? `${models.length} projection(s) dans l’Affaire${scoped}.` : "Aucune Affaire ouverte.",
      connaissances: `${models.length} dossier(s) ou carte(s) Knowledge${scoped}.`,
      outils: "État de la couche de gestion de capacités ; l’inventaire runtime live n’est pas encore exposé.",
      decisions: models.length ? `${models.length} demande(s) de validation issue(s) des Work Issues en revue.` : "Aucune Decision Request exposée. Aucun Decision record séparé n’est inventé.",
    };
    $("scene-status").textContent = statusCopy[state.space];
    const deck = $("deck");
    deck.replaceChildren();
    if (!models.length) deck.append($("empty-template").content.cloneNode(true));
    else for (const model of models) deck.append(renderCard(model));
    document.querySelectorAll("[data-space]").forEach(button => {
      button.classList.toggle("is-active", button.dataset.space === state.space);
    });
    renderBreadcrumb();
  };

  window.render = render;
  rebuildRail();
  render();
})();
