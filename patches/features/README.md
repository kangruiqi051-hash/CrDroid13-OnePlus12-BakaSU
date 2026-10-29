# crDroid 6.1 feature patch adaptations

Upstream source commits are fixed in ../../features.lock.json. Patches retain their upstream authorship and license.

Adapted against crDroid 17.0 kernel commit 6c0d07d008217df4afde27a351f711343e975b85:

- SYSVIPC: preserve crDroid's occupied kABI slots 1–3, retain slots 4–5 and use only slots 6–8 as upstream intended; refresh context. Source: Droidspaces-OSS.
- f2fs_reduce_congestion: preserve the additional MAX_FLUSH_RETRY_COUNT declaration and change only DEFAULT_IO_TIMEOUT from 20 to 6 ms.
- clear_page_16bytes_align: crDroid uses SYM_FUNC_START(__pi_clear_page); add the same .p2align 4 directive.
- disable_cache_hot_buddy: refresh context for crDroid's scheduler feature list.
- increase_sk_mem_packets: change the same _SK_MEM_PACKETS macro to 1024; crDroid names its consumers SK_WMEM_MAX/SK_RMEM_MAX instead of *_DEFAULT.
- reduce_pci_pme_wakeups: refresh context; preserve 1000 -> 4000 ms change.

All except SYSVIPC originate in WildKernels/kernel_patches/common. Application uses strict git apply --check, with reverse check for already-applied patches. No automatic fuzzy adaptation is performed during CI.
