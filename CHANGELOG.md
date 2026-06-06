# Changelog

## 0.1.0 — 2026-06-06

Initial release.

- **Skills (7):** frappe-dev (+ Jinja/print-format reference), frappe-test, frappe-portal, frappe-fixtures, frappe-upgrade, frappe-frontend, frappe-audit
- **Agents (4):** frappe-dev builder; frappe-security, frappe-schema, frappe-quality read-only auditors
- **Commands (2):** /frappe-new-app, /frappe-new-doctype
- **Bundled scripts:** `sort_nested_fixtures.py` (topo-sort tree-doctype fixtures after export), `resolve_hooks.py` (verify every hooks.py handler path resolves)
- Multi-assistant manifests: Claude Code (`.claude-plugin/`), Cursor (`.cursor-plugin/`), Codex (`.codex-plugin/`)
- All framework claims verified against Frappe v16.4.1 source; passes `claude plugin validate --strict`, claudelint, and agentskills spec checks
