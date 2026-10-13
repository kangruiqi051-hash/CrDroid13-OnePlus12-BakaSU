#!/usr/bin/env bash
set -euo pipefail
ROOT=$(pwd)
export PATH="$ROOT/work/clang/bin:$PATH"
export ARCH=arm64 SUBARCH=arm64 LLVM=1 LLVM_IAS=1
export CC=clang CXX=clang++ HOSTCC=clang HOSTCXX=clang++ LD=ld.lld
export AR=llvm-ar NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump STRIP=llvm-strip
case "$VARIANT" in Stock|BakaSU|BakaSU-SUSFS) ;; *) echo 'Invalid variant'; exit 1;; esac
cd work/kernel
python3 - <<'PY'
from pathlib import Path
import re

path = Path("certs/extract-cert.c")
text = path.read_text()
guard = r"(?:#ifdef\s+USE_PKCS11_ENGINE|#if\s+defined\s*\(\s*USE_PKCS11_ENGINE\s*\))"
declaration = re.compile(
    rf"(?m)^(?P<indent>[ \t]*){guard}[ \t]*\r?\n"
    r"(?P<body>[ \t]*)static\s+const\s+char\s+\*\s*key_pass\s*;[ \t]*\r?\n"
    r"(?P=indent)#endif[ \t]*(?:\r?\n|$)"
)
assignment = re.compile(
    rf"(?m)^(?P<indent>[ \t]*){guard}[ \t]*\r?\n"
    r"(?P<body>[ \t]*)key_pass\s*=\s*getenv\s*\(\s*"
    r"\"KBUILD_SIGN_PIN\"\s*\)\s*;[ \t]*\r?\n"
    r"(?P=indent)#endif[ \t]*(?:\r?\n|$)"
)

text, declaration_count = declaration.subn(
    lambda match: f"{match.group('body')}static const char *key_pass;\n",
    text,
    count=1,
)
text, assignment_count = assignment.subn(
    lambda match: f'{match.group("body")}key_pass = getenv("KBUILD_SIGN_PIN");\n',
    text,
    count=1,
)

if declaration_count or assignment_count:
    path.write_text(text)
    print("Fixed extract-cert.c key_pass guards")
else:
    print("extract-cert.c key_pass layout is already compatible")
PY
if [[ "$VARIANT" != Stock ]]; then
  ln -s ../../bakasu/kernel drivers/kernelsu
  printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> drivers/Makefile
  printf '\nsource "drivers/kernelsu/Kconfig"\n' >> drivers/Kconfig
fi
if [[ "$VARIANT" == BakaSU-SUSFS ]]; then
  cp ../susfs/kernel_patches/fs/* fs/
  cp ../susfs/kernel_patches/include/linux/* include/linux/
  git apply --check "$ROOT/patches/50-susfs-crdroid17.patch"
  git apply "$ROOT/patches/50-susfs-crdroid17.patch"
fi
make O=out gki_defconfig vendor/pineapple_GKI.config vendor/oplus/pineapple_GKI.config
if [[ "$VARIANT" != Stock ]]; then
  scripts/config --file out/.config --enable KSU --disable MODULE_SIG_PROTECT
  if [[ "$VARIANT" == BakaSU-SUSFS ]]; then
    scripts/config --file out/.config --enable KSU_SUSFS --disable KSU_TRACEPOINT_HOOK --disable KSU_MANUAL_HOOK
    for feature in SUS_PATH SUS_MOUNT SUS_KSTAT SPOOF_UNAME ENABLE_LOG HIDE_KSU_SUSFS_SYMBOLS SPOOF_CMDLINE_OR_BOOTCONFIG OPEN_REDIRECT SUS_MAP; do
      scripts/config --file out/.config --enable "KSU_SUSFS_$feature"
    done
  else
    scripts/config --file out/.config --enable KSU_TRACEPOINT_HOOK --disable KSU_SUSFS --disable KSU_MANUAL_HOOK
  fi
fi
make O=out olddefconfig
if [[ "$VARIANT" != Stock ]]; then grep -qx 'CONFIG_KSU=y' out/.config; fi
if [[ "$VARIANT" == BakaSU-SUSFS ]]; then grep -qx 'CONFIG_KSU_SUSFS=y' out/.config; fi
cp out/.config "$ROOT/artifacts/kernel.config"
make -j"$(nproc)" O=out Image
cp out/arch/arm64/boot/Image "$ROOT/artifacts/Image"
cp out/Module.symvers "$ROOT/artifacts/" 2>/dev/null || :
