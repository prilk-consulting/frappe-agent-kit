# Frappe Agent Kit

Production-grade [Frappe Framework](https://frappeframework.com) & [ERPNext](https://erpnext.com) skills, agents, and scaffolding commands for [Claude Code](https://claude.com/claude-code).

Built from years of shipping Frappe apps in production — including the gotchas that only show up on a fresh `bench migrate` of a downstream site, never on your dev bench.

## Install

```
/plugin marketplace add prilk-consulting/frappe-agent-kit
/plugin install frappe-kit@prilk
```

## What's inside

### Skills (loaded on demand, also invocable as `/name`)

| Skill | Covers |
|-------|--------|
| `frappe-dev` | DocType controllers, whitelisted APIs, query builder, permissions (5 layers, deny-only hooks), background jobs, caching, client scripts, Jinja sandbox traps, custom-app structure |
| `frappe-test` | FrappeTestCase isolation, test_records, permission testing, `allow_tests` setup, the `frappe.db.commit()`-in-tests trap, CI invocations |
| `frappe-portal` | WebsiteGenerator vs portal-list patterns, `website_route_rules`, `has_website_permission`, `portal_users` access, upgrade-safe extension of ERPNext portal pages |
| `frappe-fixtures` | Fixture export/sync, Workspace + Sidebar naming rule (auto-gen override trap), nested-set fixture ordering (fresh-site crash), per-environment ID scrubbing |
| `frappe-upgrade` | patches.txt pre/post model sync, idempotent patch design, reload_doc/rename_field, version upgrades, uninstall-order pitfalls |
| `frappe-frontend` | React (frappe-react-sdk) & Vue (frappe-ui) SPAs, the dev/prod boot dance, Vite base-path triad, socket port gotchas, bench build wiring |
| `frappe-audit` | Orchestrates a full app audit by delegating to the specialist agents below |

### Task skills (guided end-to-end workflows)

| Skill | Does |
|-------|------|
| `add-portal-page` | Expose a DocType on the portal: access rule → list context → hooks → templates → negative-test verification |
| `add-custom-field` | Add a field to another app's DocType the upgrade-safe way: collision check → install.py → apply → verify |

### Agents

| Agent | Role |
|-------|------|
| `frappe-dev` | Build specialist — DocTypes, server/client scripts, hooks, frontends. Preloads all skills. |
| `frappe-security` | Read-only auditor — permission enforcement, injection, guest surface, secret exposure |
| `frappe-schema` | Read-only auditor — DocType JSON quality, field types, constraints, permission matrix |
| `frappe-quality` | Read-only auditor — hooks wiring, install idempotency, patch safety, conventions, tests |

### Commands

| Command | Does |
|---------|------|
| `/frappe-kit:frappe-new-app` | `bench new-app` + production extension skeleton (install.py, custom/, hooks wiring) |
| `/frappe-kit:frappe-new-doctype` | Scaffold DocType JSON + controller + client script + real test, then migrate & verify |

## See it work

[**Sample `/frappe-audit` report**](docs/sample-audit-report.md) — real output from auditing a production app: three specialist agents in parallel, two headline security findings verified against source before reporting, severity-bucketed with `file:line` citations.

## Why this exists

Generic AI coding agents write Frappe code that *looks* right and fails in production: `get_all` leaking rows across users in whitelisted methods, `after_install` routines that crash on the second run, fixtures that migrate fine on the dev site and explode on a fresh install, `frm.call` silently clobbering Password fields. This kit encodes the framework's actual contracts — and the failure modes — so agents get it right the first time.

### Bundled scripts (skills that verify, not just advise)

| Script | Does |
|--------|------|
| `skills/frappe-fixtures/scripts/sort_nested_fixtures.py` | Topo-sorts tree-doctype fixture JSON after export — prevents the fresh-site `update_add_node` crash |
| `skills/frappe-audit/scripts/resolve_hooks.py` | Resolves every handler path in an app's hooks.py against the bench env — catches silent typos before runtime |
| `skills/frappe-dev/scripts/validate_doctype_json.py` | Validates DocType JSON (fieldnames, fieldtypes, options, flag conflicts, permissions) before `bench migrate` — `/frappe-new-doctype` refuses to migrate until it passes |

## Compatibility

Targets **Frappe v15+** / ERPNext v15+. Version-specific behavior is flagged inline (e.g. v14 `frm.set_value` promise behavior, v16 test-class renames).

Works in **Claude Code** (plugin marketplace), and the skills load in **Cursor** and **Codex** via their plugin manifests (`.cursor-plugin/`, `.codex-plugin/`).

## Roadmap

- `frappe-bench-init` command — generate a high-quality `CLAUDE.md`/`AGENTS.md` for any bench
- Hooks: auto-run ruff/eslint on edit, guard `sites/` from accidental edits
- An agentic-coding benchmark for Frappe tasks

## Contributing

PRs welcome — especially gotchas with reproduction notes. Keep skills generic: framework principles and workflows, no project-specific facts.

## License

MIT © [Prilk Consulting](https://prilk.com)
