// Cockpit V3 demo — fictional agency universe.
//
// Thin wiring on top of the shared collection lifecycle. This file owns the
// business projection of the fixtures (spaces, projects, decisions, tools,
// knowledge) and delegates every Swiper concern to the LevelController /
// CollectionController, which initialize Swiper once and never rebuild.

import { createLevelController } from "./collection/level_controller.js";
import { renderCard, renderPlaceholder, renderNewSlide } from "./collection/card_renderer.js";

const SWIPER_VERSION = "14.0.6";
const stage = document.getElementById("v2-stage");
const breadcrumb = document.getElementById("v2-breadcrumb");
const status = document.getElementById("v2-status");
const network = document.getElementById("v2-network");
const spaceButtons = [...document.querySelectorAll("[data-space]")];

if (!stage) throw new Error("Cockpit stage unavailable");

async function ensureSwiper() {
  if (typeof window.Swiper === "function") return;
  const candidates = [
    `https://cdn.jsdelivr.net/npm/swiper@${SWIPER_VERSION}/swiper-bundle.min.js`,
    `https://unpkg.com/swiper@${SWIPER_VERSION}/swiper-bundle.min.js`,
  ];
  for (const src of candidates) {
    try {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.onload = resolve;
        script.onerror = () => reject(new Error(`Swiper unavailable: ${src}`));
        document.head.append(script);
      });
      if (typeof window.Swiper === "function") return;
    } catch (_) {
      // Try next CDN.
    }
  }
  throw new Error("Swiper runtime unavailable");
}

const fixture = await fetch("demo-data.json", { cache: "no-store" }).then(response => {
  if (!response.ok) throw new Error(`Fixture indisponible (${response.status})`);
  return response.json();
});

await ensureSwiper();

document.documentElement.dataset.swiperReady = "true";
document.documentElement.dataset.swiperVersion = SWIPER_VERSION;
document.documentElement.dataset.cockpitMode = "demo";
window.PANTHEON_COCKPIT_DEMO = true;
if (network) network.textContent = "démo · données fictives";

const ROOT_ITEMS = [
  { id: "space:pantheon", title: "Pantheon", category: "Pantheon", family: "pantheon", status: "active", summary: "Contexte, gouvernance et décisions conséquentes.", details: "Pantheon gouverne ; il ne devient ni runtime, ni scheduler, ni moteur d’approbation automatique." },
  { id: "space:decisions", title: "Décisions", category: "Décisions", family: "decision", status: "review", summary: "Validations humaines et propositions à examiner." },
  { id: "space:affaires", title: "Affaires", category: "Projets", family: "project", status: "active", summary: "Projets, Informations, Contacts et Travaux." },
  { id: "space:connaissances", title: "Connaissances", category: "Références", family: "information", status: "neutral", summary: "Références réutilisables et état de revue." },
  { id: "space:outils", title: "Outils", category: "Outils", family: "tool", status: "neutral", summary: "Outils, skills, bindings et runtimes observés ou candidats." },
];

function model(id, title, category, family, summary, statusValue = "neutral", details = "") {
  return { id, title, category, family, summary, status: statusValue, details };
}

function projectModels() {
  return fixture.projects.map(project => model(
    `project:${project.project_id}`,
    project.display_name || project.code,
    "Projet",
    "project",
    [project.code, project.phase, project.location].filter(Boolean).join(" · "),
    project.status || "active",
    [
      project.primary_client ? `Client : ${project.primary_client}` : null,
      project.claim_values?.budget_target != null ? `Budget cible : ${new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(project.claim_values.budget_target)}` : null,
      project.claim_values?.surface_projected != null ? `Surface projetée : ${project.claim_values.surface_projected} m²` : null,
    ].filter(Boolean).join("\n"),
  ));
}

function projectChildren(projectId) {
  const project = fixture.projects.find(item => item.project_id === projectId);
  const payload = fixture.project_payloads[projectId] || {};
  return [
    model(`contacts:${projectId}`, "Contacts", "Contacts", "contact", `${project?.contacts?.length || 0} contact(s)`, "neutral", (project?.contacts || []).map(item => [item.name, item.role, item.organization].filter(Boolean).join(" · ")).join("\n")),
    ...(payload.information || []).map(item => model(`information:${item.information_id}`, item.title, item.category || "Information", "information", item.summary, item.status, item.details || item.source_ref || "")),
    ...(payload.documents || []).map(item => model(`document:${item.document_id}`, item.title || item.naming?.object_name || "Document", item.naming?.document_type || "Document", "information", item.source_ref || "Document source", item.status || "ready", item.document_date || "")),
    ...(payload.knowledge || []).map(item => model(`knowledge:${item.knowledge_id}`, item.title, item.family || "Référence", "information", item.markdown || "Référence", item.review_status || "neutral", `Version ${item.version || 1}`)),
    ...(payload.work_issues || []).map(entry => {
      const item = entry.work_issue || entry;
      return model(`work:${item.issue_id}`, item.title, "Travail", "work", item.description || "Travail à traiter", item.status || "open", (item.tags || []).join(" · "));
    }),
  ];
}

function decisionModels() {
  return Object.values(fixture.project_payloads).flatMap(payload => (payload.change_candidates || []).map(item => model(
    `decision:${item.candidate_id}`,
    item.reason || "Modification à valider",
    "Décision",
    "decision",
    `Révision de base ${item.base_revision ?? "?"} · ${item.proposer || "Provenance non renseignée"}`,
    item.status || "pending_review",
    (item.changes || []).map(change => `${change.field}: ${change.before ?? "—"} → ${change.proposed ?? "—"}`).join("\n"),
  )));
}

function toolModels() {
  return (fixture.tool_catalog?.items || []).map(item => model(
    `tool:${item.tool_id}`,
    item.name || item.tool_id,
    item.category || "Outil",
    "tool",
    item.short_description || "Outil candidat",
    item.governance_state || "neutral",
    [
      `Installation : ${item.installation_state || "unknown"}`,
      `Santé : ${item.health_state || "unknown"}`,
      `Activation : ${item.activation_state || "unknown"}`,
      `Evidence : ${item.evidence_expectation || "À définir"}`,
    ].join("\n"),
  ));
}

function knowledgeModels() {
  return Object.values(fixture.project_payloads).flatMap(payload => (payload.knowledge || []).map(item => model(
    `knowledge:${item.knowledge_id}`,
    item.title,
    item.family || "Référence",
    "information",
    item.markdown || "Référence",
    item.review_status || "neutral",
    `Version ${item.version || 1}`,
  )));
}

function collectionFor(item) {
  if (!item) return null;
  if (item.id === "space:affaires") return { id: "projects", title: "Affaires", items: projectModels(), canCreate: true };
  if (item.id === "space:decisions") return { id: "decisions", title: "Décisions", items: decisionModels(), canCreate: false };
  if (item.id === "space:connaissances") return { id: "knowledge", title: "Connaissances", items: knowledgeModels(), canCreate: true };
  if (item.id === "space:outils") return { id: "tools", title: "Outils", items: toolModels(), canCreate: true };
  if (item.id.startsWith("project:")) {
    const projectId = item.id.slice("project:".length);
    return { id: `project:${projectId}:children`, title: item.title, items: projectChildren(projectId), canCreate: true };
  }
  return null;
}

// --- Navigation stack (business state, independent of Swiper) ---------------

const stack = [];

function currentFrame() {
  return stack[stack.length - 1];
}

function activeItem(frame) {
  if (!frame || frame.activeSynthetic) return null;
  return frame.items[frame.index] || null;
}

function childCollectionFor(frame) {
  const item = activeItem(frame);
  if (!item) return null;
  const collection = collectionFor(item);
  if (!collection || !collection.items.length) return null;
  return collection;
}

function parentItemFor() {
  if (stack.length < 2) return null;
  const parent = stack[stack.length - 2];
  return activeItem(parent);
}

function frameCollection(frame) {
  return { id: frame.id, title: frame.title, canCreate: Boolean(frame.canCreate) };
}

// --- Flip binding (demo owns its own interactions) --------------------------

function bindFlip(card) {
  let pointerId = null;
  let startX = 0;
  let startY = 0;
  let dragged = false;
  card.addEventListener("pointerdown", event => { pointerId = event.pointerId; startX = event.clientX; startY = event.clientY; dragged = false; }, { passive: true });
  card.addEventListener("pointermove", event => {
    if (event.pointerId !== pointerId) return;
    if (Math.hypot(event.clientX - startX, event.clientY - startY) > 8) dragged = true;
  }, { passive: true });
  card.addEventListener("pointercancel", () => { pointerId = null; dragged = true; }, { passive: true });
  card.addEventListener("click", event => {
    pointerId = null;
    if (dragged || stage.dataset.swiperMoving === "true" || event.target.closest("button,a,input,textarea,select")) {
      dragged = false;
      return;
    }
    card.dataset.flipped = card.dataset.flipped === "true" ? "false" : "true";
  });
}

// --- Level controller wiring ------------------------------------------------

const level = createLevelController({
  stage,
  renderItem(item) {
    const card = renderCard(item, { hydrated: true, interactive: true });
    bindFlip(card);
    return card;
  },
  renderNew(collection) {
    return renderNewSlide(collection, col => stage.dispatchEvent(new CustomEvent("pantheon:create-requested", { bubbles: true, detail: { collection_id: col.id } })));
  },
  renderPlaceholder,
  onActiveChange(item, index, meta) {
    const frame = currentFrame();
    if (!frame) return;
    frame.activeSynthetic = meta?.synthetic === "create";
    if (!frame.activeSynthetic && index >= 0) frame.index = index;
    level.updateDescendability(Boolean(childCollectionFor(frame)));
    updateLocation();
  },
  onCommit(direction) {
    if (direction > 0) {
      const child = childCollectionFor(currentFrame());
      if (!child) { renderDeck(); return; }
      stack.push(createFrame(child, currentFrame().rootSpace));
    } else if (stack.length > 1) {
      stack.pop();
    }
    renderDeck();
  },
  onMoveState(moving) {
    if (moving) stage.dataset.swiperMoving = "true";
    else delete stage.dataset.swiperMoving;
  },
});

function createFrame(collection, rootSpace) {
  return { ...collection, index: 0, activeSynthetic: false, rootSpace };
}

function updateLocation() {
  if (breadcrumb) breadcrumb.textContent = stack.map(frame => frame.title).join(" / ");
  const frame = currentFrame();
  const active = activeItem(frame);
  if (status) {
    status.textContent = frame.activeSynthetic
      ? `Créer dans ${frame.title}`
      : active ? `${frame.items.length} carte(s) · ${active.title}` : "Collection vide";
  }
  spaceButtons.forEach(button => button.classList.toggle("is-active", frame.rootSpace === button.dataset.space));
}

function renderDeck() {
  const frame = currentFrame();
  const child = childCollectionFor(frame);
  level.render({
    collection: frameCollection(frame),
    items: frame.items,
    index: frame.index,
    parentItem: parentItemFor(),
    childItem: child?.items?.[0] || null,
    canAscend: stack.length > 1,
    canDescend: Boolean(child),
  });
  updateLocation();
}

// --- Controls ---------------------------------------------------------------

spaceButtons.forEach(button => button.addEventListener("click", () => {
  const index = ROOT_ITEMS.findIndex(item => item.id === `space:${button.dataset.space}`);
  if (index < 0) return;
  stack.splice(1);
  stack[0].index = index;
  stack[0].activeSynthetic = false;
  renderDeck();
}));

document.getElementById("v2-descend")?.addEventListener("click", () => level.descend());
document.getElementById("v2-ascend")?.addEventListener("click", () => level.ascend());
document.getElementById("v2-previous")?.addEventListener("click", () => level.slidePrevCard());
document.getElementById("v2-next")?.addEventListener("click", () => level.slideNextCard());
document.getElementById("v2-flip")?.addEventListener("click", () => {
  const card = level.activeElement()?.querySelector(".v2-card");
  if (card) card.dataset.flipped = card.dataset.flipped === "true" ? "false" : "true";
});

window.addEventListener("pagehide", () => level.dispose(), { once: true });

stack.push({ id: "root", title: "Pantheon", items: ROOT_ITEMS, index: 0, activeSynthetic: false, canCreate: false, rootSpace: "pantheon" });
renderDeck();
