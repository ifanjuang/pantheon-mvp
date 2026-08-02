(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const dataLoader = window.PantheonCockpitDataLoader.create();
  const navigationProjection = window.PantheonNavigationProjection;
  const childAssembler = window.PantheonChildCollectionAssembler;
  if (!navigationProjection) throw new Error("Navigation projection unavailable");
  if (!childAssembler?.assemble) throw new Error("Child collection assembler unavailable");

  const PROJECT_ACCENTS = ["#244f7b", "#6a4a77", "#356753", "#805a2c", "#76504a", "#4d5f87"];
  const CONTACT_GROUPS = [
    "Maîtrise d’ouvrage",
    "Équipe de maîtrise d’œuvre",
    "Bureaux d’études",
    "Bureau de contrôle",
    "SSI",
    "Entreprises de travaux",
    "Autres intervenants",
  ];

  const state = {
    project: "",
    token: "",
    projects: [],
    projectSchema: null,
    information: [],
    legacyDocuments: [],
    knowledge: [],
    workIssues: [],
    changeCandidates: [],
    currentRuns: [],
    toolCatalog: [],
    cards: new Map(),
    children: new Map(),
    flipped: new Set(),
    navigator: null,
    lastMove: "none",
  };

  const text = (value, fallback = "") => value == null || value === "" ? fallback : String(value);
  const slug = value => String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  function stableAccent(value) {
    const input = String(value || "project");
    let hash = 0;
    for (let index = 0; index < input.length; index += 1) {
      hash = ((hash << 5) - hash + input.charCodeAt(index)) | 0;
    }
    return PROJECT_ACCENTS[Math.abs(hash) % PROJECT_ACCENTS.length];
  }

  function card(input) {
    const projection = window.PantheonStructuredInterface?.buildCardProjection?.(input) || {};
    return {
      role: "entity",
      family: "information",
      presentation_family: input.presentation_family || input.family || "information",
      status: "neutral",
      summary: "",
      type_tags: [],
      subject_tags: [],
      limits: [],
      available_actions: [],
      back: [],
      ...input,
      ...projection,
      presentation_family: projection.presentation_family || input.presentation_family || input.family || "information",
    };
  }

  function putCard(model) {
    state.cards.set(model.entity_id, model);
    return model.entity_id;
  }

  function setChildren(parentId, ids) {
    state.children.set(parentId, [...ids].filter(Boolean));
  }

  function rootCards() {
    return [
      card({ entity_id: "space:pantheon", entity_type: "cockpit_space", role: "conversation", family: "pantheon", title: "Pantheon", category: "Pantheon", summary: "Contexte, gouvernance, décisions conséquentes et runs en cours.", status: "active", back: [["Principe", "Pantheon gouverne ; Hermès exécute."]] }),
      card({ entity_id: "space:affaires", entity_type: "cockpit_space", role: "container", family: "project", title: "Affaires", category: "Projets", summary: "Projets, Informations, Contacts et Travaux.", status: "active", back: [["Source", "PostgreSQL Agency Data reste le system of record."]] }),
      card({ entity_id: "space:connaissances", entity_type: "cockpit_space", role: "container", family: "information", title: "Connaissances", category: "Références", summary: "Références réutilisables et leur état de revue.", back: [["Limite", "Knowledge ≠ Evidence ≠ mémoire gouvernée."]] }),
      card({ entity_id: "space:outils", entity_type: "cockpit_space", role: "container", family: "tool", title: "Outils", category: "Outils", summary: "Outils, skills, bindings et runtimes observés ou candidats.", back: [["Limite", "Installé ≠ approuvé · healthy ≠ safe."]] }),
    ];
  }

  function projectEntityId(item) {
    return `project:${item.project_id || item.entity_id || item.code || item.display_name}`;
  }

  function formattedValue(field, value) {
    if (value == null || value === "") return "Non renseigné";
    if (Array.isArray(value)) return value.join(" · ");
    if (field?.unit === "EUR" && typeof value === "number") {
      return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);
    }
    if (field?.unit === "m2" && typeof value === "number") return `${value} m²`;
    return String(value);
  }

  function projectSchemaRows(item) {
    if (!state.projectSchema) {
      return Object.entries(item.attributes || {}).map(([key, value]) => [key.replaceAll("_", " "), formattedValue(null, value)]);
    }
    const rows = [];
    for (const field of state.projectSchema.fields || []) {
      if (field.presentation?.hidden === true || field.storage === "system") continue;
      const value = field.storage === "attributes"
        ? item.attributes?.[field.key]
        : field.storage === "projection"
          ? item.claim_values?.[field.key]
          : item[field.key];
      if (value == null || value === "" || (Array.isArray(value) && !value.length)) continue;
      rows.push([field.title || field.label || field.key, formattedValue(field, value)]);
    }
    return rows;
  }

  function workData(projection) {
    return projection.work_issue || projection;
  }

  function normalizeProject(item, { selected = false } = {}) {
    const projectId = item.project_id || item.entity_id || item.code || item.display_name;
    const title = item.display_name || item.code || projectId || "Affaire";
    return card({
      entity_id: projectEntityId(item),
      entity_type: "project",
      family: "project",
      category: "Projet",
      title,
      summary: selected
        ? `${state.information.length + state.legacyDocuments.length} information(s) · ${(item.contacts || []).length} contact(s) · ${state.workIssues.length} travail(aux)`
        : [item.code && item.code !== title ? item.code : null, item.phase, item.location].filter(Boolean).join(" · ") || "Affaire Agency Data",
      status: item.status || "active",
      subject_tags: item.tags || [],
      identity_accent: stableAccent(projectId),
      back: projectSchemaRows(item),
      source_project_id: String(projectId || ""),
    });
  }

  function normalizeInformation(item) {
    return card({
      entity_id: `information:${item.information_id}`,
      entity_type: "information",
      family: "information",
      category: item.category || "Information",
      title: item.title || "Information",
      summary: item.summary || "Résumé non renseigné",
      status: item.status || "draft",
      index: item.index_label || null,
      date: item.information_date || item.updated_at || null,
      author: item.author || null,
      type_tags: item.type_tags || [],
      subject_tags: item.subject_tags || [],
      limits: item.limits || [],
      available_actions: item.status === "acted" ? ["Nouvelle version"] : ["Modifier avec Hermès", "Acter"],
      back: [["Résumé", text(item.summary, "Non renseigné")], ["Informations détaillées", text(item.details, "Non renseignées")], ["Source", text(item.source_ref || item.source_note, "Non renseignée")]],
      base_acted_id: item.base_acted_id || null,
    });
  }

  function normalizeLegacyDocument(item) {
    const naming = item.naming || {};
    const id = item.document_id || item.card_id || item.source_ref || crypto.randomUUID();
    return card({
      entity_id: `document:${id}`,
      entity_type: "document",
      family: "information",
      category: naming.document_type || item.category || "Document",
      title: naming.object_name || item.title || "Document",
      summary: item.summary || "Document source",
      status: item.status || item.analysis_status || "partial",
      date: item.document_date || item.date || item.created_at || null,
      subject_tags: item.subject_tags || item.tags || [],
      back: [["Résumé", text(item.summary, "Non renseigné")], ["Source", text(item.source_ref, "Non exposée")]],
    });
  }

  function normalizeKnowledge(item) {
    return card({
      entity_id: `knowledge:${item.knowledge_id || item.card_id || crypto.randomUUID()}`,
      entity_type: "knowledge",
      family: "information",
      category: item.family || "Référence",
      title: item.title || "Knowledge",
      summary: item.summary || `Version ${item.version || 1}`,
      status: item.review_status || "generated_unreviewed",
      date: item.updated_at || null,
      subject_tags: item.subject_tags || item.tags || [],
      limits: item.limits || ["consultatif"],
      back: [["Informations détaillées", text(item.markdown, "Contenu non exposé")]],
    });
  }

  function normalizeWork(projection) {
    const issue = workData(projection);
    const id = issue.issue_id || crypto.randomUUID();
    return card({
      entity_id: `work:${id}`,
      entity_type: "work_issue",
      family: "work",
      category: "Travail",
      title: issue.title || "Travail",
      summary: issue.description || "Objectif non renseigné",
      status: issue.status || "open",
      subject_tags: issue.tags || [],
      back: [["Objectif", text(issue.description, "Non renseigné")]],
      source_work_id: id,
    });
  }

  function normalizeWorkDecision(projection) {
    const issue = workData(projection);
    const id = issue.issue_id || crypto.randomUUID();
    return card({
      entity_id: `decision:work:${id}`,
      entity_type: "work_decision",
      family: "decision",
      category: "Décision · Travail",
      title: issue.decision_title || issue.title || "Validation du travail",
      summary: issue.decision_question || "Le Travail demande une validation humaine.",
      status: "review",
      available_actions: ["Refuser", "Valider"],
      back: [["Travail", text(issue.title, id)], ["Question", text(issue.decision_question, "Valider la proposition ?")]],
      source_work_id: id,
    });
  }

  function normalizeChangeCandidate(item) {
    const changes = Array.isArray(item.changes) ? item.changes : [];
    return card({
      entity_id: `decision:change:${item.candidate_id}`,
      entity_type: "project_change_candidate",
      family: "decision",
      category: "Décision · Modification",
      title: changes.length === 1 ? `Modifier ${changes[0].field}` : `Modifier ${changes.length} champs du Projet`,
      summary: item.reason || "Proposition de modification à examiner.",
      status: item.status || "pending_review",
      date: item.created_at || null,
      available_actions: item.status === "pending_review" ? ["Refuser", "Valider"] : [],
      back: [["Projet", text(item.entity_id, state.project)], ["Motif", text(item.reason, "Non renseigné")]],
      source_candidate_id: item.candidate_id,
      source_project_id: item.entity_id,
    });
  }

  function normalizeCurrentRun(item) {
    const runId = item.run_id || item.execution_id || item.id || crypto.randomUUID();
    return card({
      entity_id: `run:${runId}`,
      entity_type: item.entity_type || "hermes_run",
      family: item.family || "work",
      category: item.category || "Run en cours",
      title: item.title || item.task_title || `Run ${runId}`,
      summary: item.summary || item.task_summary || "Exécution Hermès en cours.",
      status: item.status || item.run_status || "in_progress",
      available_actions: item.available_actions || [],
      back: item.back || [["Runtime", text(item.runtime || item.runtime_owner, "Non renseigné")]],
      source_run_id: runId,
    });
  }

  function currentRunItems() {
    return state.currentRuns.filter(item => ["active", "in_progress", "running", "waiting"].includes(item.status || item.run_status));
  }

  function normalizeContacts(projectId, contacts = []) {
    const groups = new Map(CONTACT_GROUPS.map(name => [name, []]));
    for (const item of contacts) groups.get(CONTACT_GROUPS.includes(item.group) ? item.group : "Autres intervenants").push(item);
    const back = [...groups.entries()]
      .filter(([, items]) => items.length)
      .map(([group, items]) => [group, items.map(item => [item.name, item.organization, item.role, item.email, item.phone].filter(Boolean).join(" · ")).join("\n")]);
    return card({
      entity_id: `project:${projectId}:contacts`,
      entity_type: "project_contacts",
      family: "contact",
      category: "Contacts",
      title: "Contacts",
      summary: `${contacts.length} contact(s)`,
      identity_accent: stableAccent(projectId),
      back: back.length ? back : [["Contacts", "Aucun contact renseigné pour cette affaire."]],
      source_project_id: projectId,
    });
  }

  function normalizeTool(item) {
    return card({
      entity_id: `tool:${item.tool_id}`,
      entity_type: "tool",
      family: "tool",
      category: item.category || item.resource_type || "Outil",
      title: item.name || item.tool_id,
      summary: item.short_description || "Outil ou binding candidat.",
      status: item.governance_state === "approved" ? "reviewed" : item.governance_state || "neutral",
      subject_tags: item.capability_slots || [],
      back: [["Description", text(item.long_description || item.short_description, "Non renseignée")], ["Runtime", text(item.runtime_owner, "Non renseigné")], ["Santé observée", text(item.health_state, "unknown")], ["Gouvernance", text(item.governance_state, "unknown")]],
    });
  }

  function buildToolCards() {
    if (state.toolCatalog.length) return state.toolCatalog.map(normalizeTool);
    return [card({ entity_id: "tools:catalog-unavailable", entity_type: "tool_container", family: "tool", category: "Outil", title: "Catalogue indisponible", summary: "Aucun état runtime n’est inventé.", back: [["Principe", "Catalogue absent ≠ outil absent."]] })];
  }

  function projectLookup() {
    const wanted = state.project.trim().toLocaleLowerCase("fr-FR");
    if (!wanted) return null;
    return state.projects.find(item => [item.project_id, item.code, item.display_name].filter(Boolean).some(value => String(value).toLocaleLowerCase("fr-FR") === wanted)) || null;
  }

  function rebuildGraph() {
    state.cards.clear();
    state.children.clear();
    rootCards().forEach(putCard);
    const selected = projectLookup();
    const selectedProjectId = selected?.project_id || state.project || null;
    const selectedCardId = selected ? projectEntityId(selected) : selectedProjectId ? `project:${selectedProjectId}` : null;

    childAssembler.assemble({
      rootItemIds: navigationProjection.rootItemIds,
      sourcesFor: navigationProjection.sourcesFor,
      state,
      selected,
      selectedProjectId,
      selectedCardId,
      putCard,
      setChildren,
      normalizeProject,
      normalizeKnowledge,
      normalizeWorkDecision,
      normalizeChangeCandidate,
      normalizeCurrentRun,
      normalizeContacts,
      normalizeInformation,
      normalizeLegacyDocument,
      normalizeWork,
      buildToolCards,
      workData,
      currentRunItems,
    });

    state.navigator = window.PantheonSpatialNavigation.create();
  }

  function currentModel() {
    return state.cards.get(state.navigator?.currentId()) || null;
  }

  function breadcrumbLabels() {
    return state.navigator.snapshot().path.map(part => state.cards.get(part.current_id)?.title).filter(Boolean);
  }

  function renderFallbackCard(model) {
    const article = document.createElement("article");
    article.className = "card v2-card";
    article.dataset.family = model.presentation_family || model.family;
    article.dataset.flipped = state.flipped.has(model.entity_id) ? "true" : "false";
    const inner = document.createElement("div");
    inner.className = "card-inner v2-card-inner";
    const front = document.createElement("div");
    front.className = "card-face card-front v2-card-face v2-card-front";
    const title = document.createElement("h2");
    title.className = "card-title v2-card-title";
    title.textContent = model.title;
    const summary = document.createElement("p");
    summary.className = "card-summary v2-card-summary";
    summary.textContent = model.summary;
    front.append(title, summary);
    const back = document.createElement("div");
    back.className = "card-face card-back v2-card-face v2-card-back";
    for (const [heading, value] of model.back || []) {
      const section = document.createElement("section");
      const h3 = document.createElement("h3");
      h3.textContent = heading;
      const p = document.createElement("p");
      p.textContent = value;
      section.append(h3, p);
      back.append(section);
    }
    inner.append(front, back);
    article.append(inner);
    return article;
  }

  function updateChrome(snapshot, model) {
    $("v2-breadcrumb").textContent = breadcrumbLabels().join(" / ");
    $("v2-previous").disabled = !snapshot.can_move_previous;
    $("v2-next").disabled = !snapshot.can_move_next;
    $("v2-ascend").disabled = !snapshot.can_ascend;
    $("v2-descend").disabled = !model || !(state.children.get(model.entity_id) || []).length;
    $("v2-flip").disabled = !model;
    const rootCurrent = snapshot.path[0]?.current_id;
    document.querySelectorAll("[data-space]").forEach(button => button.classList.toggle("is-active", `space:${button.dataset.space}` === rootCurrent));
  }

  function render() {
    if (!state.navigator) return;
    const snapshot = state.navigator.snapshot();
    const siblings = snapshot.sibling_ids.map(id => state.cards.get(id)).filter(Boolean);
    const model = currentModel();
    if (window.PANTHEON_COCKPIT_SWIPER?.mount) {
      window.PANTHEON_COCKPIT_SWIPER.mount({
        models: siblings,
        activeIndex: snapshot.current_index,
        onActiveChange(active) {
          if (active?.entity_id) state.navigator.selectSibling(active.entity_id);
          updateChrome(state.navigator.snapshot(), active);
        },
      });
    } else {
      const stage = $("v2-stage");
      stage.replaceChildren(model ? renderFallbackCard(model) : document.createTextNode("Aucune carte dans cette collection."));
    }
    updateChrome(snapshot, model);
  }

  function moveHorizontal(delta) {
    state.lastMove = delta < 0 ? "right" : "left";
    state.navigator.moveHorizontal(delta);
    render();
  }

  async function descend() {
    const model = currentModel();
    if (!model) return;
    const children = state.children.get(model.entity_id) || [];
    if (!children.length && model.entity_type === "project" && model.source_project_id !== state.project) {
      $("v2-project").value = model.source_project_id;
      await loadProject({ focusProject: true });
      return;
    }
    if (!children.length) return toggleFlip();
    state.navigator.descend({ parent_entity_id: model.entity_id, collection_id: `children:${model.entity_id}`, item_ids: children });
    render();
  }

  function ascend() {
    state.navigator.ascend();
    render();
  }

  function toggleFlip() {
    const model = currentModel();
    if (!model) return;
    if (state.flipped.has(model.entity_id)) state.flipped.delete(model.entity_id);
    else state.flipped.add(model.entity_id);
    render();
  }

  function jumpToSpace(space) {
    state.navigator.returnToRoot(`space:${space}`);
    render();
  }

  function setMessage(message) {
    $("v2-status").textContent = message;
  }

  async function loadProject({ focusProject = false } = {}) {
    const requested = $("v2-project").value.trim();
    state.token = $("v2-token").value;
    if (!state.token) return setMessage("Clé d’accès requise pour lire Agency Data.");
    $("v2-load").disabled = true;
    try {
      [state.projects, state.projectSchema] = await Promise.all([
        dataLoader.loadAgencyProjects(state.token),
        dataLoader.loadProjectSchema(state.token),
      ]);
      state.project = requested;
      const matched = projectLookup();
      if (matched?.project_id) state.project = matched.project_id;
      if (state.project) {
        const bundle = await dataLoader.loadProjectBundle(state.project, state.token);
        Object.assign(state, bundle);
      } else {
        state.information = [];
        state.legacyDocuments = [];
        state.knowledge = [];
        state.workIssues = [];
        state.changeCandidates = [];
      }
      rebuildGraph();
      state.navigator.returnToRoot("space:affaires");
      if (focusProject || state.project) {
        const projectIds = state.children.get("space:affaires") || [];
        const target = projectIds.find(id => state.cards.get(id)?.source_project_id === state.project);
        if (target) state.navigator.descend({ parent_entity_id: "space:affaires", collection_id: "children:space:affaires", item_ids: projectIds, initial_entity_id: target });
      }
      render();
      setMessage(state.project ? `Affaire ${state.project} chargée.` : `${state.projects.length} affaire(s) chargée(s).`);
    } catch (error) {
      setMessage(`Chargement refusé : ${error.message}`);
    } finally {
      $("v2-load").disabled = false;
    }
  }

  function bindControls() {
    $("v2-previous").addEventListener("click", () => moveHorizontal(-1));
    $("v2-next").addEventListener("click", () => moveHorizontal(1));
    $("v2-ascend").addEventListener("click", ascend);
    $("v2-descend").addEventListener("click", () => void descend());
    $("v2-flip").addEventListener("click", toggleFlip);
    $("v2-load").addEventListener("click", () => void loadProject());
    document.querySelectorAll("[data-space]").forEach(button => button.addEventListener("click", () => jumpToSpace(button.dataset.space)));
  }

  async function init() {
    state.toolCatalog = await dataLoader.loadToolCatalog();
    rebuildGraph();
    bindControls();
    window.addEventListener("pantheon:current-runs", event => {
      state.currentRuns = Array.isArray(event.detail?.runs) ? event.detail.runs : [];
      rebuildGraph();
      render();
    });
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => void init(), { once: true });
  else void init();
})();
