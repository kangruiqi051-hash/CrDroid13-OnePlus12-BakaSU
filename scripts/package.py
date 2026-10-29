from pathlib import Path
import hashlib,json,os,subprocess,zipfile
from datetime import datetime
from zoneinfo import ZoneInfo
build_date=datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
root=Path.cwd();ak=root/'work/anykernel';out=root/'artifacts'
image=out/'Image';assert image.stat().st_size>0
script=(ak/'anykernel.sh').read_text()
script=script.replace('do.devicecheck=0','do.devicecheck=1').replace('device.name1=','device.name1=waffle').replace('device.name2=','device.name2=OP5929L1').replace('device.name3=','device.name3=OP595DL1')
script=script.replace('kernel.string=AnyKernel3 by KernelSU Developers | Build by cctv18','kernel.string=crDroid 13 waffle '+os.environ['VARIANT'])
(ak/'anykernel.sh').write_text(script)
(ak/'Image').write_bytes(image.read_bytes())
info={'build_date':build_date,'variant':os.environ['VARIANT'],'device':'waffle','rom':'crDroid 13 Android 17','run':os.getenv('GITHUB_RUN_ID'),'sources':json.loads((out/'sources.lock.json').read_text()),'features':json.loads((out/'features.json').read_text()),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'toolchain_archive_sha256':(out/'toolchain.sha256').read_text().split()[0],'validation':'Compilation only; device boot and vendor module compatibility not verified.'}
(out/'build-info.json').write_text(json.dumps(info,indent=2)+'\n')
(ak/'build-info.json').write_bytes((out/'build-info.json').read_bytes())
name=f"waffle-crDroid13-{os.environ['VARIANT']}-{build_date}.zip"
with zipfile.ZipFile(out/name,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(ak.rglob('*')):
  rel=f.relative_to(ak)
  if f.is_file() and not any(part.startswith('.git') for part in rel.parts):
   z.write(f,rel.as_posix())
print('Packaged',name)
