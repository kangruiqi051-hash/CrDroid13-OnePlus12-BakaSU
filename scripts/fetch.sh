#!/usr/bin/env bash
set -euo pipefail
mkdir -p work artifacts
python3 - <<'PYFETCH'
import json,subprocess
from pathlib import Path
lock=json.loads(Path('sources.lock.json').read_text())
import os
features={name:os.environ.get('USE_'+name.upper(),'false').lower() == 'true'
          for name in json.loads(Path('feature-configs.json').read_text())}
pins=json.loads(Path('features.lock.json').read_text())
needed=set()
if any(features[n] for n in ('net','ntsync','unicode','perf')): needed.add('wild_patches')
for name,flag in [('nomount','nomount'),('bbg','bbg'),('droidspaces','ds')]:
    if features[flag]: needed.add(name)
for name in sorted(needed): lock[name]=pins[name]
Path('artifacts/features.json').write_text(json.dumps({'requested':features,
    'reference':pins['wild_features'],'status':{},'patches':[]},indent=2)+'\n')

# Resolve branch tips once per run, then fetch immutable commits.
for name,s in lock.items():
    if s.get('tracking') == 'branch':
        ref='refs/heads/'+s['branch']
        rows=subprocess.check_output(['git','ls-remote','--exit-code',s['url'],ref],text=True).splitlines()
        matches=[row.split()[0] for row in rows if row.split()[1] == ref]
        if len(matches) != 1:
            raise RuntimeError(f'Cannot resolve upstream branch: {name} {ref}')
        s['commit']=matches[0]
        print(f'Resolved {name}: {ref} -> {s["commit"]}',flush=True)
Path('artifacts/sources.lock.json').write_text(json.dumps(lock,indent=2)+'\n')
for name,s in lock.items():
    path=Path('work')/name
    subprocess.run(['git','init',str(path)],check=True)
    subprocess.run(['git','-C',str(path),'remote','add','origin',s['url']],check=True)
    fetch=['git','-C',str(path),'fetch']
    # BakaSU derives its driver version from the full commit count and tags.
    fetch += ['--tags'] if name == 'bakasu' else ['--depth=1']
    subprocess.run(fetch+['origin',s['commit']],check=True)
    subprocess.run(['git','-C',str(path),'checkout','--detach','FETCH_HEAD'],check=True)
    actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    assert actual==s['commit'],(name,actual)
    if name == 'bakasu':
        count=int(subprocess.check_output(['git','-C',str(path),'rev-list','--count','HEAD'],text=True))
        s['version_code']=30700+count
        print(f'BakaSU driver version: {s["version_code"]}',flush=True)
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
cp sources.lock.json artifacts/sources.requested.json
