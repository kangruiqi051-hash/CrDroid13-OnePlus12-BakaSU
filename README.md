# crDroid 13 / OnePlus 12 (waffle) Kernel Builder

为 OnePlus 12 的 crDroid 13 / Android 17 构建 Linux 6.1 内核。参考 [Floran-Kernel](https://github.com/kangruiqi051-hash/Floran-Kernel)，root 使用改名后的 BakaSU（原 ReSukiSU）。

## 使用

Actions → Build crDroid 13 OnePlus 12 Kernel → Run workflow。

- `BakaSU-SUSFS`：内置 root 和 SUSFS，默认选项。
- `BakaSU`：仅内置 root，使用 tracepoint hook。
- `Stock`：不集成 root/SUSFS 的源码对照构建；不是原 ROM 二进制的逐位复现。
- `create_release`：默认关闭；开启后成功产物会发布为 Release。

下载运行页面的 Artifacts。里面包含 AnyKernel3 ZIP、原始 Image、最终 kernel.config、构建日志和来源记录。失败时也上传日志，但不会生成可刷包。没有定时编译，手动触发。

## 来源和兼容性

所有源码固定在 sources.lock.json。主内核 17.0 分支提交 `3127ab97bcbbd4a86f7326b48fc3a1fbe6a4c12c`，对应 `6.1.175-g3127ab97bcbb`。内核、设备树和厂商模块的仓库均来自 crDroid 17.0 设备依赖。SUSFS 使用内核系列 `gki-android14-6.1`；它与用户空间的 Android 17 不是同一版本编号。

使用官方三个 defconfig 片段，参考 Floran 的 Android 17 Clang r596125，并记录工具链压缩包 SHA256。BakaSU 直接集成固定提交，不调用会追踪最新版的 setup.sh。

本工作流只编译和替换 boot 中的 Image，不刷 vendor_boot、dtbo、init_boot 或厂商模块。配套 modules/devicetrees 源码保留用于核对，不宣称重新构建了完整 ROM。必须使用匹配的 crDroid 厂商模块，编译成功不代表设备验证成功。振动、相机、Wi-Fi、recovery 必须实机验证。

切换到内置 root/SUSFS 前，准备当前 ROM 原版 boot/init_boot；移除旧 LKM root 修补，并停用原来的 SUSFS LKM 自动加载脚本，避免双重加载。不要通过重建不同内核分支来混搭原版模块。保留 fastboot 恢复镜像。

## 补丁维护

SUSFS 补丁冲突会失败停止，不使用 `patch || true` 或删除 rejects。需要在固定 crDroid 提交上手工审查兼容适配后再构建。默认不加入 LZ4、Docker、Droidspaces 或其他无关功能。

## 归属

参考工作流和 extract-cert 主机兼容修复来自 Floran-Kernel；内核和各补丁保留上游许可证。此仓库是构建脚本集合，不把上游代码改称自有源码。来源 URL 和提交见 sources.lock.json。
