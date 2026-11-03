"""Allow SUSFS priority-filter helpers to be unused when the feature is disabled."""
import hashlib
import json
from pathlib import Path
import re
import sys


def prepare(path):
    before = path.read_bytes()
    text = before.decode()
    annotated = []
    for name in ('susfs_switch_to_ksu_domain', 'susfs_restore_creds'):
        # Upstream compiles these definitions unconditionally, while their callers
        # require CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER (not present in all KSU forks).
        pattern = rf'(?m)^static (?!__maybe_unused)([^\n;{{]*\b{re.escape(name)}\([^\n]*\)\s*\{{)'
        text, count = re.subn(pattern, r'static __maybe_unused \1', text)
        if count > 1:
            raise RuntimeError(f'Unexpected duplicate SUSFS helper: {name}')
        if count:
            annotated.append(name)
    after = text.encode()
    path.write_bytes(after)
    return {'fix': 'optional-priority-filter-helpers', 'annotated': annotated,
            'original_sha256': hashlib.sha256(before).hexdigest(),
            'prepared_sha256': hashlib.sha256(after).hexdigest()}


if __name__ == '__main__':
    result = prepare(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + '\n')
    print('SUSFS optional helper compatibility:', ', '.join(result['annotated']) or 'already compatible')
