# VisionCut AI - Project Specification

## Goal

VisionCut AI is a professional desktop application for AI-powered video masking, background removal, and compositing.

The software is designed for:

- Real Estate Marketing
- Content Creators
- Agencies
- Video Editors
- Businesses

--------------------------------------------------

## Project Status

Current Version:
Sprint 31.1

Project Status:
Active Development

Completion Estimate:

```
Core Engine ............ 90%   (Project/Timeline/Track/Clip, Controller, Signals -- mature, no defects found this session)
Playback ............... 90%   (decode/seek/scrub solid and benchmarked; see Segmentation caveat below)
Render Cache ........... 90%   (critical population bug fixed Sprint 27.1; lookahead cache, partial invalidation, priority throttle all verified working)
Segmentation ........... 60%   (Sprint 31 improved sampling/latency/UX, but Sprint 32 found a confirmed, unfixed coordinate bug -- see Technical Debt)
Tracking ................ 65%  (functions, but MIL fallback with inconsistent stability: 100% one test clip, 55% another)
Export .................. 70%  (PNG sequence + WebM/MOV alpha exist and have dedicated verify scripts from earlier sprints; not re-verified end-to-end this session)
Developer Tools ........ 90%   (live CPU/GPU/VRAM/queue/cache/tracking/confidence telemetry, log console)
UI Polish ............... 65%  (functional but has a confirmed dead settings surface -- see Technical Debt)
Documentation ........... 85%  (this document, as of this rewrite)
```

These are working estimates based on what has actually been read, benchmarked, or reproduced this session -- not a formal audit of every file. Where a number reflects a specific known issue, that issue is named in Technical Debt below.

--------------------------------------------------

## Version 1.0 Feature Scope

Each item is classified as **Implemented**, **Partial**, or **Planned**, verified against the current codebase (not assumed from this document's prior contents).

### Video

| Feature | Status | Evidence |
|---|---|---|
| Open MP4 | Implemented | Primary format used in all testing this session (`real.mp4`, `dummy_1080p.mp4`) |
| Open AVI | Implemented | Tested this session (`vtest.avi`) via the same OpenCV/FFmpeg decoder path |
| Open MOV | Planned/Unverified | Decoder path (`cv2.VideoCapture`/FFmpeg) is container-agnostic so this likely works, but it was not directly tested this session -- not claiming it as verified |
| Play / Pause / Stop / Seek | Implemented | `core/video_engine.py`, `core/timeline_playback.py`; exercised throughout every sprint this session |
| Timeline | Implemented | Multi-clip timeline with split/trim/move, exercised via `core/timeline.py` and the timeline UI |

### AI

| Feature | Status | Evidence |
|---|---|---|
| Background Removal | Implemented | `ai/background_removal_processor.py` (rembg + ONNX Runtime); render cache + live pipeline both verified this session |
| Green Screen | Planned | No matching code found anywhere in the repo (`grep` for "Green Screen" returns nothing) |
| Blur Background | Planned | No matching code found |
| Replace Background | Planned | No matching code found -- no background-image compositing path exists |

### Manual Tools

| Feature | Status | Evidence |
|---|---|---|
| Brush (stroke prompt) | Implemented | `ui/widgets/viewer_widget.py` stroke drawing -> `sample_stroke_points()` in `ai/background_removal_processor.py` |
| Point Prompt | Implemented | A zero-drag stroke (click without moving) naturally produces a single-point prompt through the same stroke pipeline |
| Rectangle | Implemented | Dedicated "Bounding Box" prompt mode (`playback_controls.py` prompt_mode_combo -> `_drawing_box` handling in `viewer_widget.py`) |
| Eraser | Planned | No dedicated eraser tool. Negative-label strokes partially cover this use case (subtract from the selection via SAM re-prompting) but there is no literal pixel-eraser |
| Polygon | Planned | No matching code found |

### Export

| Feature | Status | Evidence |
|---|---|---|
| PNG Sequence | Implemented | `core/export/png_sequence_exporter.py`, has a dedicated Sprint 19/20-era verify script |
| Transparent WebM | Implemented | `core/export/video_exporter.py`, real FFmpeg encoding logic (not a stub); has a dedicated verify script |
| MOV Alpha | Implemented | Same exporter, alternate codec path; has a dedicated verify script |
| Plain MP4 | Planned | **Correction to prior spec**: no plain-MP4 export path exists. `core/exporter.py.start_export()` only recognizes `"PNG Sequence (Video)"`, `"Transparent WebM"`, `"MOV Alpha"` |
| Custom Resolution / Custom FPS | Unverified | Not traced this session -- not claiming either way |

--------------------------------------------------

## Architecture

```
UI (PyQt6)
  |
Controller (core/controller.py)
  |
Core Engine (video/timeline/render-cache/tracking)
  |
AI Modules (ai/background_removal_processor.py)
```

| Subsystem | Status | Notes |
|---|---|---|
| AI runtime | Implemented | `rembg` + ONNX Runtime. Providers resolved in priority order TensorRT -> CUDA -> CPU (`BackgroundRemovalProcessor._resolve_providers`). Models: u2net (default), u2netp (Draft), silueta (Balanced), sam/mobile_sam (interactive + tracking). **Not** PyTorch -- confirmed zero `torch` imports in the codebase. |
| Tracking backend | Partial | Requests CSRT (`cv2.TrackerCSRT_create`), unavailable in the installed OpenCV build, silently falls back to `cv2.TrackerMIL_create()` every time. Confirmed via runtime logs in every tracking test this session. Tracker abstraction (`core/ai/trackers/base_tracker.py`) exists and is pluggable in principle; only one concrete backend is implemented. |
| Render cache | Implemented | `core/ai_render_cache.py`: `AIRenderWorker` builds alpha-mask PNG + JSON cache offline; `CacheLookaheadThread` RAM-prefetches decoded masks; `invalidate_from()` does partial (not full-wipe) invalidation; `render_priority` (Low/Normal/High) throttles the offline worker. A critical bug that silently prevented the cache from ever populating (`state.bbox` vs. the real `state.bounding_box` attribute) was found and fixed Sprint 27.1 -- before that fix, "no AI inference during playback" was not actually true in practice. |
| Playback pipeline | Implemented | Timeline -> decoded frame -> cached alpha mask -> composite -> display. Verified no AI inference occurs on the playback hot path once cache exists (real end-to-end test, Sprint 27.1/30/31). |
| Interactive segmentation | Partial | Sprint 31 added geometry-aware (RDP) prompt sampling, a non-blocking background worker (`core/interactive_mask_worker.py`) with debounce + request coalescing for live refinement, and confidence-based visual feedback. Sprint 32 (in progress, see below) found a confirmed coordinate-mapping defect in this same path. |
| Developer workflow | Implemented | `ui/widgets/developer_panel.py`: live CPU/GPU/VRAM/AI-queue/cache-size/tracking-state/prompt-confidence telemetry polled every 1s, plus an in-app log console. `Launch_Dev.bat` runs the app directly via `python app.py` (VISIONCUT_ENV=development). |
| Build system | Partial | PyInstaller `--onedir` build works and was verified this session (produces a working ~1.1GB bundle with a functional `.exe`, tested by launching it twice, from two separate builds). Some TensorRT-specific DLLs (`cudnn64_9.dll`, `cublas64_12.dll`, `nvinfer_10.dll`) are not bundled -- CUDA/CPU providers still work as fallback. `Build_Dev.bat`'s build step itself works; the deploy+launch steps after it don't complete unattended -- see Technical Debt #4 for the specific diagnosis. |
| Export pipeline | Partial | PNG sequence and WebM/MOV-alpha video export both have real encoding code and dedicated verify scripts from earlier sprints. Not re-run/re-verified end-to-end this session -- classified Partial on that basis, not because of a known defect. |

--------------------------------------------------

## Technical Debt

Ordered roughly by severity/user impact:

1. **Confirmed interactive-prompt coordinate bug (Sprint 32, unfixed).** When preview quality is set below "Full Resolution" (Half/Quarter), every stroke/box/point coordinate sent to MobileSAM is incorrectly scaled down by the preview ratio before being clamped to frame bounds -- e.g. at Half Resolution, a click at original-frame x=1000 is sent to SAM as x=500. Reproduced and quantified with a standalone script (`viewer.mapToScene()` already returns full-resolution scene coordinates by construction; `ui/widgets/viewer_widget.py`'s mouse handlers then redundantly multiply by `scale_factor = 1/item.scale()`, which only happens to be a no-op at the default `preview_scale = 1.0`). This plausibly explains reported symptoms ("strokes don't select the intended object", "mask doesn't snap to boundaries", "must repeatedly paint over the object") for any user who has reduced preview quality for performance -- exactly the scenario a 4GB-VRAM laptop user would choose. Root cause identified with evidence; fix not yet applied (work was paused mid-audit for this documentation sprint). Affected: `ui/widgets/viewer_widget.py` `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` (stroke and box branches).

2. **`SettingsDialog` is a fully disconnected settings surface.** `ui/settings_dialog.py` reads/writes `Playback/preview_quality`, `AI/device`, `Performance/ram_preload`, and `Export/priority` via `QSettings`, but grepping the entire repo shows these four keys are never read anywhere else -- nothing applies them to actual behavior. The dialog is reachable from the real Settings menu action, so a user changing these values and clicking Save will see no effect, silently. This also triplicates control surfaces that already exist and work elsewhere: real preview quality lives in `main_window.py`'s toolbar combo, real render priority lives in `playback_controls.py`'s combo (with a different option set -- "Realtime" here vs. "Low" there) -- not yet reconciled.

3. **MIL tracker fallback.** `core/ai/trackers/csrt_tracker.py` requests `cv2.TrackerCSRT_create`, unavailable in the installed OpenCV build, and silently falls back to `cv2.TrackerMIL_create()`. Confirmed via runtime logs every session. Tracking stability measured inconsistent across test clips (100% vs. 55% completion). Fix requires either `opencv-contrib-python` or an alternate tracker implementation behind the existing `BaseTracker` abstraction.

4. **`Build_Dev.bat` does not run to completion from a non-interactive automation shell.** Corrected diagnosis (the version of this item written earlier in this same sprint was wrong -- re-verified with ground truth before finalizing): the PyInstaller build step inside the script *does* complete successfully (confirmed via a fresh `dist/VisionCutAI/VisionCutAI.exe` timestamp matching the run). What doesn't complete automatically is everything after it -- the Desktop deploy (`xcopy`) and launch (`start`) steps. Two concrete suspects in the script: three separate `pause` commands (including one unconditionally at the very end) that block waiting for a keypress with no interactive terminal to provide one, and a `FOR /F` loop that shells out to a nested `powershell -command` call to resolve the Desktop path, which is a known source of hangs when a `.bat` is itself invoked from within Git Bash. Worked around this sprint by running the build via the script (which now works) and completing deploy+launch manually (which has been reliable both times it's been done that way). Worth fixing the script directly -- e.g. removing/guarding the `pause` calls -- so the literal documented workflow works unattended.

5. **`print()` vs. `logging`.** Only `core/processing_engine.py` and `core/video_engine.py` use the `logging` module; `print()` remains prevalent in the AI processors, controller, and UI debug paths. Not a functional bug, but inconsistent with the stated coding standard and noisy in production (e.g. per-frame SAM diagnostics print unconditionally).

6. **Resolved this session, noted for history:** a duplicate/unsafe "AI Quality" control existed in both `main_window.py` (safe: routes through `controller.set_ai_preview_quality()`, invalidates render cache) and `playback_controls.py` (unsafe: raw `setattr` on the processor, bypassed the lock, never invalidated the cache -- meaning changing quality through it could silently serve stale-resolution cached masks). Fixed by routing the second control through the same safe method. `SettingsDialog` (item 2 above) reintroduces a version of this same class of problem and is not yet resolved.

--------------------------------------------------

## Sprint History

### Sprint 27.1 - Performance Validation & Optimization
- **Objective:** Validate the AI render-cache architecture actually eliminates inference from the playback hot path, with real benchmark numbers.
- **Files modified:** `core/ai_render_cache.py`
- **Key achievements:** Built a real benchmark harness (decoder throughput/seek latency, SAM inference latency, PNG write/read time, composite time, disk cache size, CPU/RAM/GPU/VRAM sampling, full tracking-to-cache-to-playback pipeline).
- **Regressions fixed:** Critical -- `AIRenderWorker` referenced `state.bbox`, which doesn't exist on `TrackedFrameState` (real attribute is `bounding_box`), causing an unhandled exception that silently prevented the render cache from ever populating beyond frame 0. Before this fix, the "no inference during playback" architecture did not actually work.
- **Performance improvements:** Added an in-memory decoded-mask cache to avoid re-reading/re-decoding PNGs from disk every playback frame (~8ms/read from disk vs. ~0.0004ms from memory). This was later superseded by the more capable `CacheLookaheadThread` added outside this session's edits.
- **Remaining issues at sprint end:** None blocking; cache-served playback confirmed to keep up with source FPS.

### Regression-Fix Sprint (post-Sprint 30, unnumbered)
- **Objective:** Detect and fix regressions surfaced by re-reading the codebase after substantial external changes ("Sprint 30" work: dynamic prompt density, lookahead cache, partial invalidation, render-priority throttle).
- **Files modified:** `ai/background_removal_processor.py`, `core/ai_render_cache.py`, `core/controller.py`, `ui/main_window.py`
- **Key achievements / regressions fixed:**
  - VRAM-safety regression: quality-preset scaling had lost its hard pixel cap, letting large sources run MobileSAM at up to ~2-3x the intended resolution on a 4GB GPU. Restored the cap; measured 28% latency reduction on a 4K test frame (1092.6ms -> 785.3ms) as direct evidence.
  - `render_priority` UI control was wired to the wrong object (`AIRenderCache` instead of the actual `AIRenderWorker` instance) and had no effect. Fixed with a proper `set_render_priority()` that propagates to a running worker.
  - Duplicate/unsafe AI-quality control (see Technical Debt #6). Fixed.
  - Tracked-forward prompt points used a stale fixed 5-point cap while the live preview used dynamic 2-20 point density -- unified via a shared `sample_stroke_points()` helper.
- **Performance improvements:** 28% latency reduction (above).
- **Remaining issues:** None identified at the time; superseded by Sprint 32 findings.

### Sprint 31 - Prompt Intelligence & Segmentation Quality
- **Objective:** Improve segmentation quality and interaction feel without redesigning playback/render-cache/tracking.
- **Files modified:** `ai/background_removal_processor.py`, `core/controller.py`, `ui/main_window.py`, `ui/widgets/playback_controls.py`, `ui/widgets/video_player_widget.py`, `ui/widgets/video_preview.py`, `ui/widgets/viewer_widget.py`, `ui/widgets/developer_panel.py`. New: `core/interactive_mask_worker.py`.
- **Key achievements:**
  - Geometry-aware prompt sampling (Ramer-Douglas-Peucker) replacing length-only sampling: a straight 595px stroke now uses 2 points instead of 20; a similar-length curved stroke still uses up to 20.
  - Verified (not assumed) that prompt accumulation and undo-last-prompt already worked correctly at the data level; added the missing "Undo Last" UI button for discoverability.
  - Non-blocking live refinement: new background worker with request coalescing + a 150ms debounce, replacing a synchronous call that froze the UI thread for ~800ms per stroke (the old code's own comment admitted this). Verified real SAM dispatch returns control in <1ms.
  - Confidence visualization: amber overlay + outline for fragmented/low-confidence masks, fixed a pre-existing bug where "Confidence Low" rendered in status-bar success-green, added a Developer Panel confidence readout.
- **Regressions fixed:** A new race was introduced by making regeneration async (stale mask could be applied while a newer regenerate was in flight) and was closed with an explicit busy-state guard, verified with a scripted test.
- **Performance improvements:** 15 rapid live-drag updates collapsed into 1 actual inference call (debounce+coalescing verified). Talking-head test: 1 prompt needed, 835ms latency, 100% tracking stability, 1052MB VRAM peak.
- **Remaining issues:** Walking-pedestrian tracking stability measured only 55%, traced to the pre-existing MIL fallback, not a Sprint 31 regression.

### Sprint 32 - Interactive Segmentation Pipeline Audit (IN PROGRESS, not complete)
- **Objective:** Full audit of the interactive segmentation pipeline (mouse input through mask generation) to find the root cause of poor object-selection accuracy, without assuming the UI layer or guessing.
- **Status:** Root cause identified and confirmed with a standalone, quantified reproduction (see Technical Debt #1). Fix, Developer Debug Mode visualization, and the requested multi-scenario benchmark were **not yet completed** -- work was paused by request before those steps.
- **Files modified:** None yet (audit/diagnosis only).
- **Remaining issues:** Everything past root-cause identification: the fix itself, the toggleable Developer Debug Mode (raw/transformed prompt points, SAM input image, raw/cleaned mask, final overlay), and the benchmark across talking head / walking person / complex background / overlapping people / thin objects.

### Sprint 31.1 - Documentation Synchronization
- **Objective:** Bring this document in line with actual codebase state; add Project Status, Technical Debt, and Sprint History.
- **Files modified:** `docs/PROJECT_SPECIFICATION.md`
- **Key achievements:** Every technical claim in this revision was checked against the codebase this session (grep/read), not carried forward from the prior document. Corrected: stale "Sprint 3" status, incorrect PyTorch dependency claim, incorrect plain-MP4 export claim, incorrect "Logging Instead of print()" standard. Newly documented: the disconnected `SettingsDialog` (found while verifying this sprint's claims).
- **Regressions fixed:** None (documentation only, per instruction not to change code to match docs).
- **Process note:** The mandatory post-sprint build/deploy/launch step itself produced a correction mid-sprint. `Build_Dev.bat` was re-run to comply with the workflow; this time its PyInstaller build step completed successfully (verified by the fresh `dist/` timestamp), contradicting an earlier, less precise claim about it. The deploy and launch steps after the build still didn't complete unattended, so those were finished manually (xcopy to Desktop, launch) -- consistent with what worked in Sprint 31. Technical Debt item #4 was rewritten with this more accurate diagnosis rather than left as originally drafted.
- **Performance impact:** None (no runtime code changed).
