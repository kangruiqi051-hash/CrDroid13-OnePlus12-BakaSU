# crDroid 13 / OnePlus 12 (waffle) Kernel Builder

为 OnePlus 12 的 crDroid 13 / Android 17 构建 Linux 6.1 内核。参考 [Floran-Kernel](https://github.com/kangruiqi051-hash/Floran-Kernel)，root 使用改名后的 BakaSU（原 ReSukiSU）。

## 使用

Actions → Build crDroid 13 OnePlus 12 Kernel → Run workflow。

- `BakaSU-SUSFS`：内置 root 和 SUSFS，默认选项。
- `BakaSU`：仅内置 root，使用 tracepoint hook。
- `Stock`：不集成 root/SUSFS 的源码对照构建；不是原 ROM 二进制的逐位复现。
- `create_release`：默认开启；成功产物会发布为 Release。

下载运行页面的 Artifacts。里面包含 AnyKernel3 ZIP、原始 Image、最终 kernel.config、构建日志和来源记录。失败时也上传日志，但不会生成可刷包。没有定时编译，手动触发。

## 来源和兼容性

每次运行都会解析 crDroid 内核、厂商模块和设备树 `17.0` 分支的最新提交，再按解析出的提交构建；BakaSU、SUSFS 和 AnyKernel3 继续固定在已选版本。仓库中的 sources.lock.json 定义跟踪策略，产物中的同名文件记录本次实际使用的全部提交，sources.requested.json 保留输入配置，AK3 中的 build-info.json 也记录实际提交。源码最新分支不保证与某个已发布 ROM 二进制完全对应，上游尚未公开的更新无法自动获取。内核、设备树和厂商模块的仓库均来自 crDroid 17.0 设备依赖。SUSFS 使用内核系列 `gki-android14-6.1`；它与用户空间的 Android 17 不是同一版本编号。

使用官方三个 defconfig 片段，参考 Floran 的 Android 17 Clang r596125，并记录工具链压缩包 SHA256。BakaSU 直接集成固定提交，不调用会追踪最新版的 setup.sh。

本工作流只编译和替换 boot 中的 Image，不刷 vendor_boot、dtbo、init_boot 或厂商模块。配套 modules/devicetrees 源码保留用于核对，不宣称重新构建了完整 ROM。必须使用匹配的 crDroid 厂商模块，编译成功不代表设备验证成功。振动、相机、Wi-Fi、recovery 必须实机验证。

切换到内置 root/SUSFS 前，准备当前 ROM 原版 boot/init_boot；移除旧 LKM root 修补，并停用原来的 SUSFS LKM 自动加载脚本，避免双重加载。不要通过重建不同内核分支来混搭原版模块。保留 fastboot 恢复镜像。

## 补丁维护

SUSFS 补丁冲突会失败停止，不使用 `patch || true` 或删除 rejects。遇到上游更新导致冲突时，需要手工审查兼容适配后再构建。默认不加入 LZ4、Docker、Droidspaces 或其他无关功能。

## 归属

参考工作流和 extract-cert 主机兼容修复来自 Floran-Kernel；内核和各补丁保留上游许可证。此仓库是构建脚本集合，不把上游代码改称自有源码。来源 URL 和提交见 sources.lock.json。

### BakaSU / SUSFS 与管理器

BakaSU 更新为 2026-10-25 main 提交 `d5e9e025b8b49155f8014684d64c91742b465f65`，驱动版本 `35252`。上游已解除 SUSFS 构建暂停；SUSFS 同步为 `27e0a0e42745991ba09d6f96a97bf4b83f41a012`，使用该版本原始内核补丁，不绕过兼容检查。

BakaSU 使用完整 Git 历史与标签，确保驱动版本号计算准确。非 Stock 构建从官方成功的 main CI `40109566037` 下载普通 `Manager-release` 与 `Spoofed-Manager-release`，严格核对该 CI 的源码提交与本次驱动完全一致，并验证上游 artifact SHA256（如提供）。不重新签名管理器。Release 同时发布 AK3、两份 APK、build-info.json、manager-info.json 和实际源码记录。

BakaSU 不是自动追踪最新分支：每次升级时必须同时更新 sources.lock.json 和 manager-ci.json，避免驱动与管理器混用。上游 Actions 产物有保留期限；缺失或过期会明确失败，不使用其他提交的管理器替代。
