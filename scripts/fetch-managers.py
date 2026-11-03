"""Fetch the official normal manager APK built from the kernel's exact BakaSU commit."""
import hashlib
import io
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.request
import zipfile

out = Path('artifacts')
config = json.loads(Path('manager-ci.json').read_text())
sources = json.loads((out / 'sources.lock.json').read_text())
commit = sources['bakasu']['commit']
version = sources['bakasu']['version_code']
base = 'https://api.github.com/repos/' + config['repository']
headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'waffle-kernel-builder',
           'Authorization': 'Bearer ' + os.environ['GH_TOKEN']}


def api(path):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(base + path, headers=headers), timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except OSError:
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


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


# Resolve only successful main push builds of this exact driver commit.
# Do not substitute an older driver or an APK built from another commit.
runs = api('/actions/workflows/' + config['workflow'] + '/runs?branch=' +
           config['branch'] + '&event=push&status=success&head_sha=' + commit + '&per_page=100')['workflow_runs']
run = None
artifacts = []
for candidate in runs:
    if (candidate['head_sha'] != commit or candidate['head_branch'] != config['branch']
            or candidate['event'] != 'push' or candidate['conclusion'] != 'success'
            or candidate['path'] != '.github/workflows/' + config['workflow']):
        continue
    found = []
    page = 1
    while True:
        batch = api(f"/actions/runs/{candidate['id']}/artifacts?per_page=100&page={page}")['artifacts']
        found.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    if len([a for a in found if a['name'] == config['artifact'] and not a['expired']]) == 1:
        run, artifacts = candidate, found
        break
if run is None:
    raise RuntimeError(f'No successful official {config["workflow"]} with an available '
                       f'{config["artifact"]} for BakaSU {commit}. '
                       'Wait for upstream CI to finish, then run this workflow again.')
print('Resolved matching official manager CI:', run['html_url'], flush=True)
manifest = {'commit': commit, 'driver_version_code': version, 'upstream_run': run['html_url'], 'apks': []}
# Upstream no longer builds a Spoofed manager. Require only the normal release.
for kind in (config['artifact'],):
    matches = [a for a in artifacts if a['name'] == kind and not a['expired']]
    assert len(matches) == 1, f'Missing official artifact: {kind}; retry after upstream publishes the matching artifact'
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
