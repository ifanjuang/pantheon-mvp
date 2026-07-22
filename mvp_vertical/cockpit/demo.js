(() => {
  const DEMO_PROJECT = "demo-architecture";
  const nativeFetch = window.fetch.bind(window);
  const recent = hours => new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

  const fixtures = {
    documents: {
      parent_project_id: DEMO_PROJECT,
      documents: [
        {
          document_id: "doc-cctp-lot-06",
          card_id: "card-doc-cctp-lot-06",
          title: "CCTP — Lot 06 Revêtements",
          parent_project_id: DEMO_PROJECT,
          source_ref: "demo/30_DCE/DEMO_A1_DCE_IFJ_CCTP_LOT-06_2026-07-22.pdf",
          source_digest: "sha256:demo-document-not-evidence",
          media_type: "application/pdf",
          analysis_status: "ready",
          naming: {
            object_name: "CCTP — Lot 06 Revêtements",
            document_type: "CCTP",
            phase_code: "DCE",
            revision_index: "A1",
            phase_folder: "30_DCE",
          },
          extraction: {
            chunk_count: 42,
            finished_at: recent(2),
            converter: "Docling",
            converter_version: "v1.21.0",
            quality_flags: ["fixture synthétique de démonstration"],
          },
          authority: {
            is_source: false,
            is_evidence: false,
            is_memory: false,
          },
        },
      ],
    },
    knowledge: {
      parent_project_id: DEMO_PROJECT,
      knowledge: [
        {
          knowledge_id: "knowledge-revetements-demo",
          card_id: "card-knowledge-revetements-demo",
          title: "Prescriptions revêtements à relire",
          family: "prescription_technique",
          version: 2,
          created_by: "fixture-demo",
          created_at: recent(30),
          updated_at: recent(1),
          source_chunk_refs: ["doc-cctp-lot-06#chunk-12", "doc-cctp-lot-06#chunk-18"],
          review_status: "needs_review",
          parent_project_id: DEMO_PROJECT,
          document_ref: "doc-cctp-lot-06",
          markdown_digest: "sha256:demo-knowledge-not-evidence",
        },
      ],
    },
    workIssues: {
      parent_project_id: DEMO_PROJECT,
      scope_match: "exact_case_ref",
      work_issues: [
        {
          work_issue: {
            issue_id: "WI-DEMO-001",
            title: "Valider le parquet compatible plancher chauffant",
            issue_type: "decision",
            priority: "high",
            status: "review",
            assigned_to: "human",
            requested_effect: "review_and_decide",
            case_ref: DEMO_PROJECT,
            version: 3,
            updated_at: recent(0.5),
            description: "Comparer la prescription candidate aux pièces contractuelles et confirmer l’épaisseur d’usure attendue.",
            task_contract_ref: "demo/task_contract.yaml",
            context_pack_ref: "demo/context_pack.yaml",
          },
          comments: [
            {
              author: "Hermes",
              body: "Retour candidat préparé ; la compatibilité doit rester vérifiée sur la fiche fabricant.",
            },
          ],
          hermes_runs: [
            {
              run_id: "run-demo-001",
              status: "returned",
              normalized_return: {
                outcome: "candidate",
                summary: "Compatibilité probable, validation documentaire encore requise.",
              },
            },
          ],
          events: [
            { event_type: "issue_created", actor_kind: "human", occurred_at: recent(5) },
            { event_type: "hermes_returned", actor_kind: "hermes", occurred_at: recent(1) },
            { event_type: "review_requested", actor_kind: "system", occurred_at: recent(0.5) },
          ],
        },
      ],
    },
    resources: {
      parent_project_id: DEMO_PROJECT,
      documents: [
        {
          document_id: "doc-cctp-lot-06",
          format: {
            family: "pdf",
            extension: "pdf",
            media_type: "application/pdf",
          },
          content: {
            composition: "text_and_images",
            has_text: true,
            has_images: true,
            has_tables: true,
            observed_image_items: 3,
            observed_table_items: 2,
          },
        },
      ],
      knowledge_sites: [
        {
          knowledge_id: "knowledge-revetements-demo",
          sites: [
            {
              host: "www.qualitel.org",
              site_kind: "public_information_portal",
              url: "https://www.qualitel.org/particuliers/conseils/sol-plancher-chauffant/",
            },
            {
              host: "www.cstb.fr",
              site_kind: "hierarchical_safety_reference",
              url: "https://www.cstb.fr/fr/",
            },
          ],
        },
      ],
      crawl_capability: {
        status: "not_authorized",
        vector_status: "not_indexed",
      },
    },
  };

  const jsonResponse = (payload, status = 200) => new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });

  const parseBody = init => {
    try {
      return JSON.parse(init?.body || "{}");
    } catch (_error) {
      return {};
    }
  };

  window.fetch = async (input, init = {}) => {
    const requestUrl = typeof input === "string" ? input : input.url;
    const url = new URL(requestUrl, window.location.href);
    if (!url.pathname.startsWith("/v1/")) return nativeFetch(input, init);

    const method = String(init.method || (typeof input !== "string" ? input.method : "GET") || "GET").toUpperCase();
    const base = `/v1/projects/${DEMO_PROJECT}`;

    if (method === "GET" && url.pathname === `${base}/documents`) return jsonResponse(fixtures.documents);
    if (method === "GET" && url.pathname === `${base}/knowledge`) return jsonResponse(fixtures.knowledge);
    if (method === "GET" && url.pathname === `${base}/work-issues`) return jsonResponse(fixtures.workIssues);
    if (method === "GET" && url.pathname === `${base}/resource-profiles`) return jsonResponse(fixtures.resources);

    if (method === "POST" && url.pathname === `${base}/effects/preview`) {
      return jsonResponse({
        status: "proposal_only",
        proposals: [
          {
            effect: "UPDATE",
            effect_source: "synthetic_demo_fixture",
            confidence: "medium",
            score: 0.84,
            target: {
              object_type: "knowledge",
              object_id: "knowledge-revetements-demo",
              title: "Prescriptions revêtements à relire",
              current_status: "needs_review",
            },
            reasons: [
              "Correspondance déterministe avec la Knowledge existante.",
              "La démonstration ne persiste et n’applique aucun effet.",
            ],
          },
        ],
        limits: [
          "Données entièrement synthétiques.",
          "Aucun objet n’est créé, modifié, remplacé ou marqué en conflit.",
        ],
      });
    }

    if (method === "POST" && /\/knowledge\/[^/]+\/site-manifests\/preview$/.test(url.pathname)) {
      const request = parseBody(init);
      const sites = (request.sites || []).map(site => {
        const parsed = new URL(site.url);
        return {
          host: parsed.host,
          url: site.url,
          path_prefixes: site.path_prefixes || ["/"],
          max_depth: Number(site.max_depth ?? 2),
        };
      });
      return jsonResponse({
        status: "candidate",
        manifest_id: "demo-structure-manifest",
        manifest_digest: "sha256:demo-manifest-not-persisted",
        manifest: { mode: "structure_only", sites },
        execution: { network_requests: 0, persistence_effects: 0 },
        capability_slot: {
          candidate_hermes_binding: "to_verify",
          activation: "not_authorized",
        },
        warnings: ["Fixture synthétique : aucun site n’a été contacté."],
        gates: [
          { gate: "human_task_scope_approval", status: "open" },
          { gate: "binding_health_review", status: "open" },
          { gate: "activation_authorization", status: "open" },
        ],
      });
    }

    if (method === "POST" && /\/knowledge\/[^/]+\/navigation-profiles\/preview$/.test(url.pathname)) {
      return jsonResponse({
        status: "candidate",
        execution: { network_requests: 0, persistence_effects: 0 },
        profiles: [],
        gates: ["human_task_scope_approval", "binding_health_review", "activation_authorization"],
      });
    }

    if (/\/knowledge\/[^/]+\/updates\/(preview|apply)$/.test(url.pathname)) {
      return jsonResponse({
        detail: "DÉMO statique : les mises à jour Knowledge sont désactivées et aucune signature n’est simulée.",
      }, 403);
    }

    if (method !== "GET") {
      return jsonResponse({
        detail: "DÉMO statique : toute mutation non explicitement simulée est refusée.",
      }, 403);
    }

    return jsonResponse({ detail: "Ressource absente de la fixture de démonstration." }, 404);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const project = document.getElementById("project");
    const token = document.getElementById("token");
    const load = document.getElementById("load");
    const network = document.getElementById("network");
    if (!project || !token || !load) return;

    project.value = DEMO_PROJECT;
    token.value = "demo-read-only";
    const markDemo = () => {
      if (network) network.textContent = "démo statique";
    };
    window.addEventListener("online", markDemo);
    window.addEventListener("offline", markDemo);
    markDemo();
    load.click();
  });
})();
