# SUSFS compatibility patch

Source: simonpunk/susfs4ksu, gki-android14-6.1, commit 5192aa2d33b381b58c1051532f9e1dfa5de6e8d3. GPL-2.0.

50-susfs-crdroid17.patch preserves all upstream functional hunks. Only the first namespace.c hunk context/counts are adjusted to retain crDroid's existing trace/hooks/blk.h include. Checked with git apply --check against crDroid kernel 3127ab97bcbbd4a86f7326b48fc3a1fbe6a4c12c. No reject is discarded.
