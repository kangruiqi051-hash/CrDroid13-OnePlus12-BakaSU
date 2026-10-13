#!/usr/bin/env bash
set -euo pipefail
mkdir -p work artifacts
python3 - <<'PYFETCH'
import json,subprocess
from pathlib import Path
lock=json.loads(Path('sources.lock.json').read_text())
for name,s in lock.items():
    path=Path('work')/name
    subprocess.run(['git','init',str(path)],check=True)
    subprocess.run(['git','-C',str(path),'remote','add','origin',s['url']],check=True)
    subprocess.run(['git','-C',str(path),'fetch','--depth=1','origin',s['commit']],check=True)
    subprocess.run(['git','-C',str(path),'checkout','--detach','FETCH_HEAD'],check=True)
    actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    assert actual==s['commit'],(name,actual)
Path('artifacts/sources.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
PYFETCH
# Floran's Android 17 toolchain; record the archive hash with each build.
url=https://github.com/AkiHaza/Floran-Kernel/releases/download/toolchain-r596125/linux-x86-refs_heads_android17-release-clang-r596125.tar.gz
mkdir -p work/clang
curl -fL --retry 3 "$url" -o work/clang.tar.gz
sha256sum work/clang.tar.gz > artifacts/toolchain.sha256
tar -xf work/clang.tar.gz -C work/clang
cp sources.lock.json artifacts/
