# Cockpit configuration

Local project files and web-site address lists use separate read-only locations.

```text
MVP_DOCUMENT_ROOT=/documents
MVP_SITE_LISTS_JSON=/config/site_lists.json
```

`site_lists.json` is an address registry only. It does not authorize fetching, crawling, indexing, skill installation or activation.

Expected shape:

```json
{
  "schema": "pantheon.site_lists.v1",
  "projects": {
    "project-maison-a": [
      {
        "knowledge_id": "knowledge.reglementation",
        "label": "Références réglementaires",
        "sites": [
          {
            "url": "https://www.legifrance.gouv.fr/",
            "label": "Légifrance"
          },
          {
            "url": "https://sitesecurite.com/",
            "label": "SiteSecurite"
          }
        ]
      }
    ]
  }
}
```

```text
address listed != page fetched
JSON present != crawl authorized
site listed != skill installed
```
