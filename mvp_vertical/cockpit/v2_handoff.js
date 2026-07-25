(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  let selectedContext = [];
  let previewGeneration = 0;
  let prepared = null;
  let submitted = null;
  let admitted = null;

  function token() {
    return $("v2-token")?.value || "";
  }

  function actor() {
    return $("v2-handoff-actor")?.value.trim() || "";
  }

  function includeDeclaredDescendants() {
    return Boolean($("v2-handoff-descendants")?.checked);
  }

  function idempotencyKey(prefix) {
    if (globalThis.crypto?.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
    return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function currentCardRef() {
    const card = document.querySelector("#v2-stage .v2-card");
    if (!card) return null;
    const entityId = card.querySelector(".v2-entity-id")?.textContent?.trim();
    const kicker = card.querySelector(".v2-card-back .v2-card-kicker")?.textContent || "";
    const parts = kicker.split("·").map(value => value.trim()).filter(Boolean);
    const entityType = parts.at(-1) || "";
    const title = card.querySelector(".v2-card-title")?.textContent?.trim() || entityId;
    if (!entityId || !entityType) return null;
    return { entity_id: entityId, entity_type: entityType, label: title };
  }

  function updateScopeLabel() {
    const root = currentCardRef();
    if (!root) {
      $("v2-handoff-scope").textContent = "Aucune carte courante";
      return;
    }
    const descendants = includeDeclaredDescendants() ? " + descendants déclarés" : "";
    $("v2-handoff-scope").textContent = `${root.label}${descendants} + ${selectedContext.length} ajout(s) explicite(s)`;
  }

  function buildEnvelope() {
    const root = currentCardRef();
    if (!root) throw new Error("Aucune carte courante avec identité stable");
    return {
      root_entity: { entity_id: root.entity_id, entity_type: root.entity_type },
      descendants: [],
      source_refs: [],
      explicit_additions: [],
      explicit_exclusions: [],
      scope_widened_implicitly: false,
    };
  }

  function baseRequest() {
    return {
      question: $("v2-handoff-question").value.trim(),
      card_context_envelope: buildEnvelope(),
      selected_context: selectedContext.map(item => ({
        entity_id: item.entity_id,
        entity_type: item.entity_type,
      })),
      include_declared_descendants: includeDeclaredDescendants(),
    };
  }

  function updateButtons() {
    const human = actor();
    const submit = $("v2-handoff-submit");
    const admit = $("v2-handoff-admit");
    if (submit) {
      submit.disabled = !prepared || !human || Boolean(submitted);
      submit.title = !prepared
        ? "Préparez d’abord la portée"
        : !human
          ? "Renseignez l’acteur humain"
          : submitted
            ? "Work Issue déjà créé"
            : "Créer un Work Issue sans lancer Hermes";
    }
    if (admit) {
      admit.disabled = !submitted || !human || Boolean(admitted);
      admit.title = !submitted
        ? "Créez d’abord le Work Issue"
        : !human
          ? "Renseignez l’acteur humain"
          : admitted
            ? "Handoff déjà admis"
            : "Autoriser ce Work Issue exact à être consommé par Hermes externe";
    }
  }

  function appendRows(host, rows) {
    const refs = document.createElement("dl");
    refs.className = "v2-handoff-refs";
    for (const [term, value] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = term;
      const dd = document.createElement("dd");
      dd.textContent = String(value ?? "—");
      refs.append(dt, dd);
    }
    host.append(refs);
  }

  function renderPrepared(payload) {
    const host = $("v2-handoff-preview");
    host.replaceChildren();
    const status = document.createElement("div");
    status.className = "v2-handoff-preview-status";
    const label = document.createElement("strong");
    label.textContent = "Handoff candidate";
    const effect = document.createElement("span");
    effect.textContent = `${payload.requested_effect} · exécution non autorisée`;
    status.append(label, effect);
    host.append(status);

    const resolution = payload.scope_resolution || {};
    appendRows(host, [
      ["Task Contract", payload.task_contract?.task_contract_ref],
      ["Context Pack", payload.context_pack?.context_pack_ref],
      ["Politique scope", resolution.policy || "root_only"],
      ["Descendants", resolution.descendants_added ?? 0],
      ["Entités incluses", payload.context_pack?.included_entities?.length ?? 0],
      ["Sources", payload.context_pack?.source_refs?.length ?? 0],
    ]);

    const warning = document.createElement("p");
    warning.className = "v2-handoff-warning";
    warning.textContent = "Candidate uniquement : ni Work Issue, ni admission, ni HermesRun à ce stade.";
    host.append(warning);
  }

  function renderSubmission(payload) {
    const host = $("v2-handoff-preview");
    const section = document.createElement("section");
    section.className = "v2-handoff-receipt";
    const title = document.createElement("strong");
    title.textContent = "Work Issue créé";
    section.append(title);
    appendRows(section, [
      ["Work Issue", payload.work_issue?.issue_id],
      ["Assigné à", payload.work_issue?.assigned_to],
      ["Statut", payload.work_issue?.status],
      ["HermesRun", payload.hermes_run_created ? "créé" : "aucun"],
    ]);
    host.append(section);
  }

  function renderAdmission(payload) {
    const host = $("v2-handoff-preview");
    const section = document.createElement("section");
    section.className = "v2-handoff-receipt v2-handoff-receipt--admission";
    const title = document.createElement("strong");
    title.textContent = "Admission créée";
    section.append(title);
    appendRows(section, [
      ["Admission", payload.admission_id],
      ["Décision", payload.decision],
      ["Prêt pour Hermes externe", payload.ready_for_external_runtime ? "oui" : "non"],
      ["Run consommateur", payload.consumed_by_run_id || "aucun"],
    ]);
    const note = document.createElement("p");
    note.className = "v2-handoff-warning";
    note.textContent = "Pantheon n’a rien dispatché : l’adapter Hermes externe doit consommer cet admission_id et déclarer son propre run.";
    section.append(note);
    host.append(section);
  }

  async function previewHandoff() {
    const question = $("v2-handoff-question").value.trim();
    if (question.length < 3) {
      $("v2-handoff-message").textContent = "Formulez une question avant de préparer le handoff.";
      return;
    }
    if (!token()) {
      $("v2-handoff-message").textContent = "Clé d’accès requise pour préparer le handoff.";
      return;
    }

    let request;
    try {
      request = baseRequest();
    } catch (error) {
      $("v2-handoff-message").textContent = error.message;
      return;
    }

    previewGeneration += 1;
    const generation = previewGeneration;
    prepared = null;
    submitted = null;
    admitted = null;
    updateButtons();
    $("v2-handoff-prepare").disabled = true;
    $("v2-handoff-message").textContent = "Préparation du Task Contract et du Context Pack…";

    try {
      const response = await fetch("../v1/cockpit/hermes-handoffs/preview", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      if (generation !== previewGeneration) return;
      if (!response.ok) throw new Error(payload.detail || response.statusText);
      prepared = {
        request,
        payload,
        submit_idempotency_key: idempotencyKey("handoff-submit"),
      };
      renderPrepared(payload);
      updateButtons();
      $("v2-handoff-message").textContent = "Portée préparée. Vérifiez-la avant de créer le Work Issue.";
    } catch (error) {
      if (generation !== previewGeneration) return;
      $("v2-handoff-preview").replaceChildren();
      $("v2-handoff-message").textContent = `Préparation refusée : ${error.message}`;
    } finally {
      if (generation === previewGeneration) $("v2-handoff-prepare").disabled = false;
    }
  }

  async function submitHandoff() {
    if (!prepared || !actor()) return;
    const button = $("v2-handoff-submit");
    button.disabled = true;
    $("v2-handoff-message").textContent = "Création du Work Issue à partir du preview exact…";
    try {
      const response = await fetch("../v1/cockpit/hermes-handoffs/submit", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token()}`,
          "Content-Type": "application/json",
          "X-Pantheon-Human-Actor": actor(),
        },
        body: JSON.stringify({
          ...prepared.request,
          expected_preview_digest: prepared.payload.preview_digest,
          expected_task_contract_ref: prepared.payload.task_contract.task_contract_ref,
          expected_context_pack_ref: prepared.payload.context_pack.context_pack_ref,
          idempotency_key: prepared.submit_idempotency_key,
        }),
      });
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      if (!response.ok) throw new Error(payload.detail || response.statusText);
      submitted = {
        payload,
        admission_idempotency_key: idempotencyKey("execution-admit"),
      };
      renderSubmission(payload);
      sessionStorage.setItem("pantheon-human-actor", actor());
      $("v2-handoff-message").textContent = "Work Issue créé. Aucun HermesRun n’a démarré.";
    } catch (error) {
      $("v2-handoff-message").textContent = `Création refusée : ${error.message}`;
    } finally {
      updateButtons();
    }
  }

  async function admitHandoff() {
    if (!submitted || !actor()) return;
    const handoffId = submitted.payload.handoff_id;
    const button = $("v2-handoff-admit");
    button.disabled = true;
    $("v2-handoff-message").textContent = "Création de l’admission d’exécution…";
    try {
      const response = await fetch(`../v1/cockpit/hermes-handoffs/${encodeURIComponent(handoffId)}/admissions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token()}`,
          "Content-Type": "application/json",
          "X-Pantheon-Human-Actor": actor(),
        },
        body: JSON.stringify({
          idempotency_key: submitted.admission_idempotency_key,
        }),
      });
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      if (!response.ok) throw new Error(payload.detail || response.statusText);
      admitted = payload;
      renderAdmission(payload);
      $("v2-handoff-message").textContent = "Admission créée. Pantheon n’a pas lancé Hermes.";
    } catch (error) {
      $("v2-handoff-message").textContent = `Admission refusée : ${error.message}`;
    } finally {
      updateButtons();
    }
  }

  function invalidate(message) {
    previewGeneration += 1;
    prepared = null;
    submitted = null;
    admitted = null;
    $("v2-handoff-preview")?.replaceChildren();
    if (message) $("v2-handoff-message").textContent = message;
    updateScopeLabel();
    updateButtons();
  }

  document.addEventListener("pantheon:v2-context-changed", event => {
    selectedContext = Array.isArray(event.detail?.selected) ? event.detail.selected : [];
    invalidate("Contexte sélectionné modifié : préparez à nouveau la portée.");
  });

  const stage = $("v2-stage");
  if (stage) {
    const observer = new MutationObserver(() => {
      invalidate("Carte courante modifiée : préparez à nouveau la portée.");
    });
    observer.observe(stage, { childList: true, subtree: false });
  }

  $("v2-handoff-prepare")?.addEventListener("click", () => void previewHandoff());
  $("v2-handoff-submit")?.addEventListener("click", () => void submitHandoff());
  $("v2-handoff-admit")?.addEventListener("click", () => void admitHandoff());
  $("v2-handoff-question")?.addEventListener("input", () => invalidate("Question modifiée : préparez à nouveau la portée."));
  $("v2-handoff-descendants")?.addEventListener("change", () => invalidate("Politique de descendants modifiée : préparez à nouveau la portée."));
  $("v2-handoff-actor")?.addEventListener("input", updateButtons);

  const rememberedActor = sessionStorage.getItem("pantheon-human-actor");
  if (rememberedActor && $("v2-handoff-actor")) $("v2-handoff-actor").value = rememberedActor;
  updateScopeLabel();
  updateButtons();
})();
