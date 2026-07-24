(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const ROOT_SPACES = ["pantheon", "decisions", "affaires", "connaissances", "outils"];
  const SPACE_LABELS = {
    pantheon: "Pantheon",
    decisions: "Décisions",
    affaires: "Affaires",
    connaissances: "Connaissances",
    outils: "Outils",
  };
  const STATUS_LABELS = {
    ready: "Prêt",
    reviewed: "Revu",
    done: "Clôturé",
    in_progress: "En cours",
    waiting: "En attente",
    review: "À examiner",
    needs_review: "À examiner",
    generated_unreviewed: "Non revu",
    partial: "Partiel",
    conflict: "Conflit",
    failed: "Échec",
    draft: "Brouillon",
    open: "Ouvert",
    active: "Actif",
    inactive: "Inactif",
    neutral: "Référence",
  };
  const FAMILY_MARKS = {
    pantheon: "P",
    decision: "D",
    project: "A",
    document: "DOC",
    evidence: "EV",
    knowledge: "K",
    capability: "#",
    "runtime-host": "H",
    "role-reference": "R",
  };
  const PROJECT_ACCENTS = ["#244f7b", "#6a4a77", "#356753", "#805a2c", "#76504a", "#4d5f87"];

  const state = {
    project: "",
    token: "",
    documents: [],
    knowledge: [],
    workIssues: [],
    cards: new Map(),
    children: new Map(),
    parent: new Map(),
    flipped: new Set(),
    navigator: null,
    lastMove: "none",
  };

  function statusLabel(status) {
    return STATUS_LABELS[status] || String(status || "À vérifier").replaceAll("_", " ");
  }

  function text(value, fallback = "") {
    return value == null || value === "" ? fallback : String(value);
  }

  function stableAccent(value) {
    const input = String(value || "project");
    let hash = 0;
    for (let index = 0; index < input.length; index += 1) hash = ((hash << 5) - hash + input.charCodeAt(index)) | 0;
    return PROJECT_ACCENTS[Math.abs(hash) % PROJECT_ACCENTS.length];
  }

  function card(input) {
    const candidate = {
      role: "entity",
      family: "project",
      status: "neutral",
      summary: "",
      tags: [],
      metrics: [],
      front: {},
      back: [],
      ...input,
    };
    const validation = window.PantheonStructuredInterface?.validateCardModel?.(candidate);
    if (validation && !validation.valid) throw new Error(`Invalid V2 card ${candidate.entity_id}: ${validation.errors.join(", ")}`);
    return candidate;
  }

  function putCard(model, parentId = null) {
    state.cards.set(model.entity_id, model);
    if (parentId) state.parent.set(model.entity_id, parentId);
    return model.entity_id;
  }

  function setChildren(parentId, childIds) {
    state.children.set(parentId, [...childIds].filter(Boolean));
  }

  function rootCards() {
    return [
      card({
        entity_id: "space:pantheon",
        entity_type: "cockpit_space",
        role: "conversation",
        family: "pantheon",
        title: "Pantheon",
        summary: "Dialogue gouverné et contexte explicite.",
        status: "active",
        metrics: [{ value: "IA", label: "Hermes" }],
        back: [
          ["Rôle", "Exposer le contexte, les décisions et l’état gouverné sans devenir runtime."],
          ["Portée", "Le dock Hermes suit la carte courante et ses descendants déclarés."],
        ],
      }),
      card({
        entity_id: "space:decisions",
        entity_type: "cockpit_space",
        role: "container",
        family: "decision",
        title: "Décisions",
        summary: "Tout ce qui demande une attention humaine, sans copier les objets sources.",
        status: "review",
        back: [["Projection", "À examiner · À valider · Questions Hermes · Approbations · Décisions formelles"]],
      }),
      card({
        entity_id: "space:affaires",
        entity_type: "cockpit_space",
        role: "container",
        family: "project",
        title: "Affaires",
        summary: "Projets, personnes, organisations et relations métier.",
        status: "active",
        back: [["Source métier", "Agency Data PostgreSQL est le system of record natif."], ["Notion", "Projection collaborative optionnelle lorsqu’elle est activée."]],
      }),
      card({
        entity_id: "space:connaissances",
        entity_type: "cockpit_space",
        role: "container",
        family: "knowledge",
        title: "Connaissances",
        summary: "Références réutilisables, provenance et état de revue.",
        status: "neutral",
        back: [["Principe", "Knowledge reste distinct de Document, Evidence et mémoire gouvernée."]],
      }),
      card({
        entity_id: "space:outils",
        entity_type: "cockpit_space",
        role: "container",
        family: "capability",
        title: "Outils",
        summary: "Capacités, postes, modèles et références Pantheon.",
        status: "neutral",
        back: [["Principe", "Installé ≠ approuvé · healthy ≠ safe · sélectionné ≠ autorisé."]],
      }),
    ];
  }

  function normalizeDocument(item) {
    const naming = item.naming || {};
    const extraction = item.extraction || {};
    const id = item.document_id || item.card_id || item.source_ref || crypto.randomUUID();
    const title = naming.object_name || naming.document_type || item.title || "Document";
    const status = item.analysis_status || "partial";
    return card({
      entity_id: `document:${id}`,
      entity_type: "document",
      role: "entity",
      family: "document",
      index: naming.revision_index || null,
      title,
      summary: [naming.document_type, naming.phase_code, naming.revision_index].filter(Boolean).join(" · ") || "Document projet",
      status,
      tags: Array.isArray(item.tags) ? item.tags : [],
      metrics: extraction.chunk_count != null ? [{ value: extraction.chunk_count, label: "segments" }] : [],
      front: { issuer: naming.issuer || item.issuer || null },
      back: [
        ["Identité", `Projet : ${text(item.parent_project_id, state.project)}`],
        ["Source", text(item.source_ref, "Source non exposée")],
        ["Analyse", `${statusLabel(status)} · ${Number(extraction.chunk_count || 0)} segment(s)`],
        ["Provenance", text(item.source_digest, "Empreinte non exposée")],
      ],
      source_refs: [item.source_ref].filter(Boolean),
    });
  }

  function normalizeKnowledge(item) {
    const id = item.knowledge_id || item.card_id || crypto.randomUUID();
    const status = item.review_status || "generated_unreviewed";
    return card({
      entity_id: `knowledge:${id}`,
      entity_type: "knowledge",
      role: "entity",
      family: "knowledge",
      title: item.title || "Knowledge",
      summary: `${text(item.family, "Famille non renseignée")} · version ${item.version || 1}`,
      status,
      tags: Array.isArray(item.tags) ? item.tags : [],
      metrics: [{ value: (item.source_chunk_refs || []).length, label: "sources" }],
      back: [
        ["Famille", text(item.family, "Non renseignée")],
        ["Version", item.version || 1],
        ["Document lié", text(item.document_ref, "Non renseigné")],
        ["Limite", "Knowledge ≠ Evidence · Knowledge ≠ mémoire gouvernée."],
      ],
      source_refs: (item.source_chunk_refs || []).filter(Boolean),
    });
  }

  function normalizeWorkIssue(projection) {
    const issue = projection.work_issue || projection;
    const id = issue.issue_id || crypto.randomUUID();
    const status = issue.status || "open";
    return card({
      entity_id: `work:${id}`,
      entity_type: "work_issue",
      role: "entity",
      family: "decision",
      title: issue.title || "Sujet à examiner",
      summary: `${text(issue.issue_type, "action")} · priorité ${text(issue.priority, "normale")}`,
      status,
      metrics: (projection.comments || []).length ? [{ value: projection.comments.length, label: "commentaires" }] : [],
      back: [
        ["Demande", text(issue.description, "Description non renseignée")],
        ["Assignation", text(issue.assigned_to, "Non assignée")],
        ["Effet demandé", text(issue.requested_effect, "Non renseigné")],
        ["Limite", "Une présence dans Décisions n’est pas une Decision Pantheon."],
      ],
    });
  }

  function buildToolContainers() {
    return [
      card({ entity_id: "tools:capabilities", entity_type: "tool_container", role: "container", family: "capability", title: "Capacités", summary: "Skills · Functions · Workflows · Plugins · Connecteurs/MCP", status: "neutral", back: [["État", "Hiérarchie UX présente ; inventaire runtime non branché dans cette tranche."]] }),
      card({ entity_id: "tools:hosts", entity_type: "tool_container", role: "container", family: "runtime-host", title: "Postes", summary: "Runtime Hosts observés", status: "neutral", back: [["État", "Observation ≠ santé ≠ sécurité."]] }),
      card({ entity_id: "tools:models", entity_type: "tool_container", role: "container", family: "capability", title: "Modèles", summary: "Ressources modèle et observations par poste", status: "neutral", back: [["État", "Découvert ≠ configuré ≠ sélectionné ≠ autorisé."]] }),
      card({ entity_id: "tools:roles", entity_type: "tool_container", role: "container", family: "role-reference", title: "Références Pantheon", summary: "Rôles documentaires et lentilles de gouvernance", status: "neutral", back: [["Limite", "Rôle documenté ≠ agent runtime."]] }),
    ];
  }

  function rebuildGraph() {
    state.cards.clear();
    state.children.clear();
    state.parent.clear();

    for (const model of rootCards()) putCard(model);

    const documentIds = state.documents.map(item => putCard(normalizeDocument(item), state.project ? `project:${state.project}` : null));
    const knowledgeIds = state.knowledge.map(item => putCard(normalizeKnowledge(item), "space:connaissances"));
    const workIds = state.workIssues.map(item => putCard(normalizeWorkIssue(item), "space:decisions"));

    let projectIds = [];
    if (state.project) {
      const projectId = `project:${state.project}`;
      putCard(card({
        entity_id: projectId,
        entity_type: "project",
        role: "entity",
        family: "project",
        title: state.project,
        summary: `${state.documents.length} document(s) · ${state.knowledge.length} connaissance(s) · ${state.workIssues.length} sujet(s)`,
        status: "active",
        identity_accent: stableAccent(state.project),
        metrics: [
          { value: state.documents.length, label: "documents" },
          { value: state.workIssues.length, label: "attention" },
        ],
        back: [
          ["System of record", "PostgreSQL Agency Data (direction cible)."],
          ["Chargement actuel", "Cette tranche réutilise les endpoints projet existants ; la liste Agency Data globale n’est pas encore branchée."],
          ["Connaissances liées", `${state.knowledge.length} item(s) exposé(s) dans l’espace Connaissances.`],
        ],
      }), "space:affaires");
      projectIds = [projectId];
      setChildren(projectId, documentIds);
    }

    const reviewDocuments = state.documents
      .filter(item => (item.analysis_status || "partial") !== "ready")
      .map(item => `document:${item.document_id || item.card_id || item.source_ref}`)
      .filter(id => state.cards.has(id));
    const reviewKnowledge = state.knowledge
      .filter(item => ["generated_unreviewed", "needs_review"].includes(item.review_status || "generated_unreviewed"))
      .map(item => `knowledge:${item.knowledge_id || item.card_id}`)
      .filter(id => state.cards.has(id));

    setChildren("space:pantheon", []);
    setChildren("space:decisions", [...workIds, ...reviewDocuments, ...reviewKnowledge]);
    setChildren("space:affaires", projectIds);
    setChildren("space:connaissances", knowledgeIds);

    const tools = buildToolContainers();
    for (const model of tools) putCard(model, "space:outils");
    setChildren("space:outils", tools.map(model => model.entity_id));

    state.navigator = window.PantheonSpatialNavigation.create({
      root_collection_id: "primary-spaces",
      root_item_ids: ROOT_SPACES.map(space => `space:${space}`),
    });
  }

  function familyMark(model) {
    return FAMILY_MARKS[model.family] || model.family.slice(0, 2).toUpperCase();
  }

  function orb(value, label, kind = "metric") {
    const node = document.createElement("span");
    node.className = `v2-orb v2-orb--${kind}`;
    node.title = label || String(value);
    const valueNode = document.createElement("strong");
    valueNode.textContent = String(value);
    node.append(valueNode);
    return node;
  }

  function renderTags(model, rail) {
    const tags = (model.tags || []).slice(0, 3);
    for (const tag of tags) rail.append(orb(typeof tag === "string" ? tag.slice(0, 2).toUpperCase() : (tag.name || "T").slice(0, 2).toUpperCase(), typeof tag === "string" ? tag : tag.name, "tag"));
    if ((model.tags || []).length > 3) rail.append(orb(`+${model.tags.length - 3}`, "Tags supplémentaires", "tag"));
  }

  function renderFront(model) {
    const face = document.createElement("div");
    face.className = "v2-card-face v2-card-front";

    const top = document.createElement("header");
    top.className = "v2-card-top";
    const index = document.createElement("span");
    index.className = "v2-index";
    index.textContent = model.index || (model.role === "container" ? "↳" : familyMark(model));
    const status = orb(statusLabel(model.status).slice(0, 2).toUpperCase(), statusLabel(model.status), "status");
    top.append(index, status);

    const body = document.createElement("div");
    body.className = "v2-card-body";
    if (model.front?.issuer) {
      const issuer = document.createElement("p");
      issuer.className = "v2-card-kicker";
      issuer.textContent = model.front.issuer;
      body.append(issuer);
    }
    const title = document.createElement("h2");
    title.className = "v2-card-title";
    title.textContent = model.title;
    const summary = document.createElement("p");
    summary.className = "v2-card-summary";
    summary.textContent = model.summary;
    body.append(title, summary);

    const footer = document.createElement("footer");
    footer.className = "v2-card-footer";
    const mark = document.createElement("span");
    mark.className = "v2-family-mark";
    mark.textContent = familyMark(model);
    mark.title = model.family;
    const rail = document.createElement("div");
    rail.className = "v2-indicator-rail";
    renderTags(model, rail);
    for (const metric of (model.metrics || []).slice(0, 2)) rail.append(orb(metric.value, metric.label, "metric"));
    footer.append(mark, rail);
    face.append(top, body, footer);
    return face;
  }

  function renderBack(model) {
    const face = document.createElement("div");
    face.className = "v2-card-face v2-card-back";
    const header = document.createElement("header");
    header.className = "v2-card-top";
    const label = document.createElement("span");
    label.className = "v2-card-kicker";
    label.textContent = `${model.family} · ${model.entity_type}`;
    header.append(label, orb(statusLabel(model.status).slice(0, 2).toUpperCase(), statusLabel(model.status), "status"));

    const body = document.createElement("div");
    body.className = "v2-back-body";
    const title = document.createElement("h2");
    title.className = "v2-back-title";
    title.textContent = model.title;
    body.append(title);
    for (const [heading, value] of model.back || []) {
      const row = document.createElement("section");
      row.className = "v2-back-section";
      const h = document.createElement("h3");
      h.textContent = heading;
      const p = document.createElement("p");
      p.textContent = String(value);
      row.append(h, p);
      body.append(row);
    }

    const footer = document.createElement("footer");
    footer.className = "v2-card-footer";
    const identity = document.createElement("span");
    identity.className = "v2-entity-id";
    identity.textContent = model.entity_id;
    const rail = document.createElement("div");
    rail.className = "v2-indicator-rail";
    renderTags(model, rail);
    footer.append(identity, rail);
    face.append(header, body, footer);
    return face;
  }

  function renderCard(model) {
    const wrapper = document.createElement("article");
    wrapper.className = "v2-card";
    wrapper.dataset.family = model.family;
    wrapper.dataset.role = model.role;
    wrapper.dataset.status = model.status;
    wrapper.dataset.flipped = state.flipped.has(model.entity_id) ? "true" : "false";
    wrapper.style.setProperty("--identity-accent", model.identity_accent || stableAccent(model.entity_id));
    const inner = document.createElement("div");
    inner.className = "v2-card-inner";
    inner.append(renderFront(model), renderBack(model));
    wrapper.append(inner);
    return wrapper;
  }

  function currentModel() {
    return state.cards.get(state.navigator?.currentId()) || null;
  }

  function breadcrumbLabels() {
    const snap = state.navigator.snapshot();
    const labels = snap.path.map(part => state.cards.get(part.current_id)?.title).filter(Boolean);
    return labels;
  }

  function setMessage(message) {
    $("v2-status").textContent = message;
  }

  function updateSpaceRail() {
    const rootCurrent = state.navigator.snapshot().path[0]?.current_id;
    for (const button of document.querySelectorAll("[data-space]")) {
      button.classList.toggle("is-active", `space:${button.dataset.space}` === rootCurrent);
    }
  }

  function render() {
    if (!state.navigator) return;
    const snap = state.navigator.snapshot();
    const model = currentModel();
    const stage = $("v2-stage");
    stage.replaceChildren();
    stage.dataset.motion = state.lastMove;

    if (!model) {
      const empty = document.createElement("div");
      empty.className = "v2-empty";
      empty.textContent = "Aucune carte dans cette collection.";
      stage.append(empty);
    } else {
      stage.append(renderCard(model));
    }

    const breadcrumb = $("v2-breadcrumb");
    breadcrumb.textContent = breadcrumbLabels().join(" / ");

    const previous = $("v2-previous");
    const next = $("v2-next");
    const ascend = $("v2-ascend");
    const descend = $("v2-descend");
    previous.disabled = !snap.can_move_previous;
    next.disabled = !snap.can_move_next;
    ascend.disabled = !snap.can_ascend;
    descend.disabled = !model || !(state.children.get(model.entity_id) || []).length;

    $("v2-flip").disabled = !model;
    $("v2-scope").textContent = model ? `${model.title} · portée carte courante` : "Aucun contexte";
    updateSpaceRail();
  }

  function moveHorizontal(delta) {
    state.lastMove = delta < 0 ? "right" : "left";
    state.navigator.moveHorizontal(delta);
    render();
  }

  function descend() {
    const model = currentModel();
    if (!model) return;
    const children = state.children.get(model.entity_id) || [];
    if (!children.length) {
      toggleFlip();
      setMessage("Cette carte n’a pas d’enfant déclaré ; verso affiché à la place.");
      return;
    }
    state.lastMove = "up";
    state.navigator.descend({
      parent_entity_id: model.entity_id,
      collection_id: `children:${model.entity_id}`,
      item_ids: children,
    });
    render();
  }

  function ascend() {
    if (!state.navigator.snapshot().can_ascend) return;
    state.lastMove = "down";
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
    state.lastMove = "root";
    state.navigator.returnToRoot(`space:${space}`);
    render();
  }

  async function api(path) {
    const response = await fetch(path, { headers: { Authorization: `Bearer ${state.token}` } });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(payload.detail || response.statusText);
    }
    return response.json();
  }

  async function loadProject() {
    state.project = $("v2-project").value.trim();
    state.token = $("v2-token").value;
    if (!state.project || !state.token) {
      setMessage("Projet et clé d’accès requis pour charger les projections existantes.");
      return;
    }
    $("v2-load").disabled = true;
    setMessage("Chargement des projections projet…");
    try {
      const [documents, knowledge, workIssues] = await Promise.all([
        api(`../v1/projects/${encodeURIComponent(state.project)}/documents`),
        api(`../v1/projects/${encodeURIComponent(state.project)}/knowledge`),
        api(`../v1/projects/${encodeURIComponent(state.project)}/work-issues`),
      ]);
      state.documents = documents.documents || [];
      state.knowledge = knowledge.knowledge || [];
      state.workIssues = workIssues.work_issues || [];
      rebuildGraph();
      state.navigator.returnToRoot("space:affaires");
      render();
      setMessage(`Projet ${state.project} chargé dans la hiérarchie V2.`);
    } catch (error) {
      state.documents = [];
      state.knowledge = [];
      state.workIssues = [];
      rebuildGraph();
      render();
      setMessage(`Chargement refusé : ${error.message}`);
    } finally {
      $("v2-load").disabled = false;
    }
  }

  function bindGestures() {
    const stage = $("v2-stage");
    let start = null;
    stage.addEventListener("pointerdown", event => {
      start = { x: event.clientX, y: event.clientY, id: event.pointerId };
      stage.setPointerCapture?.(event.pointerId);
    });
    stage.addEventListener("pointerup", event => {
      if (!start || start.id !== event.pointerId) return;
      const dx = event.clientX - start.x;
      const dy = event.clientY - start.y;
      start = null;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 54) return;
      if (Math.abs(dx) > Math.abs(dy)) moveHorizontal(dx < 0 ? 1 : -1);
      else if (dy < 0) descend();
      else ascend();
    });
  }

  function bindControls() {
    $("v2-previous").addEventListener("click", () => moveHorizontal(-1));
    $("v2-next").addEventListener("click", () => moveHorizontal(1));
    $("v2-ascend").addEventListener("click", ascend);
    $("v2-descend").addEventListener("click", descend);
    $("v2-flip").addEventListener("click", toggleFlip);
    $("v2-load").addEventListener("click", loadProject);
    document.querySelectorAll("[data-space]").forEach(button => button.addEventListener("click", () => jumpToSpace(button.dataset.space)));
    document.addEventListener("keydown", event => {
      if (["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;
      const actions = {
        ArrowLeft: () => moveHorizontal(-1),
        ArrowRight: () => moveHorizontal(1),
        ArrowUp: descend,
        ArrowDown: ascend,
        Enter: descend,
        " ": toggleFlip,
      };
      const action = actions[event.key];
      if (action) {
        event.preventDefault();
        action();
      }
    });
    bindGestures();
  }

  function setNetwork() {
    $("v2-network").textContent = navigator.onLine ? "en ligne" : "hors ligne";
  }

  rebuildGraph();
  bindControls();
  setNetwork();
  window.addEventListener("online", setNetwork);
  window.addEventListener("offline", setNetwork);
  render();
})();
