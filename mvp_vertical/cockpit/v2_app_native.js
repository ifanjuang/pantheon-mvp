(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const ROOT_SPACES = ["pantheon", "decisions", "affaires", "connaissances", "outils"];
  const STATUS_LABELS = {
    ready: "Prêt", reviewed: "Revu", done: "Clôturé", in_progress: "En cours",
    waiting: "En attente", review: "À examiner", needs_review: "À examiner",
    generated_unreviewed: "Non revu", partial: "Partiel", conflict: "Conflit",
    failed: "Échec", draft: "Brouillon", open: "Ouvert", active: "Actif",
    inactive: "Inactif", neutral: "Référence",
  };
  const FAMILY_MARKS = {
    pantheon: "P", decision: "D", project: "A", document: "DOC", evidence: "EV",
    knowledge: "K", capability: "#", "runtime-host": "H", "role-reference": "R",
    contact: "C", work: "W", information: "I", tool: "#",
  };
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

  const registries = {
    typeTags: new Map(), subjectTags: new Map(), statuses: new Map(), limits: new Map(),
  };

  const state = {
    project: "", token: "", projects: [], documents: [], knowledge: [], workIssues: [],
    cards: new Map(), children: new Map(), parent: new Map(), flipped: new Set(), navigator: null, lastMove: "none",
  };

  const slug = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const text = (value, fallback = "") => value == null || value === "" ? fallback : String(value);
  const statusLabel = status => STATUS_LABELS[status] || String(status || "À vérifier").replaceAll("_", " ");

  function stableAccent(value) {
    const input = String(value || "project");
    let hash = 0;
    for (let index = 0; index < input.length; index += 1) hash = ((hash << 5) - hash + input.charCodeAt(index)) | 0;
    return PROJECT_ACCENTS[Math.abs(hash) % PROJECT_ACCENTS.length];
  }

  async function loadRegistry(path, collectionKey, map) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      for (const item of payload[collectionKey] || []) map.set(slug(item.slug || item.title), item);
    } catch (_) {
      // Presentation registries are non-authoritative. Cockpit remains usable if unavailable.
    }
  }

  function registryEntry(map, value) { return map.get(slug(value)) || null; }
  function setTokenColor(node, entry) {
    if (entry?.color) node.dataset.tokenColor = entry.color;
    if (entry?.icon_key) node.dataset.iconKey = entry.icon_key;
  }

  function card(input) {
    const structured = window.PantheonStructuredInterface;
    const projection = structured?.buildCardProjection?.(input) || {};
    const candidate = {
      role: "entity", family: "project", status: "neutral", summary: "", tags: [], metrics: [], front: {}, back: [],
      ...input,
      ...projection,
      presentation_family: projection.presentation_family || input.presentation_family || input.family,
    };
    const validation = structured?.validateCardModel?.(candidate);
    if (validation && !validation.valid) throw new Error(`Invalid V2 card ${candidate.entity_id}: ${validation.errors.join(", ")}`);
    return candidate;
  }

  function putCard(model, parentId = null) {
    state.cards.set(model.entity_id, model);
    if (parentId) state.parent.set(model.entity_id, parentId);
    return model.entity_id;
  }
  function setChildren(parentId, childIds) { state.children.set(parentId, [...childIds].filter(Boolean)); }

  function rootCards() {
    return [
      card({ entity_id: "space:pantheon", entity_type: "cockpit_space", role: "conversation", family: "pantheon", title: "Pantheon", summary: "Dialogue gouverné et contexte explicite.", status: "active", back: [["Rôle", "Exposer le contexte, les décisions et l’état gouverné sans devenir runtime."]] }),
      card({ entity_id: "space:decisions", entity_type: "cockpit_space", role: "container", family: "decision", presentation_family: "decision", title: "Décisions", summary: "Tout ce qui demande une attention humaine.", status: "review", back: [["Projection", "Validation, questions, arbitrages et décisions formelles."]] }),
      card({ entity_id: "space:affaires", entity_type: "cockpit_space", role: "container", family: "project", title: "Affaires", summary: "Projets et informations métier.", status: "active", back: [["Source métier", "PostgreSQL Agency Data est le system of record natif."], ["Notion", "Projection collaborative optionnelle."]] }),
      card({ entity_id: "space:connaissances", entity_type: "cockpit_space", role: "container", family: "knowledge", presentation_family: "information", title: "Connaissances", summary: "Références réutilisables et état de revue.", status: "neutral", back: [["Principe", "Knowledge reste distinct de Document, Evidence et mémoire gouvernée."]] }),
      card({ entity_id: "space:outils", entity_type: "cockpit_space", role: "container", family: "capability", presentation_family: "tool", title: "Outils", summary: "Capacités, postes et ressources Pantheon.", status: "neutral", back: [["Principe", "Installé ≠ approuvé · healthy ≠ safe · sélectionné ≠ autorisé."]] }),
    ];
  }

  function projectEntityId(item) { return `project:${item.project_id || item.entity_id || item.code || item.display_name}`; }

  function normalizeProject(item, { selected = false } = {}) {
    const projectId = item.project_id || item.entity_id || item.code || item.display_name;
    const title = item.display_name || item.code || projectId || "Affaire";
    const contactCount = Array.isArray(item.contacts) ? item.contacts.length : 0;
    return card({
      entity_id: projectEntityId(item), entity_type: "project", role: "entity", family: "project", presentation_family: "project",
      category: "Projet", title,
      summary: selected ? `${state.documents.length} information(s) · ${contactCount} contact(s) · ${state.workIssues.length} travail(aux)` : [item.code && item.code !== title ? item.code : null, item.phase, item.location].filter(Boolean).join(" · ") || "Affaire Agency Data",
      status: item.status || "active", subject_tags: Array.isArray(item.tags) ? item.tags : [],
      identity_accent: stableAccent(projectId), index: item.display_index || item.index || null, date: item.updated_at || null,
      front: { issuer: item.primary_client || null },
      back: [["Code", text(item.code, "Non renseigné")], ["Phase", text(item.phase, "Non renseignée")], ["Lieu", text(item.location, "Non renseigné")], ["Maîtrise d’ouvrage", text(item.primary_client, "Non renseignée")], ["Révision technique", text(item.revision, "Non renseignée")]],
      source_project_id: String(projectId || ""),
    });
  }

  function normalizeDocument(item) {
    const naming = item.naming || {};
    const id = item.document_id || item.card_id || item.source_ref || crypto.randomUUID();
    const category = naming.document_type || item.category || "Information";
    return card({
      entity_id: `document:${id}`, entity_type: "document", role: "entity", family: "document", presentation_family: "information",
      category, title: naming.object_name || item.title || category,
      summary: item.summary || [naming.document_type, naming.phase_code].filter(Boolean).join(" · ") || "Information projet",
      status: item.status || item.analysis_status || "partial", index: naming.revision_index || item.index || null,
      date: item.document_date || item.date || item.created_at || null, author: item.author || naming.issuer || item.issuer || null,
      type_tags: item.type_tags || [slug(category)], subject_tags: item.subject_tags || item.tags || [], limits: item.limits || [],
      back: [["Résumé", text(item.summary, "Résumé non renseigné")], ["Informations détaillées", text(item.details, "Informations détaillées non renseignées")], ["Source", text(item.source_ref, "Note ou source non exposée")], ["Auteur", text(item.author || naming.issuer || item.issuer, "Non renseigné")]],
      source_refs: [item.source_ref].filter(Boolean),
    });
  }

  function normalizeKnowledge(item) {
    const id = item.knowledge_id || item.card_id || crypto.randomUUID();
    return card({
      entity_id: `knowledge:${id}`, entity_type: "knowledge", role: "entity", family: "knowledge", presentation_family: "information",
      category: item.family || "Référence", title: item.title || "Knowledge", summary: item.summary || `Version ${item.version || 1}`,
      status: item.review_status || "generated_unreviewed", index: item.index || null, date: item.updated_at || null, author: item.author || null,
      type_tags: item.type_tags || ["etude"], subject_tags: item.subject_tags || item.tags || [], limits: item.limits || ["consultatif"],
      back: [["Résumé", text(item.summary, "Résumé non renseigné")], ["Informations détaillées", text(item.markdown, "Contenu non exposé")], ["Document lié", text(item.document_ref, "Non renseigné")], ["Limite", "Knowledge ≠ Evidence · Knowledge ≠ mémoire gouvernée."]],
      source_refs: (item.source_chunk_refs || []).filter(Boolean),
    });
  }

  function normalizeWorkIssue(projection) {
    const issue = projection.work_issue || projection;
    const id = issue.issue_id || crypto.randomUUID();
    return card({
      entity_id: `work:${id}`, entity_type: "work_issue", role: "entity", family: "work", presentation_family: "work",
      category: "Travail", title: issue.title || "Travail à examiner", summary: issue.description || `${text(issue.issue_type, "action")} · priorité ${text(issue.priority, "normale")}`,
      status: issue.status || "open", subject_tags: issue.tags || [],
      back: [["Objectif", text(issue.description, "Description non renseignée")], ["Responsable", text(issue.assigned_to, "Non assigné")], ["Effet demandé", text(issue.requested_effect, "Non renseigné")], ["Task Contract", text(issue.task_contract_ref, "Non renseigné")], ["Context Pack", text(issue.context_pack_ref, "Non renseigné")]],
    });
  }

  function contactDisplay(item) {
    const identity = [item.name, item.organization].filter(Boolean).join(" · ");
    const role = item.role ? ` — ${item.role}` : "";
    const details = [item.email, item.phone].filter(Boolean).join(" · ");
    return `${identity || "Contact non renseigné"}${role}${details ? `\n${details}` : ""}`;
  }

  function normalizeContacts(projectId, contacts = []) {
    const groups = new Map(CONTACT_GROUPS.map(name => [name, []]));
    for (const item of Array.isArray(contacts) ? contacts : []) {
      const group = CONTACT_GROUPS.includes(item.group) ? item.group : "Autres intervenants";
      groups.get(group).push(item);
    }
    const back = [];
    for (const group of CONTACT_GROUPS) {
      const values = groups.get(group) || [];
      if (!values.length) continue;
      back.push([group, values.map(contactDisplay).join("\n")]);
    }
    return card({
      entity_id: `project:${projectId}:contacts`, entity_type: "project_contacts", role: "entity", family: "contact", presentation_family: "contact",
      category: "Contacts", title: "Contacts", summary: `${Array.isArray(contacts) ? contacts.length : 0} contact(s) classé(s) par groupe projet`, status: "neutral",
      identity_accent: stableAccent(projectId), back: back.length ? back : [["Contacts", "Aucun contact renseigné pour cette affaire."]],
      source_project_id: projectId,
    });
  }

  function buildToolContainers() {
    return [
      card({ entity_id: "tools:capabilities", entity_type: "tool_container", role: "container", family: "tool", presentation_family: "tool", category: "Outil", type_tags: ["outil"], title: "Capacités", summary: "Skills · Functions · Workflows · Plugins · Connecteurs/MCP", status: "neutral", back: [["État", "Hiérarchie UX présente ; inventaire runtime non branché dans cette tranche."]] }),
      card({ entity_id: "tools:hosts", entity_type: "tool_container", role: "container", family: "tool", presentation_family: "tool", category: "Outil", type_tags: ["outil"], title: "Postes", summary: "Runtime Hosts observés", status: "neutral", back: [["État", "Observation ≠ santé ≠ sécurité."]] }),
      card({ entity_id: "tools:roles", entity_type: "tool_container", role: "container", family: "tool", presentation_family: "tool", category: "Référence", title: "Références Pantheon", summary: "Rôles documentaires et lentilles de gouvernance", status: "neutral", back: [["Limite", "Rôle documenté ≠ agent runtime."]] }),
    ];
  }

  function projectLookup() {
    const wanted = state.project.trim().toLocaleLowerCase("fr-FR");
    if (!wanted) return null;
    return state.projects.find(item => [item.project_id, item.code, item.display_name].filter(Boolean).some(value => String(value).toLocaleLowerCase("fr-FR") === wanted)) || null;
  }

  function rebuildGraph() {
    state.cards.clear(); state.children.clear(); state.parent.clear();
    for (const model of rootCards()) putCard(model);

    const selected = projectLookup();
    const selectedProjectId = selected?.project_id || state.project || null;
    const selectedCardId = selected ? projectEntityId(selected) : selectedProjectId ? `project:${selectedProjectId}` : null;

    const documentIds = state.documents.map(item => putCard(normalizeDocument(item), selectedCardId));
    const knowledgeIds = state.knowledge.map(item => putCard(normalizeKnowledge(item), "space:connaissances"));
    const workIds = state.workIssues.map(item => putCard(normalizeWorkIssue(item), "space:decisions"));

    const projectIds = [];
    for (const item of state.projects) projectIds.push(putCard(normalizeProject(item, { selected: item.project_id === selectedProjectId }), "space:affaires"));
    if (selectedProjectId && !projectIds.includes(selectedCardId)) projectIds.push(putCard(normalizeProject({ project_id: selectedProjectId, code: selectedProjectId, display_name: selectedProjectId, status: "active", contacts: [] }, { selected: true }), "space:affaires"));

    if (selectedCardId && state.cards.has(selectedCardId)) {
      const contacts = normalizeContacts(selectedProjectId, selected?.contacts || []);
      const contactsId = putCard(contacts, selectedCardId);
      setChildren(contactsId, []);
      setChildren(selectedCardId, [contactsId, ...documentIds]);
    }

    const reviewDocuments = state.documents.filter(item => (item.analysis_status || "partial") !== "ready")
      .map(item => `document:${item.document_id || item.card_id || item.source_ref}`).filter(id => state.cards.has(id));
    const reviewKnowledge = state.knowledge.filter(item => ["generated_unreviewed", "needs_review"].includes(item.review_status || "generated_unreviewed"))
      .map(item => `knowledge:${item.knowledge_id || item.card_id}`).filter(id => state.cards.has(id));

    setChildren("space:pantheon", []);
    setChildren("space:decisions", [...workIds, ...reviewDocuments, ...reviewKnowledge]);
    setChildren("space:affaires", projectIds);
    setChildren("space:connaissances", knowledgeIds);
    const tools = buildToolContainers();
    for (const model of tools) putCard(model, "space:outils");
    setChildren("space:outils", tools.map(model => model.entity_id));
    state.navigator = window.PantheonSpatialNavigation.create({ root_collection_id: "primary-spaces", root_item_ids: ROOT_SPACES.map(space => `space:${space}`) });
  }

  function familyMark(model) { return FAMILY_MARKS[model.presentation_family] || FAMILY_MARKS[model.family] || String(model.family || "?").slice(0, 2).toUpperCase(); }
  function familyLabel(model) {
    return ({ project: "Projet", information: "Information", contact: "Contacts", work: "Travail", decision: "Décision", tool: "Outil", pantheon: "Pantheon" })[model.presentation_family] || model.category || model.family;
  }

  function tagToken(value, kind) {
    const map = kind === "type" ? registries.typeTags : registries.subjectTags;
    const entry = registryEntry(map, value);
    const node = document.createElement("span");
    node.className = kind === "type" ? "v2-type-tag" : "v2-subject-tag-icon";
    node.title = entry?.description || entry?.title || String(value);
    node.setAttribute("aria-label", entry?.title || String(value));
    setTokenColor(node, entry);
    const short = entry?.title || String(value);
    node.textContent = short.length <= 3 ? short.toUpperCase() : short.slice(0, 2).toUpperCase();
    return node;
  }

  function stateToken(value, kind = "status") {
    const entry = registryEntry(kind === "limit" ? registries.limits : registries.statuses, value);
    const node = document.createElement("span");
    node.className = "v2-state-icon";
    node.title = entry?.title || statusLabel(value);
    node.setAttribute("aria-label", node.title);
    setTokenColor(node, entry);
    node.textContent = (entry?.title || statusLabel(value)).slice(0, 2).toUpperCase();
    return node;
  }

  function renderIdentity(model) {
    const identity = document.createElement("div"); identity.className = "v2-card-identity";
    const line = document.createElement("div"); line.className = "v2-card-identity-line";
    const mark = document.createElement("span"); mark.className = "v2-family-mark v2-family-mark--identity"; mark.textContent = familyMark(model); mark.title = familyLabel(model);
    const category = document.createElement("span"); category.className = "v2-card-category"; category.textContent = model.category || familyLabel(model);
    const typeTags = document.createElement("span"); typeTags.className = "v2-card-type-tags";
    for (const tag of (model.type_tags || []).slice(0, 4)) typeTags.append(tagToken(tag, "type"));
    line.append(mark, category, typeTags);
    const meta = document.createElement("div"); meta.className = "v2-card-meta";
    meta.textContent = [model.index, model.date ? String(model.date).slice(0, 10) : null].filter(Boolean).join(" · ");
    identity.append(line, meta);
    return identity;
  }

  function renderStates(model) {
    const states = document.createElement("div"); states.className = "v2-card-states";
    states.append(stateToken(model.status, "status"));
    for (const limit of (model.limits || []).slice(0, 3)) states.append(stateToken(limit, "limit"));
    return states;
  }

  function renderFront(model) {
    const face = document.createElement("div"); face.className = "v2-card-face v2-card-front";
    const top = document.createElement("header"); top.className = "v2-card-top"; top.append(renderIdentity(model), renderStates(model));
    const body = document.createElement("div"); body.className = "v2-card-body";
    if (model.front?.issuer) { const issuer = document.createElement("p"); issuer.className = "v2-card-kicker"; issuer.textContent = model.front.issuer; body.append(issuer); }
    const title = document.createElement("h2"); title.className = "v2-card-title"; title.textContent = model.title;
    const summary = document.createElement("p"); summary.className = "v2-card-summary"; summary.textContent = model.summary;
    body.append(title, summary);
    const footer = document.createElement("footer"); footer.className = "v2-card-footer";
    const rail = document.createElement("div"); rail.className = "v2-indicator-rail";
    for (const tag of (model.subject_tags || []).slice(0, 5)) rail.append(tagToken(tag, "subject"));
    footer.append(rail);
    face.append(top, body, footer); return face;
  }

  function renderBackValue(value) {
    const p = document.createElement("p");
    const lines = String(value ?? "").split("\n").filter(Boolean);
    if (lines.length <= 1) { p.textContent = String(value ?? ""); return p; }
    p.className = "v2-back-multiline";
    for (const line of lines) { const span = document.createElement("span"); span.textContent = line; p.append(span); }
    return p;
  }

  function renderBack(model) {
    const face = document.createElement("div"); face.className = "v2-card-face v2-card-back";
    const header = document.createElement("header"); header.className = "v2-card-top";
    const identity = renderIdentity(model); const states = renderStates(model); header.append(identity, states);
    const legacyKicker = document.createElement("span"); legacyKicker.className = "v2-card-kicker v2-card-kicker--machine"; legacyKicker.textContent = `${model.family} · ${model.entity_type}`; legacyKicker.hidden = true; header.append(legacyKicker);
    const body = document.createElement("div"); body.className = "v2-back-body";
    const title = document.createElement("h2"); title.className = "v2-back-title"; title.textContent = model.title; body.append(title);
    for (const [heading, value] of model.back || []) {
      const row = document.createElement("section"); row.className = "v2-back-section";
      const h = document.createElement("h3"); h.textContent = heading; row.append(h, renderBackValue(value)); body.append(row);
    }
    const footer = document.createElement("footer"); footer.className = "v2-card-footer";
    const actions = document.createElement("div"); actions.className = "v2-card-actions";
    for (const action of model.available_actions || []) { const button = document.createElement("button"); button.type = "button"; button.textContent = action; button.disabled = true; button.title = "Action affichable uniquement lorsqu’elle est autorisée par le serveur"; actions.append(button); }
    const labels = document.createElement("div"); labels.className = "v2-back-tag-labels";
    for (const tag of model.subject_tags || []) {
      const entry = registryEntry(registries.subjectTags, tag); const chip = document.createElement("span"); chip.className = "v2-back-tag-label"; chip.textContent = entry?.title || tag; setTokenColor(chip, entry); labels.append(chip);
    }
    const machineIdentity = document.createElement("span"); machineIdentity.className = "v2-entity-id"; machineIdentity.textContent = model.entity_id; machineIdentity.hidden = true;
    footer.append(actions, labels, machineIdentity); face.append(header, body, footer); return face;
  }

  function renderCard(model) {
    const wrapper = document.createElement("article"); wrapper.className = "v2-card";
    wrapper.dataset.family = model.presentation_family || model.family; wrapper.dataset.role = model.role; wrapper.dataset.status = model.status;
    wrapper.dataset.flipped = state.flipped.has(model.entity_id) ? "true" : "false";
    wrapper.style.setProperty("--identity-accent", model.identity_accent || stableAccent(model.entity_id));
    const inner = document.createElement("div"); inner.className = "v2-card-inner"; inner.append(renderFront(model), renderBack(model)); wrapper.append(inner); return wrapper;
  }

  function currentModel() { return state.cards.get(state.navigator?.currentId()) || null; }
  function breadcrumbLabels() { return state.navigator.snapshot().path.map(part => state.cards.get(part.current_id)?.title).filter(Boolean); }
  function setMessage(message) { $("v2-status").textContent = message; }
  function updateSpaceRail() {
    const rootCurrent = state.navigator.snapshot().path[0]?.current_id;
    for (const button of document.querySelectorAll("[data-space]")) button.classList.toggle("is-active", `space:${button.dataset.space}` === rootCurrent);
  }

  function render() {
    if (!state.navigator) return;
    const snap = state.navigator.snapshot(); const model = currentModel(); const stage = $("v2-stage"); stage.replaceChildren(); stage.dataset.motion = state.lastMove;
    if (!model) { const empty = document.createElement("div"); empty.className = "v2-empty"; empty.textContent = "Aucune carte dans cette collection."; stage.append(empty); }
    else stage.append(renderCard(model));
    $("v2-breadcrumb").textContent = breadcrumbLabels().join(" / ");
    $("v2-previous").disabled = !snap.can_move_previous; $("v2-next").disabled = !snap.can_move_next; $("v2-ascend").disabled = !snap.can_ascend;
    $("v2-descend").disabled = !model || (!(state.children.get(model.entity_id) || []).length && model.entity_type !== "project"); $("v2-flip").disabled = !model;
    updateSpaceRail();
  }

  function moveHorizontal(delta) { state.lastMove = delta < 0 ? "right" : "left"; state.navigator.moveHorizontal(delta); render(); }
  async function descend() {
    const model = currentModel(); if (!model) return; const children = state.children.get(model.entity_id) || [];
    if (!children.length && model.entity_type === "project" && model.source_project_id && model.source_project_id !== state.project) { $("v2-project").value = model.source_project_id; await loadProject({ focusProject: true }); return; }
    if (!children.length) { toggleFlip(); setMessage("Cette carte n’a pas d’enfant déclaré ; verso affiché à la place."); return; }
    state.lastMove = "up"; state.navigator.descend({ parent_entity_id: model.entity_id, collection_id: `children:${model.entity_id}`, item_ids: children }); render();
  }
  function ascend() { if (!state.navigator.snapshot().can_ascend) return; state.lastMove = "down"; state.navigator.ascend(); render(); }
  function toggleFlip() { const model = currentModel(); if (!model) return; if (state.flipped.has(model.entity_id)) state.flipped.delete(model.entity_id); else state.flipped.add(model.entity_id); render(); }
  function jumpToSpace(space) { state.lastMove = "root"; state.navigator.returnToRoot(`space:${space}`); render(); }

  async function api(path) {
    const response = await fetch(path, { headers: { Authorization: `Bearer ${state.token}` } });
    if (!response.ok) { const payload = await response.json().catch(() => ({ detail: response.statusText })); throw new Error(payload.detail || response.statusText); }
    return response.json();
  }
  async function loadAgencyProjects() { const payload = await api("../v1/agency/projects?limit=200"); state.projects = payload.projects || []; return state.projects; }

  async function loadProject(options = {}) {
    const focusProject = Boolean(options.focusProject); const requested = $("v2-project").value.trim(); state.token = $("v2-token").value;
    if (!state.token) { setMessage("Clé d’accès requise pour lire Agency Data."); return; }
    $("v2-load").disabled = true; setMessage("Chargement d’Agency Data…");
    try {
      await loadAgencyProjects(); state.project = requested; const matched = projectLookup();
      if (matched?.project_id) { state.project = matched.project_id; $("v2-project").value = matched.code || matched.display_name || matched.project_id; }
      if (!state.project) { state.documents = []; state.knowledge = []; state.workIssues = []; rebuildGraph(); state.navigator.returnToRoot("space:affaires"); render(); setMessage(`${state.projects.length} affaire(s) Agency Data chargée(s). ↑ pour ouvrir la collection.`); return; }
      setMessage(`Chargement des projections de ${state.project}…`);
      const [documents, knowledge, workIssues] = await Promise.all([
        api(`../v1/projects/${encodeURIComponent(state.project)}/documents`),
        api(`../v1/projects/${encodeURIComponent(state.project)}/knowledge`),
        api(`../v1/projects/${encodeURIComponent(state.project)}/work-issues`),
      ]);
      state.documents = documents.documents || []; state.knowledge = knowledge.knowledge || []; state.workIssues = workIssues.work_issues || [];
      rebuildGraph(); state.navigator.returnToRoot("space:affaires");
      if (focusProject || state.project) { const projectIds = state.children.get("space:affaires") || []; const target = projectIds.find(id => state.cards.get(id)?.source_project_id === state.project); if (target) state.navigator.descend({ parent_entity_id: "space:affaires", collection_id: "children:space:affaires", item_ids: projectIds, initial_entity_id: target }); }
      render(); setMessage(`Affaire ${matched?.display_name || matched?.code || state.project} chargée dans la hiérarchie V2.`);
    } catch (error) {
      state.documents = []; state.knowledge = []; state.workIssues = []; rebuildGraph(); render(); setMessage(`Chargement refusé : ${error.message}`);
    } finally { $("v2-load").disabled = false; }
  }

  function bindGestures() {
    const stage = $("v2-stage"); let start = null;
    stage.addEventListener("pointerdown", event => { start = { x: event.clientX, y: event.clientY, id: event.pointerId }; stage.setPointerCapture?.(event.pointerId); });
    stage.addEventListener("pointerup", event => { if (!start || start.id !== event.pointerId) return; const dx = event.clientX - start.x; const dy = event.clientY - start.y; start = null; if (Math.max(Math.abs(dx), Math.abs(dy)) < 54) return; if (Math.abs(dx) > Math.abs(dy)) moveHorizontal(dx < 0 ? 1 : -1); else if (dy < 0) void descend(); else ascend(); });
  }
  function bindControls() {
    $("v2-previous").addEventListener("click", () => moveHorizontal(-1)); $("v2-next").addEventListener("click", () => moveHorizontal(1)); $("v2-ascend").addEventListener("click", ascend);
    $("v2-descend").addEventListener("click", () => void descend()); $("v2-flip").addEventListener("click", toggleFlip); $("v2-load").addEventListener("click", () => void loadProject());
    document.querySelectorAll("[data-space]").forEach(button => button.addEventListener("click", () => jumpToSpace(button.dataset.space)));
    document.addEventListener("keydown", event => { if (["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) return; const actions = { ArrowLeft: () => moveHorizontal(-1), ArrowRight: () => moveHorizontal(1), ArrowUp: () => void descend(), ArrowDown: ascend, Enter: () => void descend(), " ": toggleFlip }; const action = actions[event.key]; if (action) { event.preventDefault(); action(); } }); bindGestures();
  }
  function setNetwork() { $("v2-network").textContent = navigator.onLine ? "en ligne" : "hors ligne"; }

  async function init() {
    await Promise.all([
      loadRegistry("registries/type_tags.json", "tags", registries.typeTags), loadRegistry("registries/subject_tags.json", "tags", registries.subjectTags),
      loadRegistry("registries/status_registry.json", "values", registries.statuses), loadRegistry("registries/limit_registry.json", "values", registries.limits),
    ]);
    rebuildGraph(); bindControls(); setNetwork(); window.addEventListener("online", setNetwork); window.addEventListener("offline", setNetwork); render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => void init(), { once: true }); else void init();
})();
