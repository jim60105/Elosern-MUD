"""Throwaway per-file lint helper for the P07 migration (deleted before commit)."""
import json
import sys

from tools import test_data_lint

u = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
out = {}
for rel in sys.argv[1:]:
    out[rel] = [
        {"kind": f.kind, "line": f.line, "detail": f.detail}
        for f in test_data_lint.scan_file(test_data_lint.REPO_ROOT, rel, u)
    ]
print(json.dumps(out, ensure_ascii=False, indent=1))
