---
description: Scaffold a new DocType (JSON + controller + client script + test) following Frappe conventions
argument-hint: "<DocType Name> in <app> [submittable|child|single|tree]"
---

Scaffold a new DocType named from `$ARGUMENTS` in the specified app. If the app or module is ambiguous, list the app's modules from `modules.txt` and ask.

## Steps

1. **Resolve target**: `apps/<app>/<app>/<module>/doctype/<scrubbed_name>/` where `scrubbed_name` is the lowercase snake_case DocType name. The directory gets an empty `__init__.py`.

2. **Study a sibling first**: open an existing DocType JSON in the same module (or in `apps/frappe/frappe/core/doctype/` if none) and match its structure exactly — key order, `engine: "InnoDB"`, `modified`/`creation` timestamps, `sort_field: "creation"` (v15+; older apps use `modified`), `sort_order: "DESC"`.

3. **Design before writing** — confirm with the user if not derivable from the request:
   - **Naming**: `naming_series` for transactional docs (`format:PREFIX-.YYYY.-.#####`), `field:` for natural keys, hash (omit autoname) for child tables. Hash-named user-facing doctypes need a title field + `show_title_field_in_link`.
   - **Flags**: `is_submittable` (transactions), `istable` (child), `issingle` (settings), `is_tree` (hierarchies). Default `track_changes: 1` for business data.
   - **Fields**: prefer Link over free Data, Select only for closed enums, Check over yes/no Data, Currency with `options: "currency_field"` for money. Child tables need `in_list_view: 1` on key columns.
   - **Permissions**: map roles to existing ones (System Manager, ERPNext's Customer/Supplier/etc.) — do NOT invent new roles unless genuinely new. Include the permission matrix in the JSON.

4. **Write the files**:
   - `<scrubbed_name>.json` — full DocType definition
   - `<scrubbed_name>.py` — controller extending `Document`, with typed docstring stub and only the lifecycle hooks that have actual logic (no empty boilerplate methods)
   - `<scrubbed_name>.js` — only if there's client behavior; otherwise skip
   - `test_<scrubbed_name>.py` — test class with at least one real assertion (validation rule or default), not an empty placeholder

5. **Validate BEFORE migrating** (do not skip): run the validator bundled with this plugin's frappe-dev skill:

   ```bash
   python3 <plugin>/skills/frappe-dev/scripts/validate_doctype_json.py <path/to/doctype.json>
   ```

   Fix every ERROR and re-run until exit 0 (max 3 attempts; if still failing, show the user the remaining errors and stop). Treat WARNs as review prompts — fix or consciously dismiss each one. Never run `bench migrate` on a JSON the validator rejects.

6. **Apply**: run `bench --site <site> migrate` (ask which site if several; check `sites/common_site_config.json` `default_site` first). Confirm the table exists: `bench --site <site> execute frappe.db.table_exists --args "['<DocType Name>']"`.

7. **Verify**: open `/app/<scrubbed-name-with-dashes>/new` mentally — walk the field layout once for section/column breaks so the form isn't one endless column. Add `Section Break`/`Column Break` fields where natural groups exist.

## Rules

- Server-side validation in `validate()` for every business rule — client scripts are hints only.
- New DocTypes in an existing app: check `developer_mode` is enabled on the site, else the JSON won't sync from files.
- Don't add a workspace/sidebar entry unless asked.
