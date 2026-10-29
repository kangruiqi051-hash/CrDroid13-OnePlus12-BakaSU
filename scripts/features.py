"""Optional WildKernels features adapted to crDroid's android14-6.1 tree.

Sources are fetched by fetch.sh at recorded commits. Patch conflicts and dropped
Kconfig requests are fatal; no fuzzy application or discarded rejects.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / 'work/kernel'
OUT = ROOT / 'artifacts'
STATE = OUT / 'features.json'
GROUPS = json.loads((ROOT / 'feature-configs.json').read_text())


def run(*args):
    subprocess.run(args, cwd=KERNEL, check=True)


def patch(source, state, transform=None):
    upstream = source
    adapted = ROOT / "patches/features" / source.name
    if adapted.exists():
        source = adapted
    data = source.read_bytes()
    if transform:
        data = transform(data.decode()).encode()
    applied = OUT / 'feature-patches' / source.name
    applied.parent.mkdir(exist_ok=True)
    applied.write_bytes(data)
    check = subprocess.run(['git', 'apply', '--check', str(applied)], cwd=KERNEL,
                           capture_output=True, text=True)
    if check.returncode == 0:
        run('git', 'apply', str(applied))
        result = 'applied'
    elif subprocess.run(['git', 'apply', '--reverse', '--check', str(applied)],
                        cwd=KERNEL, capture_output=True).returncode == 0:
        result = 'already-present'
    else:
        raise RuntimeError(f'Feature patch conflicts with current crDroid: {source}\n{check.stderr}')
    state['patches'].append({'name': source.name, 'sha256': hashlib.sha256(data).hexdigest(),
                             'result': result, 'adapted': source != upstream})
    STATE.write_text(json.dumps(state, indent=2) + '\n')


def integrate():
    state = json.loads(STATE.read_text())
    features = state['requested']
    version = (KERNEL / 'Makefile').read_text()
    if not re.search(r'^VERSION = 6$', version, re.M) or not re.search(r'^PATCHLEVEL = 1$', version, re.M):
        raise RuntimeError('These feature adaptations are audited only for kernel 6.1')
    common = ROOT / 'work/wild_patches/common'
    if features['nomount']:
        link = KERNEL / 'fs/nomount'
        link.symlink_to(os.path.relpath(ROOT / 'work/nomount/kernel/src', link.parent))
        with (KERNEL / 'fs/Makefile').open('a') as f:
            f.write('\nobj-$(CONFIG_NOMOUNT) += nomount/\n')
        with (KERNEL / 'fs/Kconfig').open('a') as f:
            f.write('\nsource "fs/nomount/Kconfig"\n')
    if features['bbg']:
        if '#define DEFINE_LSM(lsm)' not in (KERNEL / 'include/linux/lsm_hooks.h').read_text():
            raise RuntimeError('Baseband Guard requires the modern LSM infrastructure')
        link = KERNEL / 'security/baseband-guard'
        link.symlink_to(os.path.relpath(ROOT / 'work/bbg', link.parent))
        with (KERNEL / 'security/Makefile').open('a') as f:
            f.write('\nobj-$(CONFIG_BBG) += baseband-guard/\n')
        with (KERNEL / 'security/Kconfig').open('a') as f:
            f.write('\nsource "security/baseband-guard/Kconfig"\n')
    if features['net']:
        patch(common / 'bbrv3/0001-net-tcp-backport-BBRv3-to-android14-6.1.patch', state)
    if features['ds']:
        patch(ROOT / 'work/droidspaces/Documentation/resources/kernel-patches/GKI/below-kernel-6.12/001.GKI-below-6.12-fix_sysvipc_kabi_6_7_8.patch', state)
    if features['ntsync']:
        patch(common / 'ntsync/ntsync_compat_android14-6.1.patch', state)
        patch(common / 'ntsync/ntsync_base.patch', state)
    if features['unicode']:
        patch(common / 'unicode_bypass_fix_6.1+.patch', state)
    if features['perf']:
        names = ['optimized_mem_operations', 'file_struct_8bytes_align', 'reduce_cache_pressure',
                 'mem_opt_prefetch', 'optimise_memcmp', 'minimise_wakeup_time', 'int_sqrt',
                 'reduce_gc_thread_sleep_time', 'add_timeout_wakelocks_globally',
                 'f2fs_reduce_congestion', 'reduce_freeze_timeout']
        for name in names:
            patch(common / (name + '.patch'), state)
        patch(common / 'clear_page_16bytes_align.patch', state,
              lambda s: s.replace('SYM_FUNC_START_PI(clear_page)', 'SYM_FUNC_START_PI(__pi_clear_page)'))
        # Same prerequisite as WildKernels; retain all other code in this function.
        path = KERNEL / 'drivers/base/power/wakeup.c'
        text = path.read_text()
        text = re.sub(r'(void pm_system_wakeup\(void\)\s*\{)(.*?)(^\})',
                      lambda m: m[1] + re.sub(r'^.*suspend_abort_fs_sync\(\);.*\n', '', m[2], flags=re.M) + m[3],
                      text, flags=re.S | re.M)
        path.write_text(text)
        for name in ['avoid_extra_s2idle_wake_attempts', 'disable_cache_hot_buddy',
                     'f2fs_enlarge_min_fsync_blocks', 'increase_ext4_default_commit_age',
                     'increase_sk_mem_packets', 'reduce_pci_pme_wakeups',
                     'silence_irq_cpu_logspam', 'silence_system_logspam']:
            patch(common / (name + '.patch'), state)
    for name, enabled in features.items():
        state['status'][name] = 'requested' if enabled else 'not-requested'
    if features['ptrace']:
        state['status']['ptrace'] = 'not-applicable: upstream limits this fix to kernels below 5.16'
    STATE.write_text(json.dumps(state, indent=2) + '\n')


def requested_config(state):
    result = {}
    for name, selected in state['requested'].items():
        if selected:
            result.update(GROUPS[name])
    if state['requested']['bbg']:
        text = (KERNEL / 'out/.config').read_text()
        current = re.search(r'^CONFIG_LSM="(.*)"$', text, re.M)
        if not current:
            raise RuntimeError('Cannot preserve existing LSM order: CONFIG_LSM is missing')
        lsms = current[1].split(',')
        if 'baseband_guard' not in lsms:
            lsms.append('baseband_guard')
        result['CONFIG_LSM'] = '"' + ','.join(lsms) + '"'
    return result


def configure():
    state = json.loads(STATE.read_text())
    requested = requested_config(state)
    # BTF cannot coexist with these alternate debug-info choices.
    if state['requested']['bpf']:
        for symbol in ['DEBUG_INFO_NONE', 'DEBUG_INFO_REDUCED', 'DEBUG_INFO_SPLIT']:
            run('scripts/config', '--file', 'out/.config', '--disable', symbol)
    for key, value in requested.items():
        args = ['scripts/config', '--file', 'out/.config']
        if value in ('y', 'm', 'n'):
            args += [{'y': '--enable', 'm': '--module', 'n': '--disable'}[value], key[7:]]
        elif value.startswith('"'):
            args += ['--set-str', key[7:], value.strip('"')]
        else:
            args += ['--set-val', key[7:], value]
        run(*args)
    state['requested_config'] = requested
    STATE.write_text(json.dumps(state, indent=2) + '\n')


def verify():
    state = json.loads(STATE.read_text())
    actual = dict(re.findall(r'^(CONFIG_\w+)=(.+)$', (KERNEL / 'out/.config').read_text(), re.M))
    mismatches = {k: {'requested': v, 'actual': actual.get(k, 'n')}
                  for k, v in state['requested_config'].items() if actual.get(k, 'n') != v}
    state['config_mismatches'] = mismatches
    for name, status in state['status'].items():
        if status == 'requested':
            state['status'][name] = 'configured' if not mismatches else 'configuration-failed'
    STATE.write_text(json.dumps(state, indent=2) + '\n')
    if mismatches:
        raise RuntimeError('Kconfig dropped selected feature options: ' + json.dumps(mismatches))
    print('Selected feature configuration verified')


if __name__ == '__main__':
    {'integrate': integrate, 'configure': configure, 'verify': verify}[sys.argv[1]]()
