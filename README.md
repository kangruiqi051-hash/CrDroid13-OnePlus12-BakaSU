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

SUSFS 补丁冲突会失败停止，不使用 `patch || true` 或删除 rejects。遇到上游更新导致冲突时，需要手工审查兼容适配后再构建。可选功能默认关闭，按需在 Actions 中选择。

## 归属

参考工作流和 extract-cert 主机兼容修复来自 Floran-Kernel；内核和各补丁保留上游许可证。此仓库是构建脚本集合，不把上游代码改称自有源码。来源 URL 和提交见 sources.lock.json。

### BakaSU / SUSFS 与管理器

BakaSU 更新为 2026-10-25 main 提交 `d5e9e025b8b49155f8014684d64c91742b465f65`，驱动版本 `35252`。上游已解除 SUSFS 构建暂停；SUSFS 同步为 `27e0a0e42745991ba09d6f96a97bf4b83f41a012`，使用该版本原始内核补丁，不绕过兼容检查。

BakaSU 使用完整 Git 历史与标签，确保驱动版本号计算准确。非 Stock 构建从官方成功的 main CI `40109566037` 下载普通 `Manager-release` 与 `Spoofed-Manager-release`，严格核对该 CI 的源码提交与本次驱动完全一致，并验证上游 artifact SHA256（如提供）。不重新签名管理器。Release 同时发布 AK3、两份 APK、build-info.json、manager-info.json 和实际源码记录。

BakaSU 不是自动追踪最新分支：每次升级时必须同时更新 sources.lock.json 和 manager-ci.json，避免驱动与管理器混用。上游 Actions 产物有保留期限；缺失或过期会明确失败，不使用其他提交的管理器替代。

## 可选内核 Features

参考 [WildKernels/GKI_KernelSU_SUSFS](https://github.com/WildKernels/GKI_KernelSU_SUSFS) 的功能开关，适配本项目的 crDroid android14-6.1 内核。原有 variant 继续决定是否集成 BakaSU / SUSFS；下面的新增功能均默认关闭。

| Actions 选项 | 实际作用 |
| --- | --- |
| `use_nomount` | 集成 NoMount VFS 驱动。仍需配套用户空间元模块；构建内核不会自动安装手机模块。 |
| `use_bbg` | 集成 Baseband Guard LSM，并保留已有 LSM 顺序后追加 baseband_guard；会限制相关分区访问。 |
| `use_net` | BBRv3 补丁，启用 BBR 默认拥塞控制、WireGuard、CIFS、IPSET、IPv6 NAT、TTL/HL、队列调度等。不会自动修改手机的代理、路由或共享网络。 |
| `use_ds` | DroidSpaces 所需命名空间、SYSVIPC、消息队列、devtmpfs 和执行格式，使用 kABI 预留空间存放 SYSVIPC 字段。 |
| `use_ntsync` | 回移 NTSync 驱动和 6.1 兼容补丁。 |
| `use_unicode` | 实验性 Unicode 路径处理补丁。 |
| `use_bpf` | eBPF / BTF / FUSE-BPF 与探针配置；不自动安装用户空间工具。 |
| `use_perf` | 上游实验性内存、调度、文件系统、电源及日志补丁集合；不保证更省电或更流畅。 |
| `use_ptrace` | 保留上游选项以便对照；上游只对 5.16 之前的内核应用此修复，本项目 6.1 标记为不适用，不重复打补丁。 |

功能源码固定在 `features.lock.json` 的提交，不执行浮动版本的远程安装脚本。`patches/features/` 是为 crDroid 上下文调整的补丁；其来源、修改点见该目录说明。功能补丁在 SUSFS 后应用，冲突立即停止；olddefconfig 后逐项核实请求的配置，未生效则构建失败。

产物中的 `features.json` 记录本次选项、补丁哈希及配置验证结果，`build-info.json` 同时包含这些信息，Release 附带这些记录。Artifact 中额外保留本次实际应用的功能补丁。新功能需要实机验证，建议逐项启用以方便判断兼容性。

网络配置适配说明：此 crDroid 6.1 分支的 CIFS 本身不依赖 NETFS_SUPPORT。NETFS_SUPPORT 为隐藏选项，由 FSCACHE 等功能选择，因此不直接请求它，也不额外开启未要求的磁盘缓存功能。
