---
name: frappe-fixtures
description: Frappe fixtures, workspaces, and sidebar setup. Use for exporting/syncing fixtures, Workspace + Workspace Sidebar + Desktop Icon configuration, nested-set fixture ordering, and per-environment ID pitfalls that break fresh-site migrations.
---

# Fixtures, Workspaces & Sidebars

## Usage

Use this skill when:

- Exporting or syncing fixtures (`bench export-fixtures`, hooks `fixtures` list)
- Setting up a Workspace, Workspace Sidebar, or Desktop Icon for an app
- Debugging fresh-site `bench migrate` crashes caused by fixture ordering or per-environment links
- Deciding between fixtures and install.py for custom fields

## Fixture basics

```python
# hooks.py
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "My Module"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "My Module"]]},
    {"dt": "Role", "filters": [["name", "in", ["My Role"]]]},
]
```

```bash
bench --site <site> export-fixtures --app myapp     # DB → apps/myapp/myapp/fixtures/*.json
bench --site <site> migrate                          # JSON → DB (runs sync_fixtures)
bench --site <site> execute frappe.utils.fixtures.sync_fixtures --args "['myapp']"  # sync only
```

- **Always filter** — an unfiltered `{"dt": "Custom Field"}` exports every custom field on the site, including other apps'. Each app owns only its own records.
- Use `or_filters` when records can't be matched by one field: `{"dt": "Wiki Document", "or_filters": [...]}`.
- Fixture sync is **upsert-only**: deleting a record from the JSON does not delete it from sites that already have it. Removals need a patch.
- Re-export after every UI-side change, and **diff the export before committing** — `export-fixtures` rewrites whole files and happily captures unrelated records that match your filter.
- For content managed live in the UI by end users (website pages, wiki content), consider NOT shipping fixtures at all — a fixture sync on deploy will overwrite their edits. Fixtures fit configuration, not user-owned content.

## Workspace + Sidebar + Desktop Icon

### CRITICAL naming rule

- Workspace Sidebar **`name`** MUST differ from the module name
- Workspace Sidebar **`module`** field MUST equal the module name (this prevents auto-gen)
- Example: module="Logistics" → sidebar `name`="Logistics Hub", sidebar `module`="Logistics"

If `name` matches `module`, Frappe's `auto_generate_sidebar_from_module()` creates a cached auto-generated sidebar (top 3 DocTypes only) that overrides yours.

```python
# hooks.py
fixtures = [
    {"dt": "Workspace", "filters": [["name", "in", ["MyWorkspace"]]]},
    {"dt": "Workspace Sidebar", "filters": [["name", "in", ["My Sidebar"]]]},
    {"dt": "Desktop Icon", "filters": [["name", "in", ["My Sidebar"]]]},
]
```

```jsonc
// fixtures/workspace_sidebar.json (minimal)
[{
  "doctype": "Workspace Sidebar", "name": "My Sidebar", "module": "MyModule",
  "title": "My Sidebar", "header_icon": "bot-message-square", "standard": 1,
  "items": [
    {"label": "Home", "link_to": "MyWorkspace", "link_type": "Workspace", "type": "Link"},
    {"label": "My DocType", "link_to": "My DocType", "link_type": "DocType", "type": "Link", "icon": "list"}
  ]
}]
```

- Desktop Icon `link_to` and `sidebar` reference the sidebar name.
- Icon SVG: 118x118px, colored background + white icon, in `public/images/`.
- Sidebar item icons: pick from `frappe/public/icons/lucide/icons.svg`.
- After syncing: `bench --site <site> clear-cache` (sidebars are cached).

## Nested-set fixture ordering gotcha

`bench export-fixtures` writes records sorted **alphabetically by `name`**. For nested-set doctypes (tree doctypes: Item Group, Customer Group, Account, Wiki Document, BOM trees, …) this can put children before their parents in the JSON — random hash names sort unpredictably.

On a **fresh site**, `bench migrate` hits the child row first, calls `update_add_node`, looks up the parent's `lft`/`rgt` — and the parent doesn't exist yet:

```
File ".../frappe/utils/nestedset.py", line 77, in update_add_node
    left, right = frappe.db.get_value(doctype, {"name": parent}, ["lft", "rgt"], for_update=True)
TypeError: cannot unpack non-iterable NoneType object
```

**Fix**: topologically re-sort the JSON after every export so each record appears only after its parent.

```python
import json
from pathlib import Path

path = Path("apps/<app>/<app>/fixtures/<doctype_singular>.json")
PARENT_FIELD = "parent_<doctype_singular>"  # the link-to-parent field on your tree doctype

docs = json.loads(path.read_text())
by_name = {d["name"]: d for d in docs}
depth_cache: dict[str, int] = {}

def depth_of(name: str) -> int:
    if name in depth_cache:
        return depth_cache[name]
    d = by_name.get(name)
    parent = d.get(PARENT_FIELD) if d else None
    depth_cache[name] = (depth_of(parent) + 1) if parent else 0
    return depth_cache[name]

for d in docs:
    depth_of(d["name"])
docs.sort(key=lambda d: depth_cache[d["name"]])
path.write_text(json.dumps(docs, indent=1, ensure_ascii=False) + "\n")
```

Run this as a post-export step (or wrap `bench export-fixtures` in a script that does both). Fixture order is **per-file**; fixture files import alphabetically by filename, so make sure parent-doctype fixtures sort before child-doctype fixtures if they're linked.

This gotcha never shows on the dev site where the records already exist — only on fresh installs / first `bench migrate` of a downstream bench. Test fixtures on a throwaway site before shipping.

## Per-environment ID gotcha

Fixtures that contain **links to records that are generated per-environment** (revision IDs, version rows, file attachments, auto-named children that aren't themselves exported) will migrate fine on the source site and crash on every other site with `LinkValidationError: Could not find <DocType>`.

Before committing an export, null out or strip any field whose value is an autoname/hash that the fixture set itself does not include. Typical offenders: "current revision" pointers, "latest version" links, cached file URLs pointing at `/private/files/`.

```python
# post-export scrub example
for d in docs:
    d["main_revision"] = None   # per-environment pointer; rebuilt on first save
```

## Custom fields: fixtures vs install.py

Two valid approaches — pick ONE per app, don't mix:

| Approach | Pro | Con |
|----------|-----|-----|
| `install.py` + `create_custom_fields()` in `after_install`/`after_migrate` | Code-reviewed dicts, no export step, idempotent | Fields not visible in fixture diffs |
| `fixtures = [{"dt": "Custom Field", "filters": [["module", "=", "X"]]}]` | UI-first workflow | Export captures noise; needs module set on every field |

The install.py approach is generally preferred for apps that extend other apps' DocTypes — see the frappe-dev skill.
