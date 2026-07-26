(() => {
  "use strict";

  const registryState = {
    typeTags: new Map(),
    subjectTags: new Map(),
    statuses: new Map(),
    limits: new Map(),
  };

  const GROUP_ORDER = [
    "Maîtrise d’ouvrage",
    "Équipe de maîtrise d’œuvre",
    "Bureaux d’études",
    "Bureau de contrôle",
    "SSI",
    "Entreprises de travaux",
    "Autres intervenants",
  ];

  function slug(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  async function loadRegistry(path, collectionKey, map) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      for (const item of payload[collectionKey] || []) {
        map.set(slug(item.slug || item.title), item);
      }
    } catch (_) {
      // Presentation registry failure must not block the cockpit.
    }
  }

  function registryEntry(map, value) {
    const key = slug(value);
    return map.get(key) || null;
  }

  function tokenColor(node, entry) {
    if (entry?.color) node.dataset.tokenColor = entry.color;
    if (entry?.icon_key) node.dataset.iconKey = entry.icon_key;
  }

  function familyLabel(card) {
    const labels = {
      project: "Projet",
      document: "Information",
      knowledge: "Information",
      decision: "Décision",
      capability: "Outil",
      "runtime-host": "Outil",
      "role-reference": "Référence",
      pantheon: "Pantheon",
    };
    return labels[card.dataset.family] || card.dataset.family || "Carte";
  }

  function ensureIdentity(front, card) {
    const top = front.querySelector(".v2-card-top");
    if (!top || top.querySelector(".v2-card-identity")) return;

    const existingIndex = top.querySelector(".v2-index");
    const statusOrb = top.querySelector(".v2-orb--status");
    const footerMark = front.querySelector(".v2-family-mark");

    const identity = document.createElement("div");
    identity.className = "v2-card-identity";

    const line = document.createElement("div");
    line.className = "v2-card-identity-line";

    if (footerMark) {
      footerMark.remove();
      footerMark.classList.add("v2-family-mark--identity");
      line.append(footerMark);
    }

    const category = document.createElement("span");
    category.className = "v2-card-category";
    category.textContent = familyLabel(card);
    line.append(category);

    const typeTags = document.createElement("span");
    typeTags.className = "v2-card-type-tags";
    line.append(typeTags);

    const meta = document.createElement("div");
    meta.className = "v2-card-meta";
    if (existingIndex) {
      meta.textContent = existingIndex.textContent || "";
      existingIndex.remove();
    }

    identity.append(line, meta);

    const states = document.createElement("div");
    states.className = "v2-card-states";
    if (statusOrb) {
      statusOrb.remove();
      statusOrb.classList.add("v2-state-icon");
      const status = card.dataset.status || statusOrb.title;
      tokenColor(statusOrb, registryEntry(registryState.statuses, status));
      states.append(statusOrb);
    }

    top.replaceChildren(identity, states);
  }

  function classifyFrontTags(front) {
    const identityTags = front.querySelector(".v2-card-type-tags");
    const rail = front.querySelector(".v2-indicator-rail");
    if (!identityTags || !rail) return;

    const tagNodes = [...rail.querySelectorAll(".v2-orb--tag")];
    for (const node of tagNodes) {
      const label = node.title || node.textContent || "";
      const typeEntry = registryEntry(registryState.typeTags, label);
      const subjectEntry = registryEntry(registryState.subjectTags, label);

      if (typeEntry) {
        node.remove();
        node.className = "v2-type-tag";
        node.title = typeEntry.title;
        node.setAttribute("aria-label", typeEntry.title);
        tokenColor(node, typeEntry);
        identityTags.append(node);
        continue;
      }

      node.classList.add("v2-subject-tag-icon");
      tokenColor(node, subjectEntry);
    }
  }

  function renderBackTags(back) {
    const footer = back.querySelector(".v2-card-footer");
    if (!footer || footer.querySelector(".v2-back-tag-labels")) return;

    const rail = footer.querySelector(".v2-indicator-rail");
    const labels = document.createElement("div");
    labels.className = "v2-back-tag-labels";

    for (const node of [...(rail?.querySelectorAll(".v2-orb--tag") || [])]) {
      const label = node.title || node.textContent || "";
      const entry = registryEntry(registryState.subjectTags, label) || registryEntry(registryState.typeTags, label);
      const chip = document.createElement("span");
      chip.className = "v2-back-tag-label";
      chip.textContent = entry?.title || label;
      chip.title = entry?.description || label;
      tokenColor(chip, entry);
      labels.append(chip);
    }

    const actions = document.createElement("div");
    actions.className = "v2-card-actions";
    actions.hidden = true;

    footer.replaceChildren(actions, labels);
  }

  function contactGroup(item) {
    const source = slug([item.participation_type, item.role, item.label].filter(Boolean).join(" "));
    if (/maitrise-d-ouvrage|client|moa/.test(source)) return "Maîtrise d’ouvrage";
    if (/bureau-de-controle|controle-technique|controle/.test(source)) return "Bureau de contrôle";
    if (/ssi|securite-incendie/.test(source)) return "SSI";
    if (/architecte|maitrise-d-oeuvre|moe/.test(source)) return "Équipe de maîtrise d’œuvre";
    if (/bureau-d-etudes|bet|structure|fluides|thermique|acoustique|geotechnique/.test(source)) return "Bureaux d’études";
    if (/entreprise|travaux|lot-/.test(source)) return "Entreprises de travaux";
    return "Autres intervenants";
  }

  function contactDisplay(item) {
    const person = item.person_name || "";
    const company = item.organization_name || item.label || "";
    const role = item.role || item.participation_type || "";
    return [person, company, role].filter(Boolean).join(" · ") || "Contact non renseigné";
  }

  async function enhanceContacts(card) {
    const back = card.querySelector(".v2-card-back");
    const title = back?.querySelector(".v2-back-title")?.textContent?.trim();
    if (title !== "Intervenants" || back.dataset.contactsEnhanced === "true") return;

    const projectInput = document.getElementById("v2-project");
    const tokenInput = document.getElementById("v2-token");
    const project = projectInput?.value?.trim();
    const token = tokenInput?.value || "";
    if (!project || !token) return;

    try {
      const response = await fetch(`../v1/agency/projects/${encodeURIComponent(project)}/participations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) return;
      const payload = await response.json();
      const groups = new Map(GROUP_ORDER.map(name => [name, []]));
      for (const item of payload.participations || []) groups.get(contactGroup(item)).push(item);

      const body = back.querySelector(".v2-back-body");
      if (!body) return;
      body.querySelectorAll(".v2-contact-groups").forEach(node => node.remove());

      const wrapper = document.createElement("div");
      wrapper.className = "v2-contact-groups";
      for (const groupName of GROUP_ORDER) {
        const contacts = groups.get(groupName) || [];
        if (!contacts.length) continue;
        const section = document.createElement("section");
        section.className = "v2-back-section v2-contact-group";
        const heading = document.createElement("h3");
        heading.textContent = groupName;
        section.append(heading);
        for (const item of contacts) {
          const row = document.createElement("p");
          row.textContent = contactDisplay(item);
          section.append(row);
        }
        wrapper.append(section);
      }
      body.append(wrapper);
      back.dataset.contactsEnhanced = "true";
    } catch (_) {
      // Contacts enhancement is presentation-only and must fail open.
    }
  }

  function enhanceCard(card) {
    const front = card.querySelector(".v2-card-front");
    const back = card.querySelector(".v2-card-back");
    if (!front || !back) return;
    ensureIdentity(front, card);
    classifyFrontTags(front);
    renderBackTags(back);
    enhanceContacts(card);
  }

  function enhanceStage() {
    document.querySelectorAll("#v2-stage .v2-card").forEach(enhanceCard);
  }

  async function init() {
    await Promise.all([
      loadRegistry("registries/type_tags.json", "tags", registryState.typeTags),
      loadRegistry("registries/subject_tags.json", "tags", registryState.subjectTags),
      loadRegistry("registries/status_registry.json", "values", registryState.statuses),
      loadRegistry("registries/limit_registry.json", "values", registryState.limits),
    ]);

    const stage = document.getElementById("v2-stage");
    if (!stage) return;
    new MutationObserver(enhanceStage).observe(stage, { childList: true, subtree: true });
    enhanceStage();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
