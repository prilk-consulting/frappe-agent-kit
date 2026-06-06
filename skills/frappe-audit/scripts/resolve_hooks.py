#!/usr/bin/env python3
"""Resolve every dotted-path handler registered in an app's hooks.py.

Hook path typos fail silently or at runtime, never at import. This script
imports the app's hooks module, collects every handler path from the
code-bearing hook keys, and tries to resolve each one to a real callable.

Run with the BENCH's Python so app modules are importable:

    cd <bench> && ./env/bin/python /path/to/resolve_hooks.py <app_name>

Exit codes: 0 = all resolve, 1 = bad input, 3 = broken hooks found.
"""

import importlib
import sys

# Hook keys whose values are dotted paths to Python callables/classes.
# Asset hooks (doctype_js, app_include_*, web_include_*) hold file paths — excluded.
CODE_HOOKS = [
	"doc_events",
	"scheduler_events",
	"override_whitelisted_methods",
	"override_doctype_class",
	"override_doctype_dashboards",
	"permission_query_conditions",
	"has_permission",
	"has_website_permission",
	"before_install",
	"after_install",
	"before_uninstall",
	"after_uninstall",
	"before_migrate",
	"after_migrate",
	"after_sync",
	"before_tests",
	"boot_session",
	"extend_bootinfo",
	"update_website_context",
	"on_session_creation",
	"on_logout",
	"auth_hooks",
	"get_translated_dict",
	"jinja",
]


def collect_paths(value, found):
	"""Recursively collect dotted-path strings from hook values."""
	if isinstance(value, str):
		if "." in value and " " not in value and "/" not in value:
			found.append(value)
	elif isinstance(value, (list, tuple)):
		for v in value:
			collect_paths(v, found)
	elif isinstance(value, dict):
		for v in value.values():
			collect_paths(v, found)


def resolve(path):
	"""Mirror frappe.get_attr: import the module part, getattr the rest."""
	module_path, _, attr = path.rpartition(".")
	if not module_path:
		return False, "not a dotted path"
	try:
		module = importlib.import_module(module_path)
	except ImportError as e:
		return False, f"module import failed: {e}"
	if not hasattr(module, attr):
		return False, f"module {module_path!r} has no attribute {attr!r}"
	return True, ""


def main() -> int:
	if len(sys.argv) != 2:
		print(__doc__)
		return 1
	app = sys.argv[1]

	try:
		hooks = importlib.import_module(f"{app}.hooks")
	except ImportError as e:
		print(f"error: cannot import {app}.hooks — run with the bench's env python "
			f"from the bench root ({e})")
		return 1

	paths = []
	for key in CODE_HOOKS:
		collect_paths(getattr(hooks, key, None), paths)

	if not paths:
		print(f"{app}: no code hooks registered")
		return 0

	broken = []
	for p in sorted(set(paths)):
		ok, reason = resolve(p)
		status = "OK    " if ok else "BROKEN"
		print(f"{status} {p}" + (f"  ← {reason}" if reason else ""))
		if not ok:
			broken.append(p)

	print(f"\n{app}: {len(set(paths))} hook paths, {len(broken)} broken")
	return 3 if broken else 0


if __name__ == "__main__":
	sys.exit(main())
