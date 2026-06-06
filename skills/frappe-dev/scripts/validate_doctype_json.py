#!/usr/bin/env python3
"""Validate a DocType JSON definition before bench migrate sees it.

Standalone (no frappe import) — checks structure, fieldnames, fieldtypes,
option requirements, and flag conflicts that otherwise surface as cryptic
errors mid-migrate or, worse, silently produce a broken form.

Usage:
    python3 validate_doctype_json.py <path/to/my_doctype.json>

Exit codes: 0 = valid (warnings allowed), 1 = bad input, 4 = errors found.
"""

import json
import re
import sys
from pathlib import Path

VALID_FIELDTYPES = {
	"Attach", "Attach Image", "Autocomplete", "Barcode", "Button", "Check",
	"Code", "Color", "Column Break", "Currency", "Data", "Date", "Datetime",
	"Duration", "Dynamic Link", "Float", "Fold", "Geolocation", "Heading",
	"HTML", "HTML Editor", "Icon", "Image", "Int", "JSON", "Link",
	"Long Text", "Markdown Editor", "Password", "Percent", "Phone",
	"Read Only", "Rating", "Section Break", "Select", "Signature",
	"Small Text", "Tab Break", "Table", "Table MultiSelect", "Text",
	"Text Editor", "Time",
}

RESERVED_FIELDNAMES = {
	"name", "owner", "creation", "modified", "modified_by", "docstatus",
	"idx", "parent", "parentfield", "parenttype", "doctype",
}

LAYOUT_TYPES = {"Section Break", "Column Break", "Tab Break", "Fold", "Heading"}
OPTIONS_REQUIRED = {"Link", "Table", "Table MultiSelect", "Dynamic Link"}
FIELDNAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def main() -> int:
	if len(sys.argv) != 2:
		print(__doc__)
		return 1
	path = Path(sys.argv[1])
	if not path.is_file():
		print(f"error: no such file: {path}")
		return 1

	try:
		doc = json.loads(path.read_text())
	except json.JSONDecodeError as e:
		print(f"ERROR invalid JSON: {e}")
		return 4

	errors, warnings = [], []
	err, warn = errors.append, warnings.append

	if not isinstance(doc, dict) or doc.get("doctype") != "DocType":
		err('root must be an object with "doctype": "DocType"')
		report(errors, warnings)
		return 4

	# --- identity ---
	name = doc.get("name")
	if not name:
		err('missing "name"')
	if not doc.get("module"):
		err('missing "module"')
	if name and path.parent.name not in ("", "."):
		scrubbed = name.lower().replace(" ", "_").replace("-", "_")
		if path.parent.name != scrubbed and path.stem == path.parent.name:
			warn(f'folder {path.parent.name!r} != scrubbed name {scrubbed!r}')

	# --- flags ---
	istable = bool(doc.get("istable"))
	issingle = bool(doc.get("issingle"))
	if istable and doc.get("is_submittable"):
		err("istable and is_submittable are mutually exclusive")
	if istable and issingle:
		err("istable and issingle are mutually exclusive")
	if doc.get("is_tree") and not any(
		f.get("fieldname") == f"parent_{name.lower().replace(' ', '_')}"
		for f in doc.get("fields", []) if isinstance(f, dict)
	) and not doc.get("nsm_parent_field"):
		warn("is_tree without a recognizable parent field or nsm_parent_field")
	if "engine" not in doc:
		warn('no "engine" — add "engine": "InnoDB"')

	# --- fields ---
	fields = doc.get("fields")
	if not isinstance(fields, list) or not fields:
		err('"fields" must be a non-empty list')
		fields = []

	seen = set()
	fieldnames = set()
	for i, f in enumerate(fields):
		if not isinstance(f, dict):
			err(f"fields[{i}] is not an object")
			continue
		fn = f.get("fieldname")
		ft = f.get("fieldtype")
		where = f"fields[{i}] ({fn or '?'})"

		if not fn:
			err(f"{where}: missing fieldname")
		else:
			fieldnames.add(fn)
			if not FIELDNAME_RE.match(fn):
				err(f"{where}: fieldname must be snake_case starting with a letter")
			if fn in RESERVED_FIELDNAMES:
				err(f"{where}: {fn!r} is a reserved fieldname")
			if fn in seen:
				err(f"{where}: duplicate fieldname")
			seen.add(fn)

		if not ft:
			err(f"{where}: missing fieldtype")
		elif ft not in VALID_FIELDTYPES:
			err(f"{where}: unknown fieldtype {ft!r}")
		else:
			if ft in OPTIONS_REQUIRED and not f.get("options"):
				err(f"{where}: fieldtype {ft} requires options")
			if ft == "Select" and not f.get("options"):
				warn(f"{where}: Select without options")
			if ft not in LAYOUT_TYPES and not f.get("label"):
				warn(f"{where}: data field without label")
			if ft == "Currency" and not f.get("options"):
				warn(f"{where}: Currency without options (currency-link field) uses company default")

	# --- field_order consistency ---
	order = doc.get("field_order")
	if isinstance(order, list):
		missing = [fn for fn in order if fn not in fieldnames]
		extra = [fn for fn in fieldnames if fn not in order]
		if missing:
			err(f"field_order references undefined fields: {missing}")
		if extra:
			err(f"fields missing from field_order: {extra}")

	# --- autoname ---
	autoname = doc.get("autoname") or ""
	if autoname.startswith("field:") and autoname[6:] not in fieldnames:
		err(f"autoname {autoname!r} references a field that doesn't exist")
	if autoname.startswith("format:") and "{" not in autoname and "#" not in autoname:
		warn(f"autoname {autoname!r} has no series (#) or field ({{}}) component")
	if autoname == "naming_series" and "naming_series" not in fieldnames:
		warn('autoname "naming_series" but no naming_series field defined')

	# --- permissions ---
	perms = doc.get("permissions")
	if istable:
		if perms:
			warn("child table with a permissions block (parent's permissions apply)")
	elif not perms:
		err("non-child DocType without permissions — nobody can access it")
	else:
		for i, p in enumerate(perms):
			if not p.get("role"):
				err(f"permissions[{i}]: missing role")
		if doc.get("is_submittable") and not any(p.get("cancel") for p in perms):
			warn("is_submittable but no role can cancel")

	# --- child table list view ---
	if istable and not any(f.get("in_list_view") for f in fields if isinstance(f, dict)):
		warn("child table with no in_list_view columns — grid shows nothing")

	if not doc.get("sort_field"):
		warn('no sort_field — add "sort_field": "creation" (v15+ default)')

	report(errors, warnings)
	return 4 if errors else 0


def report(errors, warnings):
	for e in errors:
		print(f"ERROR {e}")
	for w in warnings:
		print(f"WARN  {w}")
	print(f"\n{len(errors)} errors, {len(warnings)} warnings")


if __name__ == "__main__":
	sys.exit(main())
