"""Publish official manager APKs built from the kernel's exact BakaSU commit."""
import hashlib
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
import zipfile

out = Path('artifacts')
config = json.loads(Path('manager-ci.json').read_text())
sources = json.loads((out / 'sources.lock.json').read_text())
commit = sources['bakasu']['commit']
assert config['commit'] == commit, 'Manager CI must match the driver commit'
version = config['driver_version_code']
assert sources['bakasu'].get('version_code', version) == version, 'Driver version count differs from official CI'
base = 'https://api.github.com/repos/' + config['repository']
headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'waffle-kernel-builder',
           'Authorization': 'Bearer ' + os.environ['GH_TOKEN']}


def api(path):
    with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=120) as response:
        return json.load(response)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def download(url):
    # Never forward the GitHub token to the signed object-storage URL.
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(urllib.request.Request(url, headers=headers), timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code != 302:
            raise
        target = error.headers['Location']
        if not target.startswith('https://'):
            raise RuntimeError('Unexpected artifact redirect')
    with urllib.request.urlopen(target, timeout=180) as response:
        return response.read()


run_id = config['run_id']
run = api(f'/actions/runs/{run_id}')
assert run['head_sha'] == commit and run['head_branch'] == 'main'
assert run['event'] == 'push' and run['conclusion'] == 'success'
assert run['path'] == '.github/workflows/build-manager.yml'
artifacts = []
page = 1
while True:
    batch = api(f'/actions/runs/{run_id}/artifacts?per_page=100&page={page}')['artifacts']
    artifacts.extend(batch)
    if len(batch) < 100:
        break
    page += 1
manifest = {'commit': commit, 'driver_version_code': version, 'upstream_run': run['html_url'], 'apks': []}
for kind in ('Manager-release', 'Spoofed-Manager-release'):
    matches = [a for a in artifacts if a['name'] == kind and not a['expired']]
    assert len(matches) == 1, f'Missing official artifact: {kind}; update manager-ci.json to a matching successful run'
    artifact = matches[0]
    cache = Path('work/manager-downloads')
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / f'{artifact["id"]}.zip'
    data = cached.read_bytes() if cached.exists() else download(artifact['archive_download_url'])
    cached.write_bytes(data)
    digest = artifact.get('digest')
    if digest:
        assert digest == 'sha256:' + hashlib.sha256(data).hexdigest(), 'Artifact checksum mismatch'
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        apks = [n for n in archive.namelist() if n.endswith('-arm64-v8a-release.apk') and f'_{version}-' in n]
        assert len(apks) == 1, f'Unexpected APK contents: {kind}: {apks}'
        apk = archive.read(apks[0])
    name = f'BakaSU-{kind}-{version}-arm64-v8a-{commit[:8]}.apk'
    (out / name).write_bytes(apk)
    manifest['apks'].append({'name': name, 'upstream_name': apks[0],
                             'artifact_id': artifact['id'], 'sha256': hashlib.sha256(apk).hexdigest()})
    print('Verified official manager:', name, flush=True)
(out / 'manager-info.json').write_text(json.dumps(manifest, indent=2) + '\n')
