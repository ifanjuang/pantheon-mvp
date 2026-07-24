(() => {
  "use strict";

  const NAMESPACES = Object.freeze({
    _: { key: "affaires", label: "Affaires" },
    "#": { key: "capabilities", label: "Capacités" },
    "@": { key: "people", label: "Personnes" },
    "*": { key: "global", label: "Recherche globale" },
  });

  const providers = new Map();

  function normalize(value) {
    return String(value ?? "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLocaleLowerCase("fr")
      .trim();
  }

  function parse(input) {
    const raw = String(input ?? "");
    const prefix = raw.charAt(0);
    const namespace = NAMESPACES[prefix] ? prefix : null;
    return {
      raw,
      namespace,
      namespaceKey: namespace ? NAMESPACES[namespace].key : null,
      query: normalize(namespace ? raw.slice(1) : raw),
    };
  }

  function searchableText(item) {
    const tags = Array.isArray(item.tags)
      ? item.tags.map(tag => typeof tag === "string" ? tag : tag?.name)
      : [];
    const aliases = Array.isArray(item.aliases) ? item.aliases : [];
    return normalize([
      item.label,
      item.secondary_label,
      item.title,
      item.display_name,
      item.description,
      ...tags,
      ...aliases,
      ...(Array.isArray(item.search_terms) ? item.search_terms : []),
    ].filter(Boolean).join(" "));
  }

  function scoreItem(item, query, namespace) {
    if (!query) return 1;
    const label = normalize(item.label || item.title || item.display_name);
    const haystack = searchableText(item);

    if (namespace === "_") {
      if (label.startsWith(query)) return 100;
      if (label.includes(query)) return 70;
      return 0;
    }

    if (label.startsWith(query)) return 90;
    if (label.includes(query)) return 70;
    if (haystack.includes(query)) return namespace === "*" ? 60 : 45;
    return 0;
  }

  function normalizeResult(item, namespaceKey) {
    return {
      entity_id: item.entity_id ?? item.id ?? null,
      entity_type: item.entity_type ?? item.type ?? namespaceKey,
      label: item.label ?? item.title ?? item.display_name ?? "Sans titre",
      secondary_label: item.secondary_label ?? item.subtitle ?? "",
      icon_key: item.icon_key ?? null,
      tags: Array.isArray(item.tags) ? item.tags : [],
      scope: item.scope ?? null,
      status: item.status ?? null,
      selected: Boolean(item.selected),
      aliases: Array.isArray(item.aliases) ? item.aliases : [],
      search_terms: Array.isArray(item.search_terms) ? item.search_terms : [],
      source: item.source ?? null,
    };
  }

  function registerProvider(namespaceKey, provider) {
    if (!Object.values(NAMESPACES).some(spec => spec.key === namespaceKey)) {
      throw new Error(`Unknown context namespace provider: ${namespaceKey}`);
    }
    if (typeof provider !== "function") {
      throw new TypeError("Context provider must be a function");
    }
    providers.set(namespaceKey, provider);
  }

  function unregisterProvider(namespaceKey) {
    providers.delete(namespaceKey);
  }

  async function providerItems(namespaceKey, request) {
    const provider = providers.get(namespaceKey);
    if (!provider) return [];
    const result = await provider(request);
    if (!Array.isArray(result)) return [];
    return result.map(item => normalizeResult(item, namespaceKey));
  }

  async function resolve(input, options = {}) {
    const parsed = parse(input);
    const limit = Math.max(1, Number(options.limit) || 12);
    const request = {
      query: parsed.query,
      namespace: parsed.namespace,
      namespaceKey: parsed.namespaceKey,
      currentScope: options.currentScope ?? null,
      limit,
    };

    if (!parsed.namespace) {
      return { ...parsed, results: [], reason: "namespace_required" };
    }

    let candidates = [];
    if (parsed.namespace === "*") {
      const keys = ["affaires", "capabilities", "people", "global"];
      const groups = await Promise.all(keys.map(key => providerItems(key, request)));
      const seen = new Set();
      for (const item of groups.flat()) {
        const key = `${item.entity_type}:${item.entity_id ?? item.label}`;
        if (seen.has(key)) continue;
        seen.add(key);
        candidates.push(item);
      }
    } else {
      candidates = await providerItems(parsed.namespaceKey, request);
    }

    const ranked = candidates
      .map(item => ({ item, score: scoreItem(item, parsed.query, parsed.namespace) }))
      .filter(entry => entry.score > 0)
      .sort((a, b) => b.score - a.score || a.item.label.localeCompare(b.item.label, "fr"))
      .slice(0, limit)
      .map(entry => entry.item);

    return { ...parsed, results: ranked, reason: null };
  }

  window.PantheonContextResolver = Object.freeze({
    namespaces: NAMESPACES,
    parse,
    resolve,
    registerProvider,
    unregisterProvider,
  });
})();
