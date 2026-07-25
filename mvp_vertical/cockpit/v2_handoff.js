(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  let selectedContext = [];
  let previewGeneration = 0;

  function token() {
    return $("v2-token")?.value || "";
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
    const selectedCount = selectedContext.length;
    if (!root) {
      $("v2-handoff-scope").textContent = "Aucune carte courante";
      return;
    }
    $("v2-handoff-scope").textContent = `${root.label} · carte seule + ${selectedCount} ajout(s) explicite(s)`;
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

  function renderPreview(payload) {
    const host = $("v2-handoff-preview");
    host.replaceChildren();

    const status = document.createElement("div");
    status.className = "v2-handoff-preview-status";
    const label = document.createElement("strong");
    label.textContent = "Handoff candidate";
    const effect = document.createElement("span");
    effect.textContent = `${payload.requested_effect} · exécution non autorisée`;
    status.append(label, effect);

    const refs = document.createElement("dl");
    refs.className = "v2-handoff-refs";
    const rows = [
      ["Task Contract", payload.task_contract?.task_contract_ref],
      ["Context Pack", payload.context_pack?.context_pack_ref],
      ["Entités incluses", payload.context_pack?.included_entities?.length ?? 0],
      ["Sources", payload.context_pack?.source_refs?.length ?? 0],
    ];
    for (const [term, value] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = term;
      const dd = document.createElement("dd");
      dd.textContent = String(value ?? "—");
      refs.append(dt, dd);
    }

    const warning = document.createElement("p");
    warning.className = "v2-handoff-warning";
    warning.textContent = "Preview uniquement : aucun Work Issue créé, aucun run Hermes lancé, aucune Evidence admise.";

    host.append(status, refs, warning);
    $("v2-handoff-execute").disabled = true;
    $("v2-handoff-execute").title = "Exécution volontairement non branchée : Task Contract/Context Pack candidates seulement";
  }

  async function previewHandoff() {
    const question = $("v2-handoff-question").value.trim();
    if (question.length < 3) {
      $("v2-handoff-message").textContent = "Formulez une question avant de préparer le handoff.";
      return;
    }
    const currentToken = token();
    if (!currentToken) {
      $("v2-handoff-message").textContent = "Clé d’accès requise pour préparer le handoff.";
      return;
    }

    let envelope;
    try {
      envelope = buildEnvelope();
    } catch (error) {
      $("v2-handoff-message").textContent = error.message;
      return;
    }

    previewGeneration += 1;
    const generation = previewGeneration;
    $("v2-handoff-prepare").disabled = true;
    $("v2-handoff-message").textContent = "Préparation du Task Contract et du Context Pack…";

    try {
      const response = await fetch("../v1/cockpit/hermes-handoffs/preview", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${currentToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
          card_context_envelope: envelope,
          selected_context: selectedContext.map(item => ({
            entity_id: item.entity_id,
            entity_type: item.entity_type,
          })),
        }),
      });
      const payload = await response.json().catch(() => ({ detail: response.statusText }));
      if (generation !== previewGeneration) return;
      if (!response.ok) throw new Error(payload.detail || response.statusText);
      renderPreview(payload);
      $("v2-handoff-message").textContent = "Portée préparée. Vérifiez-la avant toute future exécution.";
    } catch (error) {
      if (generation !== previewGeneration) return;
      $("v2-handoff-preview").replaceChildren();
      $("v2-handoff-message").textContent = `Préparation refusée : ${error.message}`;
    } finally {
      if (generation === previewGeneration) $("v2-handoff-prepare").disabled = false;
    }
  }

  document.addEventListener("pantheon:v2-context-changed", event => {
    selectedContext = Array.isArray(event.detail?.selected) ? event.detail.selected : [];
    previewGeneration += 1;
    $("v2-handoff-preview")?.replaceChildren();
    updateScopeLabel();
  });

  const stage = $("v2-stage");
  if (stage) {
    const observer = new MutationObserver(() => {
      previewGeneration += 1;
      $("v2-handoff-preview")?.replaceChildren();
      updateScopeLabel();
    });
    observer.observe(stage, { childList: true, subtree: false });
  }

  $("v2-handoff-prepare")?.addEventListener("click", () => void previewHandoff());
  $("v2-handoff-question")?.addEventListener("input", () => {
    previewGeneration += 1;
    $("v2-handoff-preview")?.replaceChildren();
    $("v2-handoff-message").textContent = "Question modifiée : préparez à nouveau la portée.";
  });

  updateScopeLabel();
})();
