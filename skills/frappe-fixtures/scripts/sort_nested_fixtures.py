#!/usr/bin/env python3
"""Topologically sort a nested-set fixture file so parents precede children.

`bench export-fixtures` writes records alphabetically by name; for tree
doctypes a child can land before its parent, crashing fresh-site migrates
inside nestedset.update_add_node. Run this after every export.

Usage:
    python3 sort_nested_fixtures.py <fixture.json> <parent_fieldname>

Example:
    python3 sort_nested_fixtures.py apps/myapp/myapp/fixtures/item_group.json parent_item_group

Exit codes: 0 = sorted (or already sorted), 1 = bad input, 2 = cycle detected.
"""

import json
import sys
from pathlib import Path


def main() -> int:
	if len(sys.argv) != 3:
		print(__doc__)
		return 1

	path = Path(sys.argv[1])
	parent_field = sys.argv[2]

	if not path.is_file():
		print(f"error: no such file: {path}")
		return 1

	docs = json.loads(path.read_text())
	if not isinstance(docs, list):
		print("error: fixture root must be a JSON array")
		return 1

	by_name = {d.get("name"): d for d in docs}
	depth_cache: dict = {}

	def depth_of(name, trail=()):
		if name in depth_cache:
			return depth_cache[name]
		if name in trail:
			raise ValueError(f"cycle detected at {name!r}: {' -> '.join(trail)}")
		d = by_name.get(name)
		parent = d.get(parent_field) if d else None
		depth_cache[name] = (depth_of(parent, trail + (name,)) + 1) if parent else 0
		return depth_cache[name]

	try:
		for d in docs:
			depth_of(d.get("name"))
	except ValueError as e:
		print(f"error: {e}")
		return 2

	original = [d.get("name") for d in docs]
	docs.sort(key=lambda d: depth_cache[d.get("name")])
	if [d.get("name") for d in docs] == original:
		print(f"{path}: already in topological order ({len(docs)} records)")
		return 0

	path.write_text(json.dumps(docs, indent=1, ensure_ascii=False) + "\n")
	print(f"{path}: re-sorted {len(docs)} records by tree depth (max depth {max(depth_cache.values())})")
	return 0


if __name__ == "__main__":
	sys.exit(main())
