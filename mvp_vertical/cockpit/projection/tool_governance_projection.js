(() => {
  "use strict";

  const base = window.PantheonStructuredInterface;
  if (!base?.buildCardProjection) throw new Error("Structured interface unavailable for tool governance projection");

  const originalBuildCardProjection = base.buildCardProjection.bind(base);
  const text = (value, fallback = "Non observé") => value == null || value === "" ? fallback : String(value);

  function anchorLabel(anchor) {
    if (!anchor || typeof anchor !== "object") return "Non observée";
    const kind = text(anchor.kind, "type inconnu");
    const value = text(anchor.value, "valeur inconnue");
    return `${kind} · ${value}`;
  }

  function scopeLabel(scope) {
    if (!scope || typeof scope !== "object") return "Non activé / non observé";
    return [scope.scope_type, scope.scope_id].filter(Boolean).join(" · ") || "Scope inconnu";
  }

  function toolGovernanceRows(input) {
    const governance = input.capability_governance;
    if (!governance || typeof governance !== "object" || Array.isArray(governance)) return [];

    const observation = governance.compatibility_observation;
    const rows = [
      ["Capability Binding", text(governance.binding_id)],
      ["Release exacte", anchorLabel(governance.implementation_anchor)],
      ["Activation gouvernée", text(governance.activation_state, "Non activée / non observée")],
      ["Scope d’activation", scopeLabel(governance.activation_scope)],
      ["Compatibilité", text(observation?.compatibility_status)],
      ["Sécurité", text(observation?.safety_status)],
      ["Fraîcheur", text(observation?.freshness_status)],
      ["Observation source", text(observation?.source_observation_ref)],
      ["Effet d’autorisation", "Aucun — projection uniquement"],
    ];
    return rows;
  }

  function buildCardProjection(input) {
    const projection = originalBuildCardProjection(input) || {};
    if (input?.entity_type !== "tool") return projection;

    const governanceRows = toolGovernanceRows(input);
    if (!governanceRows.length) return projection;

    return {
      ...projection,
      back: [...(Array.isArray(input.back) ? input.back : []), ...governanceRows],
    };
  }

  window.PantheonStructuredInterface = Object.freeze({
    ...base,
    buildCardProjection,
  });
})();
