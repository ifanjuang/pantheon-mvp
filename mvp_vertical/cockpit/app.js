const $ = id => document.getElementById(id);

const state = {
  project: "",
  token: "",
  scene: "now",
  documents: [],
  knowledge: [],
};

const sceneCopy = {
  now: ["MAINTENANT", "Cartes à examiner"],
  documents: ["DOCUMENTS", "Sources et représentations dérivées"],
  knowledge: ["KNOWLEDGE", "Connaissances éditoriales à revoir"],
  questionnaire: ["QUESTIONNAIRE", "Préciser une demande"],
};

const statusLabels = {
  ready: "Prêt à examiner",
  partial: "Partiel",
  failed: "Échec visible",
  generated_unreviewed: "Généré · non revu",
  needs_review: "Revue nécessaire",
  reviewed: "Revu",
  superseded: "Remplacé",
  conflict: "Conflit",
  draft: "Brouillon local",
};

const iconPaths = {
  document: '<path d="M6 2.75h8l4 4V21.25H6z"/><path d="M14 2.75v4h4M9 12h6M9 16h6"/>',
  knowledge: '<path d="M4 5.5c2.7-.9 5.3-.5 8 1.1v14c-2.7-1.6-5.3-2-8-1.1z"/><path d="M20 5.5c-2.7-.9-5.3-.5-8 1.1v14c2.7-1.6 5.3-2 8-1.1z"/>',
  questionnaire: '<path d="M5 4.5h14v15H5z"/><path d="m8 9 1.2 1.2L11.5 8M13 9h3M8 14h3M13 14h3"/>',
  source: '<path d="M9.5 14.5 14.5 9.5"/><path d="M7.2 16.8 5.8 18.2a3.5 3.5 0 0 1-5-5l3.4-3.4a3.5 3.5 0 0 1 5 0" transform="translate(3 0)"/><path d="m16.8 7.2 1.4-1.4a3.5 3.5 0 0 1 5 5l-3.4 3.4a3.5 3.5 0 0 1-5 0" transform="translate(-3 0)"/>',
  review: '<path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5"/><path d="m8.5 12 2.3 2.3L18.5 6.6"/>',
  scope: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5"/><path d="M12 1.5v3M22.5 12h-3M12 22.5v-3M1.5 12h3"/>',
  memory: '<ellipse cx="12" cy="5.5" rx="7.5" ry="3"/><path d="M4.5 5.5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6M4.5 11.5v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6"/>',
  history: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.5 2M4.5 5.5 2.5 5.3l.2-2"/>',
  decision: '<path d="M12 3v13M7 7h10M5 20h14"/><path d="m7 7-3 5h6zM17 7l-3 5h6z"/>',
};

function icon(name) {
  const wrapper = document.createElement("span");
  wrapper.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.document}</svg>`;
  return wrapper.firstElementChild;
}

function setNetwork() {
  $("network").textContent = navigator.onLine ? "en ligne" : "hors ligne";
}

async function api(path) {
  const response = await fetch(path, {
    headers: { Authorization: `Bearer ${state.token}` },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(payload.detail || response.statusText);
  }
  return response.json();
}

function recentEvent(createdAt, updatedAt, version = 1) {
  const timestamp = new Date(updatedAt || createdAt || 0).getTime();
  if (!timestamp || Date.now() - timestamp > 48 * 60 * 60 * 1000) return null;
  return version > 1 || (createdAt && updatedAt && createdAt !== updatedAt) ? "updated" : "created";
}

function statusLabel(status) {
  return statusLabels[status] || String(status || "À vérifier").replaceAll("_", " ");
}

function documentModel(item) {
  const naming = item.naming || {};
  const extraction = item.extraction || {};
  const status = item.analysis_status || "partial";
  const title = naming.object_name || naming.document_type || item.title || "Document";
  const descriptor = [naming.document_type, naming.phase_code, naming.revision_index].filter(Boolean).join(" · ");
  const signal = extraction.error
    ? "Une erreur d’extraction doit être examinée"
    : `${extraction.chunk_count || 0} segment(s) dérivé(s)`;

  return {
    id: item.card_id || `card-${item.document_id}`,
    kind: "document",
    typeLabel: "Document",
    title,
    summary: descriptor || "Document projet avec provenance et état d’analyse visibles.",
    status,
    signal,
    context: naming.phase_folder || item.parent_project_id,
    event: null,
    attention: status !== "ready" ? "human" : null,
    responsibilities: [
      { icon: "source", label: "Source liée · la carte n’est pas la source" },
      { icon: "history", label: "Extraction et provenance" },
      ...(status !== "ready" ? [{ icon: "review", label: "Revue humaine nécessaire", attention: true }] : []),
    ],
    sections: [
      ["Identité", [
        `Document : ${item.title || title}`,
        `Projet : ${item.parent_project_id || "non renseigné"}`,
        `Type média : ${item.media_type || "non renseigné"}`,
      ]],
      ["Source", [
        item.source_ref || "Localisation non exposée",
        `Empreinte : ${item.source_digest || "non exposée"}`,
        `La carte est une projection : source=${Boolean(item.authority?.is_source)}, preuve=${Boolean(item.authority?.is_evidence)}, mémoire=${Boolean(item.authority?.is_memory)}.`,
      ]],
      ["Extraction", [
        `Statut : ${statusLabel(status)}`,
        `Convertisseur : ${extraction.converter || "non renseigné"}`,
        `Version : ${extraction.converter_version || "non renseignée"}`,
        `Segments : ${extraction.chunk_count || 0}`,
        ...(extraction.quality_flags || []).map(flag => `Signal qualité : ${flag}`),
        ...(extraction.error ? [`Erreur : ${extraction.error}`] : []),
      ]],
      ["Prochaine revue", [status === "ready" ? "Ouvrir le document ou son Markdown dérivé avant toute qualification." : "Examiner l’état incomplet ou l’erreur avant de s’appuyer sur le contenu."]],
    ],
  };
}

function knowledgeModel(item) {
  const status = item.review_status || "generated_unreviewed";
  const sourceCount = (item.source_chunk_refs || []).length;
  return {
    id: item.card_id || `card-${item.knowledge_id}`,
    kind: "knowledge",
    typeLabel: "Knowledge",
    title: item.title || "Knowledge",
    summary: `${item.family || "famille non renseignée"} · version ${item.version || 1}`,
    status,
    signal: `${sourceCount} segment(s) source · ${statusLabel(status)}`,
    context: item.parent_project_id,
    event: recentEvent(item.created_at, item.updated_at, item.version),
    attention: ["generated_unreviewed", "needs_review"].includes(status) ? "human" : null,
    responsibilities: [
      { icon: "source", label: `${sourceCount} segment(s) source lié(s)` },
      { icon: "memory", label: "Knowledge n’est pas mémoire gouvernée" },
      { icon: "review", label: statusLabel(status), attention: ["generated_unreviewed", "needs_review"].includes(status) },
    ],
    sections: [
      ["Identité", [
        `Knowledge : ${item.knowledge_id || "non renseignée"}`,
        `Famille : ${item.family || "non renseignée"}`,
        `Version : ${item.version || 1}`,
        `Créée par : ${item.created_by || "non renseigné"}`,
      ]],
      ["Statut", [
        statusLabel(status),
        "Knowledge ≠ Evidence.",
        "Knowledge ≠ mémoire gouvernée.",
        "Knowledge ≠ doctrine.",
      ]],
      ["Provenance", [
        `Document lié : ${item.document_ref || "non renseigné"}`,
        `${sourceCount} référence(s) de segment conservée(s).`,
        `Empreinte Markdown : ${item.markdown_digest || "non exposée"}`,
      ]],
      ["Prochaine revue", [["generated_unreviewed", "needs_review"].includes(status)
        ? "Relire le Markdown, les sources et les limites avant toute réutilisation conséquente."
        : "La réutilisation reste dépendante du dossier, du périmètre et des sources applicables."]],
    ],
  };
}

function questionnaireModel() {
  return {
    id: "local-questionnaire",
    kind: "questionnaire",
    typeLabel: "Questionnaire",
    title: "Préciser la demande",
    summary: "Quatre questions pour réduire l’ambiguïté avant de préparer une réponse.",
    status: "draft",
    signal: "Brouillon local · aucun effet serveur",
    context: state.project || "non rattaché",
    event: null,
    attention: "human",
    responsibilities: [
      { icon: "scope", label: "Périmètre de la demande", attention: true },
      { icon: "decision", label: "Réponses confirmées par l’humain" },
    ],
    questionnaire: true,
  };
}

function currentModels() {
  const documents = state.documents.map(documentModel);
  const knowledge = state.knowledge.map(knowledgeModel);
  if (state.scene === "documents") return documents;
  if (state.scene === "knowledge") return knowledge;
  if (state.scene === "questionnaire") return [questionnaireModel()];
  return [...knowledge, ...documents].sort((a, b) => {
    const priority = value => value.attention === "human" ? 0 : 1;
    return priority(a) - priority(b);
  });
}

function typeLockup(model) {
  const lockup = document.createElement("div");
  lockup.className = "type-lockup";
  const iconCircle = document.createElement("span");
  iconCircle.className = "type-icon";
  iconCircle.append(icon(model.kind));
  const label = document.createElement("span");
  label.className = "type-label";
  label.textContent = model.typeLabel;
  lockup.append(iconCircle, label);
  return lockup;
}

function responsibilityButton(item) {
  const badge = document.createElement("span");
  badge.className = "responsibility-icon";
  badge.title = item.label;
  badge.setAttribute("aria-label", item.label);
  if (item.attention) badge.dataset.attention = "true";
  badge.append(icon(item.icon));
  return badge;
}

function renderCard(model) {
  const card = document.createElement("article");
  card.className = "p-card";
  card.dataset.kind = model.kind;
  card.dataset.status = model.status;
  card.dataset.frame = "gradient";
  if (model.event) card.dataset.event = model.event;
  if (model.attention) card.dataset.attention = model.attention;

  const button = document.createElement("button");
  button.className = "card-button";
  button.type = "button";
  button.setAttribute("aria-label", `Ouvrir le détail : ${model.title}`);
  button.addEventListener("click", () => openDetail(model));

  const header = document.createElement("header");
  header.className = "card-header";
  header.append(typeLockup(model));
  if (model.event) {
    const event = document.createElement("span");
    event.className = "event-chip";
    event.textContent = model.event === "created" ? "Nouveau" : "Mis à jour";
    header.append(event);
  }

  const body = document.createElement("div");
  body.className = "card-body";
  const title = document.createElement("h3");
  title.className = "card-title";
  title.textContent = model.title;
  const summary = document.createElement("p");
  summary.className = "card-summary";
  summary.textContent = model.summary;
  const signal = document.createElement("p");
  signal.className = "card-signal";
  signal.textContent = model.signal;
  body.append(title, summary, signal);

  const footer = document.createElement("footer");
  footer.className = "card-footer";
  const meta = document.createElement("div");
  meta.className = "card-meta";
  const status = document.createElement("p");
  status.className = "card-status";
  status.textContent = statusLabel(model.status);
  const context = document.createElement("p");
  context.className = "card-context";
  context.textContent = model.context || "Contexte non renseigné";
  meta.append(status, context);
  const responsibilities = document.createElement("div");
  responsibilities.className = "responsibility-row";
  for (const item of model.responsibilities || []) responsibilities.append(responsibilityButton(item));
  footer.append(meta, responsibilities);

  card.append(button, header, body, footer);
  return card;
}

function sectionElement(title, entries) {
  const section = document.createElement("section");
  section.className = "detail-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.append(heading);
  const values = entries.flat().filter(Boolean);
  if (values.length === 1) {
    const paragraph = document.createElement("p");
    paragraph.textContent = values[0];
    section.append(paragraph);
  } else {
    const list = document.createElement("ul");
    for (const entry of values) {
      const item = document.createElement("li");
      item.textContent = entry;
      list.append(item);
    }
    section.append(list);
  }
  return section;
}

function questionnaireContent() {
  const wrapper = document.createElement("div");
  wrapper.className = "questionnaire-form";
  const stored = JSON.parse(sessionStorage.getItem(`pantheon-questionnaire:${state.project || "unscoped"}`) || "{}");

  const intro = sectionElement("Limite", ["Ce questionnaire reste un brouillon local. Il ne crée, ne modifie, ne remplace et n’approuve aucune carte."]);
  wrapper.append(intro);

  const questions = [
    {
      id: "deliverable",
      title: "Quel résultat attendez-vous ?",
      type: "radio",
      options: ["Réponse courte", "Analyse détaillée", "Document à relire", "Décision à préparer"],
    },
    {
      id: "priorities",
      title: "Quels points doivent être prioritaires ?",
      type: "checkbox",
      options: ["Périmètre", "Sources", "Responsabilités", "Délais", "Coût"],
    },
    {
      id: "external",
      title: "Le résultat est-il destiné à une action externe ?",
      type: "radio",
      options: ["Oui", "Non", "À déterminer"],
    },
  ];

  for (const question of questions) {
    const block = document.createElement("section");
    block.className = "question-block";
    const heading = document.createElement("h3");
    heading.textContent = question.title;
    const options = document.createElement("div");
    options.className = "option-list";
    for (const option of question.options) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = question.type;
      input.name = question.id;
      input.value = option;
      const previous = stored[question.id];
      input.checked = Array.isArray(previous) ? previous.includes(option) : previous === option;
      input.addEventListener("change", saveQuestionnaireDraft);
      label.append(input, document.createTextNode(option));
      options.append(label);
    }
    block.append(heading, options);
    wrapper.append(block);
  }

  const noteBlock = document.createElement("section");
  noteBlock.className = "question-block";
  const noteLabel = document.createElement("label");
  noteLabel.textContent = "Précision libre";
  const note = document.createElement("textarea");
  note.id = "question-note";
  note.rows = 4;
  note.placeholder = "Élément utile, limite ou contexte à conserver";
  note.value = stored.note || "";
  note.addEventListener("input", saveQuestionnaireDraft);
  noteLabel.append(note);
  noteBlock.append(noteLabel);
  wrapper.append(noteBlock);

  const action = document.createElement("button");
  action.type = "button";
  action.className = "primary-action";
  action.textContent = "Préparer le résumé";
  action.addEventListener("click", reviewQuestionnaire);
  wrapper.append(action);

  const output = document.createElement("section");
  output.id = "question-summary";
  output.className = "detail-section";
  wrapper.append(output);
  return wrapper;
}

function questionnaireValues() {
  const values = {};
  for (const name of ["deliverable", "external"]) {
    values[name] = document.querySelector(`input[name="${name}"]:checked`)?.value || "";
  }
  values.priorities = [...document.querySelectorAll('input[name="priorities"]:checked')].map(input => input.value);
  values.note = $("question-note")?.value.trim() || "";
  return values;
}

function saveQuestionnaireDraft() {
  sessionStorage.setItem(`pantheon-questionnaire:${state.project || "unscoped"}`, JSON.stringify(questionnaireValues()));
}

function reviewQuestionnaire() {
  const values = questionnaireValues();
  saveQuestionnaireDraft();
  const output = $("question-summary");
  output.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "Résumé à confirmer";
  const list = document.createElement("ul");
  const entries = [
    `Résultat attendu : ${values.deliverable || "non répondu"}`,
    `Priorités : ${values.priorities.length ? values.priorities.join(", ") : "non répondu"}`,
    `Action externe : ${values.external || "non répondu"}`,
    `Précision : ${values.note || "aucune"}`,
    "Aucun effet n’a été appliqué. Le rapprochement CREATE / UPDATE / SUPERSEDE / CONFLICT n’est pas encore implémenté dans ce lot.",
  ];
  for (const entry of entries) {
    const item = document.createElement("li");
    item.textContent = entry;
    list.append(item);
  }
  output.append(heading, list);
}

function openDetail(model) {
  $("detail-kind").replaceChildren(typeLockup(model));
  const content = $("detail-content");
  content.replaceChildren();
  const title = document.createElement("h2");
  title.id = "detail-title";
  title.textContent = model.title;
  content.append(title);
  if (model.questionnaire) content.append(questionnaireContent());
  else for (const [heading, entries] of model.sections || []) content.append(sectionElement(heading, entries));
  $("detail-dialog").showModal();
}

function render() {
  const [eyebrow, title] = sceneCopy[state.scene];
  $("scene-eyebrow").textContent = eyebrow;
  $("scene-title").textContent = title;
  const models = currentModels();
  $("scene-status").textContent = state.scene === "questionnaire"
    ? "Brouillon conservé uniquement pour cette session."
    : state.project
      ? `${models.length} carte(s) projetée(s) pour ${state.project}.`
      : "Indiquez un projet pour charger ses cartes.";
  const deck = $("deck");
  deck.replaceChildren();
  if (!models.length) deck.append($("empty-template").content.cloneNode(true));
  else for (const model of models) deck.append(renderCard(model));
}

async function loadProject() {
  state.project = $("project").value.trim();
  state.token = $("token").value;
  if (!state.project) {
    $("scene-status").textContent = "Le projet est obligatoire.";
    return;
  }
  if (!state.token) {
    $("scene-status").textContent = "La clé d’accès est obligatoire.";
    return;
  }
  $("load").disabled = true;
  $("scene-status").textContent = "Chargement des projections…";
  try {
    const [documents, knowledge] = await Promise.all([
      api(`../v1/projects/${encodeURIComponent(state.project)}/documents`),
      api(`../v1/projects/${encodeURIComponent(state.project)}/knowledge`),
    ]);
    state.documents = documents.documents || [];
    state.knowledge = knowledge.knowledge || [];
    render();
  } catch (error) {
    state.documents = [];
    state.knowledge = [];
    render();
    $("scene-status").textContent = `Chargement refusé : ${error.message}`;
  } finally {
    $("load").disabled = false;
  }
}

for (const button of document.querySelectorAll("[data-scene]")) {
  button.addEventListener("click", () => {
    state.scene = button.dataset.scene;
    document.querySelectorAll("[data-scene]").forEach(tab => tab.classList.toggle("is-active", tab === button));
    render();
  });
}

$("load").addEventListener("click", loadProject);
window.addEventListener("online", setNetwork);
window.addEventListener("offline", setNetwork);
setNetwork();
render();
