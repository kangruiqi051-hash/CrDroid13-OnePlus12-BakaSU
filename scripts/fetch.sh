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
# crDroid tracks external driver symlinks using its original sibling names.
# Resolve by the explicit upstream marker, rather than relying on directory depth.
import os
kernel=Path('work/kernel').resolve()
roots={'sm8650-modules':Path('work/modules').resolve(),
       'sm8650-devicetrees':Path('work/devicetrees').resolve()}
fixed=0
for link in kernel.rglob('*'):
    if not link.is_symlink():
        continue
    old=os.readlink(link)
    for marker,base in roots.items():
        parts=Path(old).parts
        if marker not in parts:
            continue
        suffix=parts[parts.index(marker)+1:]
        target=base.joinpath(*suffix)
        if not target.exists():
            # The pinned upstream carries this dangling, unreferenced legacy link.
            # It is NOT the charger driver (drivers/power/oplus), which is required.
            if link.relative_to(kernel).as_posix() == 'drivers/soc/oplus/power':
                referenced = subprocess.run(
                    ['git','-C',str(kernel),'grep','-q','-F','oplus/power/',
                     'HEAD','--','*Makefile*','*Kconfig*','*.c','*.h']).returncode
                if referenced == 1:
                    print('Unused upstream legacy link: drivers/soc/oplus/power; left unchanged')
                    continue
                if referenced != 0:
                    raise RuntimeError('Could not verify legacy power link references')
            raise RuntimeError(f'Missing vendor dependency: {link} -> {target}')
        link.unlink()
        link.symlink_to(os.path.relpath(target,link.parent))
        print(f'Vendor link: {link.relative_to(kernel)} -> {target}')
        fixed+=1
        break
assert fixed>0, 'Expected crDroid external vendor links were not found'
assert (kernel/'drivers/base/kernelFwUpdate/Kconfig').is_file()
print(f'Validated {fixed} vendor source symlinks')

Path('artifacts/sources.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
PYFETCH
# Floran's Android 17 toolchain; record the archive hash with each build.
url=https://github.com/AkiHaza/Floran-Kernel/releases/download/toolchain-r596125/linux-x86-refs_heads_android17-release-clang-r596125.tar.gz
mkdir -p work/clang
curl -fL --retry 3 "$url" -o work/clang.tar.gz
sha256sum work/clang.tar.gz > artifacts/toolchain.sha256
tar -xf work/clang.tar.gz -C work/clang
cp sources.lock.json artifacts/
