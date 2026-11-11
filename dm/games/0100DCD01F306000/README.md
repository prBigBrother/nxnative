# Mina the Hollower (`0100DCD01F306000`)

Update 1.0.6 (v327680), SDK 21.4.3, Yacht Club Games' own engine on NVN. Modules `main` and `sdk`. Everything in the RomFS is a `.yc` file in Yacht Club's YCD archive format, uncompressed; the 114 shaders (110 keys) are in `shaders.pak.yc`. Both code builds are registered, but the bundled shader tables are 1.0.6 only. The packer derives separate shader tables for a registered package outside `shader_versions`, even with both updates present; the 1.0.5 arena cuts from PR #1021 remain registered. This avoids packing 1.0.5 with the 1.0.6 tables; the 1.0.5 binary is not available here for a combined split or another playtest.

The original contribution, [PR #1021](https://github.com/seedds/nxnative/pull/1021) by AmperageOverspend, reports the following for **1.0.5**: on the Mac (2026-11-03, Apple silicon, the iPhone's memory layout): boot, the intro, profile and name entry, the opening story and the opening on the boat at 60 fps (frame time p95 17.2 ms), with movement, attacks, the pause menu and its inventory; the profile saves and a later start loads it back into play. No `[RED]` line in the runs. On the iPhone: an iPhone 16 Pro Max plays it at a steady 60 fps (the user's report, 2026-11-03).

## What it needs

| Setting | Where | Why |
|---|---|---|
| YCD reader | `dm/gfx/tools/shader_split.py` (`ycd_files`, `ycd_shaders`) | the shaders are in `shaders.pak.yc`; see [Shaders](#shaders) |
| SDK 21.4.3 node area cut | `dm/tools/sdk_patches.py` (`MATCH_CUTS`, the SDK 22.2.0 rule's second fingerprint) | the SDK's address-region node area is 1 GB without it; see [Memory](#memory) |
| TLSF arenas 4 GB → 1 GB and 256 MB (both build IDs) | [`patches.py`](patches.py) | the engine's two arenas reserve 4 GB each; see [Memory](#memory) |
| `stdalloc_cap 0xa4000000` | [`game.tsv`](game.tsv) | the regions made after the StandardAllocator's need 1.48 GB |
| 5 GB block, 4.375 GB alias region | `game.tsv` | the NPDM declares 32 MB of system resource (virtual address memory) and `main` sets no heap: the provisional layout |
| `depth_mode zero` | `game.tsv` | the game calls `nvnDeviceSetDepthMode` with near = 0 at boot |
| `build v327680`, `shader_versions v327680` | `game.tsv` | 1.0.6 is checked locally; 1.0.5 always gets a derived shader profile and retains its build-gated cuts |

## Files

- A YCD archive: `YCD\0`, version 8, the header size (0xc0 in every `.pak.yc`, 0x140 and 0x180 in the sound banks), then a root record and a file table of 0x20-byte pairs, a name record and a data record per file, each with an offset from its record's +8. The names follow the table. `ycd_files` reads the table; it also lists the files of the level and player archives.
- `shaders.pak.yc` holds 229 files: `shaders/<name>.vert.bin` (20) and `.frag.bin` (94), a `.meta` beside each (binding names such as `g_tex`, `g_cbuffer_1`, `IN_0_pos`) and `shaders/shader.db` (2.3 MB, no shader code).
- The sound banks (`default.sndbnk.yc`, 630 MB, and three more) hold compressed audio.

## Shaders

- **Current:** each `.bin` is `{u32 control length, u32 code length, control section, code area}`, one stage compiled offline; the SPH stage of every one matches its file name. The engine combines vertex and pixel shaders per draw, so they are paired as single-stage programs (the pixel-input cover of `separable_pairs`, 17 pairs). All 110 translate for the Mac.
- The game loads every shader at boot. In 1.0.6, 90 of the 110 keys differ from PR #1021's 1.0.5 tables; the split still gives 17 vertex keys and 93 pixel keys, with 17 cover pairs. All 110 compile with chain `3ae08e02ec6a` on Xcode 27.2.

## Memory

PR #1021 measured **1.0.5** with a 64 GB alias region (`DM_ALIAS_SIZE`, the region table from `DM_REGIONS`) from boot into the boat, 7 minutes:

| Region | Reserved | Mapped | Who |
|---|---|---|---|
| StandardAllocator | 16 GB | 1.28 GB | `nninitStartup`, returning to `main+0x875c5c` |
| TLSF arena "Default Mem" | 4 GB | 320 MB | `main+0x6d8ac` |
| TLSF arena "Render Mem" | 4 GB | 16 MB | `main+0x6dc0c` |
| twelve 16 MB arenas, one of 64 MB | 0.24 GB | small | the engine's other arenas (`main+0x108a10`, `+0x108c20`) |

- **Resolved: the 1 GB node area.** The SDK-wide node area rule did not match this `sdk` build (`cb82ed52…`): its AddressRegionManager constructor (`sdk+0x14fbe0`, 276 bytes, the cuts at +0x10 and +0x7c) has the SDK 22.2.0 implementation's size and cut offsets but another fingerprint by its callees. With the fingerprint added to that rule, the StandardAllocator region starts at alias +0.06 GB instead of +1.00 GB. Region placement aligns only to 2 MB, as SDK 20, so no alignment cut is needed ([The SDK's address-region node area](../../../docs/reference/memory.md#the-sdks-address-region-node-area)).
- **Workaround: the TLSF arenas.** The engine's startup (`main+0x6d850`, from `nnMain`) initializes two TLSF arenas through `main+0xdec90` → `main+0xdda90`, `init(arena, size, 16 MB, 32 MB)`. The init rounds the size up to its page, derives the first-level bin count from it and reserves the whole size with `nn::os::AllocateAddressRegion` (`main+0x1089b0`), committing pages as the arena grows. Each asks for 4 GB, which an iPhone's 4.375 GB alias region cannot hold beside the StandardAllocator. The cuts in `patches.py` give them 1 GB and 256 MB, about 3 and 16 times what they map on the route. What the game does when an arena is full is not known: open.
- **iPhone layout checked on the Mac:** the StandardAllocator gets 2.56 GB (`stdalloc_cap`, maps 1.25 GB), the arenas 1 GB at alias +2.88 GB and 256 MB at +3.89 GB; the regions reach alias +4.14 GB of 4.375 GB. Resident memory is about 1.7 GB with 674 MB of Metal allocations.

## Playing on the Mac

`scripts/build_ipa_from_nsp.py <NSP folder> --platform mac` prints the run command. On a new save, the intro can be skipped with +, the profile's name is confirmed on Done (the D-pad: Down four times, Right, A), and A through the opening story leads to the boat.

## Found on this game

- **A YCD archive's shaders** (`shader_split.py`, `ycd_files` / `ycd_shaders`).
- **The SDK 21.4.3 AddressRegionManager constructor** for the node area rule: [The SDK's address-region node area](../../../docs/reference/memory.md#the-sdks-address-region-node-area).
- **Game-owned regions cut for the alias region** (the TLSF arenas), as [A 62 GB page allocator behind `nu::VirtualAllocHook`](../../../docs/reference/memory.md#a-62-gb-page-allocator-behind-nuvirtualallochook).

## Open

- Play past the opening on the boat is untested on the Mac, and so is what the engine does when a TLSF arena runs out (the cuts leave about 3 and 16 times the measured use).
- The base game 1.0.0 (v0) is not registered; the NSP script packs it from a derived profile, without the arena cuts.
- 1.0.6 has not been tested on an iPhone here. The iPhone result above belongs to PR #1021's 1.0.5 run.

## 1.0.6 on current main

Ported the profile and YCD reader from PR #1021 to upstream `084f5aa5` on 2026-11-11. The reader also rejects unknown YCD versions, root records outside the file table, and shader members shorter than their two length fields; synthetic tests cover these cases and the file-scan prefilter.

`main=e86ae07bdfec77ee10d50d2163d0ff2e`, `sdk=cb82ed52216313df5626154efb64d45f` (the same SDK as 1.0.5). Both arena size instructions moved by +0x20: `main+0x6d8cc` and `main+0x6dc2c`. Disassembly confirms the names (`main+0x8d8c30`, `main+0x8df519`) and both calls to `main+0xdecf0` with a 16 MB page and 32 MB growth. These fixed sites are registered only for this build ID. The SDK node-area rule matches `sdk+0x14fbf0` and `sdk+0x14fc5c`.

Mac test device: MacBook Pro, M2 Pro, 32 GB, macOS 27.2 (26B123), Xcode 27.2. Build: `build_ipa_from_nsp.py --platform mac`; all 110 shaders compile, and the Mac host and pipeline prebuild succeed. The runtime uses `DM_ALIAS_SIZE=0x118000000` to check the iPhone-sized alias region on the Mac; the StandardAllocator is capped to 2.56 GB and startup reaches alias +3.90 GB. A seven-minute run reached the opening boat, with movement and jump input, inventory, pause/options, return to title and the saved profile visible there. The last quiet 300-frame boat/menu windows report frame p50 16.67 ms, p95 16.68–16.74 ms (about 60 fps); resident memory is about 1.75 GB, Metal allocations about 748 MB. This is bring-up validation, not a whole-game playthrough. A fresh process reads the saved profile again; continuation is checked back to the opening. The first run has no `[RED]` lines; during the second run, alongside graphics test builds, one audio callback missed 214 ms and the host selected its silent sink/retry path. That transient has not been traced to the game, and audio timing is not validated.

The new prewarm list holds 110 shader and 17 render-pipeline entries from that route. A self-contained Mac app (922.4 MB including the RomFS) also builds and passes `codesign --verify --deep --strict`.

Checks on current main: 40 profile/docs/patch/reader/version-selection tests pass; the 9 reader tests also pass on the PR #1021 follow-up branch. The final full tool suite runs 1,462 tests, with 27 skipped and two failures: `test_env_switches` (stale upstream switch documentation, reproduced unchanged on a clean `084f5aa5` checkout), and `test_triage_report.Report.test_main_load`. All 14 triage-report tests pass when rerun separately; no triage code was changed. An earlier 1,458-test run before the shader-version tests had only the environment-documentation failure. The pinned lint tools report no finding in the changed files; the full ratchet reports the upstream `dmsh_entry.py` unused `dmsh_fetch` import and, with NumPy installed locally, one fixed missing-import baseline entry. No unrelated baseline is rewritten.

`regress.py check --games 0100DCD01F306000 --no-smoke` passes on current main versus the integration worktree: 110/110 shaders on each side, no newly failing shader, no changed MSL and no pipeline-interface error. Runtime testing is the manual Mac route above; no harness smoke route is supplied. The full Metal graphics suite (`make -C dm/gfx/tests GAME=0100DCD01F306000 -j3 run`) also passes on the M2 Pro. Only Mina was selected for the game regression comparison: the reader changes are limited to YCD files and the SDK fingerprint is this game's `sdk`; other games are not validated by this report.

The registered-build selection fix is described in [A registered build outside the shader versions](../../../docs/reference/packing.md#a-registered-build-outside-the-shader-versions).
