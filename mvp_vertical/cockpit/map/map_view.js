(() => {
  "use strict";

  // Read-only D3-free SVG renderer for the Cockpit knowledge map.
  //
  // Boundary (see map/README.md): binds to the in-memory projection
  // (state.cards / state.children), performs no fetch, no mutation, launches no
  // run, promotes no memory. It reshapes and draws; it decides nothing.
  //
  // Core rendering is deliberately minimal (nodes + containment + group labels +
  // swappable layout). Richer treatments (metaballs, subject lens, time
  // scrubber) belong to the standalone demo / a later phase, not this bounded
  // slice.

  const NS = "http://www.w3.org/2000/svg";

  // Neutral fallback palette by subject bucket; production reads real tokens
  // from tag_registry (passed via opts.subjectColor). Colour is never the sole
  // identifier — a subject icon disambiguates same-colour subjects.
  const FALLBACK = "#66758c";

  function el(name, attrs) {
    const node = document.createElementNS(NS, name);
    if (attrs) for (const k in attrs) node.setAttribute(k, attrs[k]);
    return node;
  }

  function create(svg, data, opts = {}) {
    const width = opts.width || 1000;
    const height = opts.height || 620;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    const model = window.PantheonMapGraphModel;
    const layouts = window.PantheonMapLayouts;
    if (!model || !layouts) throw new Error("Map model/layouts unavailable");

    const graph = model.build(data.cards, data.children);
    const byId = new Map(graph.nodes.map(n => [n.id, n]));
    const subjectColor = typeof opts.subjectColor === "function"
      ? opts.subjectColor
      : () => FALLBACK;

    const state = {
      layout: opts.layout || "cluster",
      groupBy: opts.groupBy || "subject", // "subject" | "family"
    };
    const groupOf = n => (state.groupBy === "family" ? (n.family || "—") : (n.subject || "—"));

    const gLinks = el("g", { "data-layer": "links" });
    const gNodes = el("g", { "data-layer": "nodes" });
    const gLabels = el("g", { "data-layer": "labels" });
    svg.append(gLinks, gNodes, gLabels);

    const nodeEls = new Map();
    for (const n of graph.nodes) {
      const g = el("g", { "data-id": n.id, tabindex: "0", role: "button" });
      g.setAttribute("aria-label", n.title);
      const c = el("circle", { r: 9, "stroke-width": 1.5 });
      const title = el("title");
      title.textContent = `${n.title}${n.subject ? " · " + n.subject : ""}`;
      g.append(c, title);
      gNodes.append(g);
      nodeEls.set(n.id, { g, c, n });
    }

    const linkEls = graph.links.map(link => {
      const line = el("line", { "data-kind": link.kind });
      line.setAttribute("stroke", link.kind === "lineage" ? "#5f83b8" : "#c3cbd8");
      line.setAttribute("stroke-width", link.kind === "lineage" ? 1.6 : 1);
      gLinks.append(line);
      return { line, ...link };
    });

    function positions() {
      return layouts.layout(state.layout, graph.nodes, { width, height, groupOf });
    }

    function render() {
      const pos = positions();
      for (const [id, e] of nodeEls) {
        const p = pos[id] || { x: width / 2, y: height / 2 };
        e.x = p.x; e.y = p.y;
        e.g.setAttribute("transform", `translate(${p.x} ${p.y})`);
        e.c.setAttribute("fill", subjectColor(e.n.subject));
        e.c.setAttribute("stroke", e.n.origin === "hermes" ? "#9aa4b4" : "#3a4657");
        e.c.setAttribute("stroke-dasharray", e.n.origin === "hermes" ? "4 3" : "");
      }
      for (const l of linkEls) {
        const a = nodeEls.get(l.source), b = nodeEls.get(l.target);
        if (!a || !b) { l.line.style.display = "none"; continue; }
        l.line.style.display = "";
        l.line.setAttribute("x1", a.x); l.line.setAttribute("y1", a.y);
        l.line.setAttribute("x2", b.x); l.line.setAttribute("y2", b.y);
      }
      renderLabels(pos);
    }

    function renderLabels(pos) {
      gLabels.textContent = "";
      const groups = new Map();
      for (const n of graph.nodes) {
        const k = groupOf(n);
        let b = groups.get(k); if (!b) { b = []; groups.set(k, b); }
        b.push(pos[n.id] || { x: width / 2, y: height / 2 });
      }
      for (const [k, pts] of groups) {
        const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length;
        const minY = Math.min(...pts.map(p => p.y));
        const t = el("text", { x: cx, y: Math.max(16, minY - 16), "text-anchor": "middle", "font-size": 11, "font-family": "ui-monospace, monospace", fill: "#6c7789" });
        t.textContent = `${k} · ${pts.length}`;
        gLabels.append(t);
      }
    }

    render();

    return {
      setLayout(name) { state.layout = name; render(); },
      setGroupBy(mode) { state.groupBy = mode; render(); },
      render,
      graph,
      destroy() { svg.textContent = ""; nodeEls.clear(); },
    };
  }

  window.PantheonMapView = Object.freeze({ create });
})();
