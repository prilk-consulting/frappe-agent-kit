# Changelog

## 0.2.0 — 2026-06-06

- **Task skills (Expo pattern):** `add-portal-page` and `add-custom-field` — guided end-to-end workflows with built-in verification steps
- **Generate→validate loop (Shopify pattern):** new `validate_doctype_json.py` bundled in frappe-dev; `/frappe-new-doctype` now refuses to migrate until the JSON passes (max 3 fix attempts)
- CI smoke-tests the new validator

## 0.1.0 — 2026-06-06

Initial release.

- **Skills (7):** frappe-dev (+ Jinja/print-format reference), frappe-test, frappe-portal, frappe-fixtures, frappe-upgrade, frappe-frontend, frappe-audit
- **Agents (4):** frappe-dev builder; frappe-security, frappe-schema, frappe-quality read-only auditors
- **Commands (2):** /frappe-new-app, /frappe-new-doctype
- **Bundled scripts:** `sort_nested_fixtures.py` (topo-sort tree-doctype fixtures after export), `resolve_hooks.py` (verify every hooks.py handler path resolves)
- Multi-assistant manifests: Claude Code (`.claude-plugin/`), Cursor (`.cursor-plugin/`), Codex (`.codex-plugin/`)
- All framework claims verified against Frappe v16.4.1 source; passes `claude plugin validate --strict`, claudelint, and agentskills spec checks
