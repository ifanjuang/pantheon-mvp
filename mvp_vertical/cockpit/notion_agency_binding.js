(() => {
  "use strict";

  const MODES = Object.freeze(["disabled", "read_only"]);
  const DEFAULT_COLLECTIONS = Object.freeze({
    affaires: "_Affaires",
    people: "_Personnes",
    organizations: "_Sociétés",
    participations: "_Intervenants",
  });

  function field(record, name) {
    return record?.fields?.[name] ?? record?.[name] ?? null;
  }

  function text(value) {
    if (value == null) return "";
    if (typeof value === "string" || typeof value === "number") return String(value);
    if (typeof value === "object" && typeof value.label === "string") return value.label;
    if (Array.isArray(value)) return value.map(text).filter(Boolean).join(", ");
    return "";
  }

  function sourceProjection(record, collection, workspaceLabel) {
    return {
      system: "notion",
      collection,
      workspace: workspaceLabel || null,
      external_id: record?.external_id ?? record?.id ?? null,
      url: record?.url ?? record?.source_url ?? null,
      authority: "external_owner_projection",
    };
  }

  function normalizeAffaire(record, config) {
    const code = text(field(record, "Code")) || text(record.label) || "Affaire sans code";
    const status = text(field(record, "Statut"));
    const phase = text(field(record, "Phase"));
    const location = text(field(record, "Lieu"));
    const secondary = [status, phase, location].filter(Boolean).join(" · ");

    return {
      entity_id: record.external_id ?? record.id ?? record.url,
      entity_type: "project",
      label: code,
      secondary_label: secondary,
      description: text(field(record, "Description")),
      status: status || null,
      tags: Array.isArray(record.tags) ? record.tags : [],
      aliases: Array.isArray(record.aliases) ? record.aliases : [],
      search_terms: [
        phase,
        location,
        text(field(record, "Numéro de Parcelle")),
        text(field(record, "Zone PLU")),
        text(field(record, "No Permis")),
        text(field(record, "type ERP")),
      ].filter(Boolean),
      scope: { system: "notion", collection: config.collections.affaires },
      source: sourceProjection(record, config.collections.affaires, config.workspaceLabel),
    };
  }

  function normalizePerson(record, config) {
    const name = text(field(record, "Nom")) || text(record.label) || "Personne sans nom";
    const company = text(record.company_label ?? field(record, "Société"));
    return {
      entity_id: record.external_id ?? record.id ?? record.url,
      entity_type: "person",
      label: name,
      secondary_label: company,
      description: "",
      status: record.status ?? null,
      tags: Array.isArray(record.tags) ? record.tags : [],
      aliases: Array.isArray(record.aliases) ? record.aliases : [],
      search_terms: [
        text(field(record, "E-mail")),
        text(field(record, "Numéro")),
        text(field(record, "adresse")),
        company,
      ].filter(Boolean),
      scope: { system: "notion", collection: config.collections.people },
      source: sourceProjection(record, config.collections.people, config.workspaceLabel),
    };
  }

  function normalizeOrganization(record, config) {
    const name = text(field(record, "Name")) || text(record.label) || "Société sans nom";
    return {
      entity_id: record.external_id ?? record.id ?? record.url,
      entity_type: "organization",
      label: name,
      secondary_label: text(field(record, "siret")),
      description: "",
      status: record.status ?? null,
      tags: Array.isArray(record.tags) ? record.tags : [],
      aliases: Array.isArray(record.aliases) ? record.aliases : [],
      search_terms: [
        text(field(record, "E-mail")),
        text(field(record, "Téléphone")),
        text(field(record, "Adresse")),
        text(field(record, "siret")),
      ].filter(Boolean),
      scope: { system: "notion", collection: config.collections.organizations },
      source: sourceProjection(record, config.collections.organizations, config.workspaceLabel),
    };
  }

  function normalizeParticipation(record, config) {
    const role = text(field(record, "Rôle"));
    const type = text(field(record, "Type"));
    const code = text(field(record, "Code"));
    const responsible = text(record.responsible_label ?? field(record, "Responsable"));
    const company = text(record.company_label ?? field(record, "Société"));
    const label = code || [role, responsible, company].filter(Boolean).join(" · ") || "Intervenant";

    return {
      entity_id: record.external_id ?? record.id ?? record.url,
      entity_type: "project_participation",
      label,
      secondary_label: [type, role, company].filter(Boolean).join(" · "),
      description: "",
      status: record.status ?? null,
      tags: Array.isArray(record.tags) ? record.tags : [],
      aliases: Array.isArray(record.aliases) ? record.aliases : [],
      search_terms: [role, type, responsible, company, text(record.project_label)].filter(Boolean),
      scope: { system: "notion", collection: config.collections.participations },
      source: sourceProjection(record, config.collections.participations, config.workspaceLabel),
    };
  }

  function normalizePayload(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.results)) return payload.results;
    return [];
  }

  function create(options = {}) {
    const mode = options.mode ?? "disabled";
    if (!MODES.includes(mode)) throw new Error(`Unsupported Notion agency binding mode: ${mode}`);

    const resolver = options.resolver ?? window.PantheonContextResolver;
    const transport = options.transport;
    const config = {
      mode,
      workspaceLabel: options.workspaceLabel ?? null,
      collections: { ...DEFAULT_COLLECTIONS, ...(options.collections ?? {}) },
    };

    let attached = false;
    let detachCallbacks = [];

    async function query(kind, request) {
      if (config.mode !== "read_only") return [];
      if (typeof transport !== "function") {
        throw new Error("Read-only Notion binding requires an injected bounded transport");
      }
      const payload = await transport({
        operation: "search",
        effect: "read_only",
        provider: "notion",
        collection: config.collections[kind],
        query: request.query,
        limit: request.limit,
        currentScope: request.currentScope,
      });
      return normalizePayload(payload);
    }

    async function affairesProvider(request) {
      return (await query("affaires", request)).map(record => normalizeAffaire(record, config));
    }

    async function peopleProvider(request) {
      return (await query("people", request)).map(record => normalizePerson(record, config));
    }

    async function globalProvider(request) {
      const [organizations, participations] = await Promise.all([
        query("organizations", request),
        query("participations", request),
      ]);
      return [
        ...organizations.map(record => normalizeOrganization(record, config)),
        ...participations.map(record => normalizeParticipation(record, config)),
      ];
    }

    function attach() {
      if (attached || config.mode === "disabled") return status();
      if (!resolver?.registerProvider) throw new Error("Pantheon Context Resolver is unavailable");
      detachCallbacks = [
        resolver.registerProvider("affaires", affairesProvider),
        resolver.registerProvider("people", peopleProvider),
        resolver.registerProvider("global", globalProvider),
      ];
      attached = true;
      return status();
    }

    function detach() {
      detachCallbacks.splice(0).forEach(detach => detach());
      attached = false;
      return status();
    }

    function status() {
      return {
        provider: "notion",
        mode: config.mode,
        attached,
        workspace_label: config.workspaceLabel,
        collections: { ...config.collections },
        write_effect: false,
        direct_browser_credentials: false,
        health_inferred: false,
        adoption_inferred: false,
      };
    }

    return Object.freeze({ attach, detach, status, config: Object.freeze(config) });
  }

  window.PantheonNotionAgencyBinding = Object.freeze({
    modes: MODES,
    defaultCollections: DEFAULT_COLLECTIONS,
    create,
  });
})();