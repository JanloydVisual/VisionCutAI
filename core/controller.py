from core.project import Project
from core.video_engine import VideoEngine
from core.processing_engine import ProcessingEngine
from core.project_importer import ProjectImporter
from core.edit_history import EditHistory
from core.timeline_playback import TimelinePlayback
from core.ai_render_cache import AIRenderCache
from core.ai.object_tracker import ObjectTracker
from core.interactive_mask_worker import InteractiveMaskWorker


def _prompt_bounding_region(prompts):
    """Union bounding box (x1, y1, x2, y2), original-frame coordinates, of
    every point/rectangle/stroke coordinate in a prompt list. Used by the
    off-target confidence check -- see _on_interactive_mask_ready."""
    xs, ys = [], []
    for p in prompts:
        data = p.get('data')
        if not data:
            continue
        if p.get('type') == 'stroke':
            for pt in data:
                xs.append(pt[0])
                ys.append(pt[1])
        elif p.get('type') == 'point':
            xs.append(data[0])
            ys.append(data[1])
        elif p.get('type') == 'rectangle':
            xs.extend([data[0], data[2]])
            ys.extend([data[1], data[3]])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


class AppController:
    """
    Connects the GUI with application engines without importing PyQt6.
    """

    def __init__(self):
        self.on_interactive_mask_updated = None
        self.on_interactive_points_updated = None
        self.on_interactive_busy_changed = None
        self.on_debug_prompt_points_updated = None
        self.on_tracker_initialized = None
        self.on_error_occurred = None
        self.on_workflow_stage_changed = None
        self.on_refinement_verdict_changed = None

        # Three-stage workflow (Sprint 32E): 1 = Select Object, 2 = Track
        # Object, 3 = Remove Background. Purely a UI-guidance concept --
        # doesn't gate what the underlying methods allow, just tells the
        # stage indicator what to highlight.
        self.workflow_stage = 1

        self.project = Project()
        self.importer = ProjectImporter(self.project)

        self.video = VideoEngine()

        self.processing = ProcessingEngine()
        self.processing.start()

        self._background_removal_processor = None
        self.background_removal_error = None
        self._init_ai_processor()
        self.frames_sent_to_processing = 0
        self.ai_mode = "u2net"
        self._interactive_prompts = []
        # Sprint 36: snapshot-based undo/redo -- replaces the old append/
        # pop-only stack, which could only undo "the last thing added".
        # Arbitrary delete and enabled/disabled toggling both need to be
        # undoable too, and a full-list snapshot before every edit handles
        # any edit type uniformly instead of needing a hand-written
        # inverse for each one.
        self._prompt_undo_stack = []
        self._prompt_redo_stack = []
        self._prompt_id_counter = 0
        self._prompt_edit_seq = 0
        self.on_prompt_list_changed = None

        # Sprint 31: live interactive-mask regeneration runs on its own
        # background thread (latest-request-wins), decoupled from the Qt
        # UI thread that processor.process() would otherwise block for
        # ~1s per call. See core/interactive_mask_worker.py.
        self._interactive_worker = InteractiveMaskWorker()
        self._interactive_worker.result_ready.connect(self._on_interactive_mask_ready)
        self._interactive_worker.start()
        self._live_stroke_prompt = None
        self._live_regenerate_timer = None
        self._interactive_busy = False
        self._last_confidence_info = None  # dict: state/confidence_pct/area_fraction/bbox_w/bbox_h/components -- see _on_interactive_mask_ready
        self._last_quality_gate = None  # dict: gate/6 metrics/reasons -- Sprint 34, see _evaluate_quality_gate
        # Sprint 35: quality-gate progression across committed prompts (one
        # entry per Keep(+)/Remove(-) stroke that actually got applied, not
        # per live-drag preview frame) -- see _record_refinement_progress.
        self._quality_gate_history = []
        self._last_refinement_verdict = None

        self.render_cache = AIRenderCache()
        self.object_tracker = ObjectTracker()

        self.history = EditHistory()
        self._edit_snapshot = None

        # -- TimelinePlayback coordinator --------------------------------
        self.timeline_playback = TimelinePlayback(
            timeline=self.project.timeline,
            decoder=self.video,
        )

        # Expose the coordinator's frame-ready signal so MainWindow
        # gets (frame, timeline_frame) instead of just frame.
        self.frame_ready = self.timeline_playback.frame_ready

        # Keep the original VideoEngine.frame_ready connected for
        # the background-removal pipeline (unchanged path).
        self.video.frame_ready.connect(self._process_frame)

        # -- Blade mode state -------------------------------------------
        self._blade_mode = False

        from core.tracking_engine import TrackingEngine
        self.tracking_engine = TrackingEngine(self.video, self.object_tracker)
        self.tracking_engine.progress_updated.connect(lambda c, t, conf: self.on_tracking_progress_updated(c, t, conf) if hasattr(self, 'on_tracking_progress_updated') else None)
        
        # When tracking is complete, automatically start background AI rendering
        def on_tracking_done():
            if hasattr(self, 'on_tracking_status_changed'):
                self.on_tracking_status_changed("Complete")
            
            # Start Render Cache
            worker = self.render_cache.start_caching(
                self.timeline_playback,
                self.tracking_engine,
                processor=self._background_removal_processor
            )
            if hasattr(self, 'on_render_cache_started'):
                self.on_render_cache_started(worker)
                
        self.tracking_engine.tracking_completed.connect(on_tracking_done)
        self.tracking_engine.tracking_failed.connect(lambda m: self.on_tracking_status_changed(f"Failed: {m}") if hasattr(self, 'on_tracking_status_changed') else None)
        self.tracking_engine.tracking_paused.connect(lambda m: self.on_tracking_status_changed(f"Paused: {m}") if hasattr(self, 'on_tracking_status_changed') else None)
        
        from core.exporter import ExportManager
        self.exporter = ExportManager(self.project, self._background_removal_processor, self.tracking_engine)
        
    def _on_tracking_progress(self, current, total, confidence):
        if getattr(self, 'on_tracking_progress_updated', None):
            self.on_tracking_progress_updated(current, total, confidence)
        
    def _on_tracking_completed(self):
        print("Background tracking completed.")
        if getattr(self, 'on_tracking_status_changed', None):
            self.on_tracking_status_changed("Tracking Complete")
        
    def _on_tracking_failed(self, error):
        print(f"Background tracking failed: {error}")
        if getattr(self, 'on_tracking_status_changed', None):
            self.on_tracking_status_changed(f"Tracking Failed: {error}")
        
    def _on_tracking_paused(self, reason):
        print(f"Background tracking paused: {reason}")
        if getattr(self, 'on_tracking_status_changed', None):
            self.on_tracking_status_changed(f"Tracking Paused: {reason}")

    def _init_ai_processor(self):
        try:
            from ai.background_removal_processor import BackgroundRemovalProcessor

            processor = BackgroundRemovalProcessor()
            self._background_removal_processor = processor
            self.ai_device_label = processor.device_label
        except Exception as error:
            self.background_removal_error = str(error)
            self.ai_device_label = "AI unavailable"

    @property
    def background_removal_available(self):
        return self._background_removal_processor is not None

    @property
    def active_ai_provider(self):
        return self.ai_device_label if hasattr(self, 'ai_device_label') else "None"

    @property
    def background_removal_status(self):
        if self.background_removal_available:
            return f"Background removal ready ({self.ai_device_label})"
        return self.background_removal_error or "Background removal is unavailable"

    @property
    def blade_mode(self) -> bool:
        return self._blade_mode

    def start_background_removal(self):
        """Activates AI processing and processes the current preview frame."""
        return self.toggle_background_removal(force_on=True)

    def _process_frame(self, frame):
        pass

    def _set_workflow_stage(self, stage: int):
        if self.workflow_stage == stage:
            return
        self.workflow_stage = stage
        if self.on_workflow_stage_changed:
            self.on_workflow_stage_changed(stage)

    def open_video(self, filepath):
        # Reset previous project state
        self.project.new()
        self.clear_target_prompts()
        self.object_tracker.reset()
        if hasattr(self, 'tracking_engine'):
            self.tracking_engine.stop()
            self.tracking_engine.tracking_cache.clear()
        self._set_workflow_stage(1)
        
        info = self.importer.import_video(filepath)
        success = self.video.load_video(filepath)
        if not success:
            return False

        # After loading, snap the timeline playhead to the first
        # playable frame (which maps to source frame 0).
        self.timeline_playback.seek(0)
        return info

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def toggle_playback(self):
        """Toggle between play and pause."""
        self.timeline_playback.toggle_playback()

    def play(self):
        self.timeline_playback.play()

    def play_reverse(self):
        """Start reverse playback."""
        self.timeline_playback.play_reverse()

    def pause(self):
        self.timeline_playback.pause()

    def stop(self):
        self.timeline_playback.stop()

    def seek(self, frame_index):
        """Seek to *frame_index* in timeline-frame space."""
        self.timeline_playback.seek(frame_index)

    def preview_seek(self, frame_index):
        """Seek decoder to *frame_index* without moving playhead. For blade hover preview."""
        self.timeline_playback.preview_seek(frame_index)

    def next_frame(self):
        self.timeline_playback.step_forward()

    def previous_frame(self):
        self.timeline_playback.step_backward()

    # ------------------------------------------------------------------
    # JKL shuttle speed
    # ------------------------------------------------------------------

    def toggle_background_removal(self, force_on=False):
        if not self.video.is_loaded:
            return False

        if not self.background_removal_available:
            return False
            
        timeline_frame = self.timeline_playback.current_timeline_frame
        pos = self.timeline_playback.position_at(timeline_frame)
        if not pos:
            return False
            
        current_active = getattr(pos.clip, 'background_removed', False)

        # If forcing on, just turn it on without checking current state
        is_turning_on = force_on or not current_active

        if is_turning_on and not self.object_tracker.is_tracking:
            return False # Tracking must be initialized first!
            
        self.render_cache.clear()

        if is_turning_on:
            if self.ai_mode != "sam":
                self.set_ai_mode("sam")
            self.processing.set_processor(self._background_removal_processor)
            pos.clip.background_removed = True
        else:
            self.processing.set_processor(None)
            pos.clip.background_removed = False

        # Re-emit current frame
        self.render_cache.clear()
        self.timeline_playback.seek(self.timeline_playback.current_timeline_frame)

        # Update UI text based on new state
        if hasattr(self, 'on_tracker_initialized') and self.on_tracker_initialized:
            self.on_tracker_initialized()

        # Stage 3 (Remove Background) while active; turning it back off
        # returns to Stage 2 (Track Object) rather than resetting further.
        self._set_workflow_stage(3 if pos.clip.background_removed else 2)

        return pos.clip.background_removed

    @property
    def is_background_removal_active(self):
        if not self.video.is_loaded:
            return False
        timeline_frame = self.timeline_playback.current_timeline_frame
        pos = self.timeline_playback.position_at(timeline_frame)
        return getattr(pos.clip, 'background_removed', False) if pos else False

    @property
    def interactive_prompt_count(self) -> int:
        """Sprint 36: total prompts in this selection, enabled or not."""
        return len(self._interactive_prompts)

    @property
    def interactive_active_prompt_count(self) -> int:
        """Sprint 36: prompts SAM actually sees (enabled, non-disabled)."""
        return sum(1 for p in self._interactive_prompts if p.get('enabled', True))

    def set_ai_mode(self, mode_name: str):
        if not self.background_removal_available:
            return
        self.ai_mode = mode_name
        self._background_removal_processor.set_model(mode_name)
        self.render_cache.clear()
        if self.is_background_removal_active:
            self.timeline_playback.seek(self.timeline_playback.current_timeline_frame)

    def set_ai_preview_quality(self, quality: str):
        """Sets the AI pipeline quality and invalidates cache."""
        self.processing.set_quality(quality)
        self.render_cache.clear()
        if self.is_background_removal_active:
            self.timeline_playback.seek(self.timeline_playback.current_timeline_frame)

    def set_drawing_mode(self, enabled: bool):
        if enabled:
            # Once Apply Target has been used at least once (stage >= 2),
            # re-entering paint mode is a correction on the existing track,
            # not a fresh selection -- stay in stage 2 rather than resetting
            # to stage 1. Deliberately checks workflow_stage rather than
            # object_tracker.is_tracking: if CSRT loses the subject mid-clip
            # (a real, separate failure mode on long/dynamic footage), the
            # user is still correcting an existing track, not starting over.
            self._set_workflow_stage(2 if self.workflow_stage >= 2 else 1)
        else:
            self.clear_target_prompts()

    def _push_prompt_history_snapshot(self):
        """Sprint 36: snapshot the full prompt list before an edit (add/
        delete/toggle) -- see the undo/redo stack comment in __init__ for
        why this replaced the old append/pop-only mechanism. Also bumps
        _prompt_edit_seq, a monotonic counter used to de-duplicate
        refinement-progress recording (see _record_refinement_progress);
        unlike prompt count, it never revisits a prior value even when an
        edit (e.g. a delete) makes the count go back down.
        """
        import copy
        self._prompt_undo_stack.append(copy.deepcopy(self._interactive_prompts))
        self._prompt_redo_stack.clear()
        self._prompt_edit_seq += 1

    def _add_prompt_entry(self, entry: dict) -> dict:
        import time
        self._prompt_id_counter += 1
        entry['id'] = self._prompt_id_counter
        entry['order'] = len(self._interactive_prompts)
        entry['timestamp'] = time.time()
        entry['enabled'] = True
        self._interactive_prompts.append(entry)
        return entry

    def _notify_prompt_list_changed(self):
        if self.on_prompt_list_changed:
            self.on_prompt_list_changed()

    def set_target_object(self, prompt: dict):
        if not self.video.is_loaded:
            return

        if self.ai_mode != "sam":
            self.set_ai_mode("sam")

        # A completed stroke is the authoritative "this is a correction"
        # signal (unlike the Select Target toggle, which may already be
        # checked from before Apply Target and so may not fire again here).
        # Any new prompt while reviewing/removing background means the
        # previous track is being revised -- back to stage 2 until the user
        # explicitly re-applies and re-confirms Remove Background.
        if self.workflow_stage >= 2:
            self._set_workflow_stage(2)

        fw, fh = self.video.decoder.width, self.video.decoder.height

        def clamp_pt(pt):
            return [max(0, min(int(pt[0]), fw - 1)), max(0, min(int(pt[1]), fh - 1))]

        ptype = prompt.get('type')
        if ptype == 'stroke':
            clamped_points = [clamp_pt(pt) for pt in prompt['data']]
            if not clamped_points:
                return
            entry = {'type': 'stroke', 'data': clamped_points, 'label': prompt.get('label', 1)}
        elif ptype == 'point':
            # Sprint 35: a single click/correction point -- was previously
            # unhandled here (only the plural 'points' batch form was),
            # silently dropping the prompt with no error. _flatten_prompts_
            # to_points already expects this exact singular form, so this
            # closes a real gap rather than adding a new prompt shape.
            entry = {'type': 'point', 'data': clamp_pt(prompt['data']), 'label': prompt.get('label', 1)}
        elif ptype == 'rectangle':
            r = prompt['data']
            x1, y1 = clamp_pt((r[0], r[1]))
            x2, y2 = clamp_pt((r[2], r[3]))
            entry = {'type': 'rectangle', 'data': [x1, y1, x2, y2], 'label': prompt.get('label', 1)}
        elif ptype == 'points':
            # Multiple points batched under one call -- each still gets
            # its own history entry (id/order/timestamp) since the Prompt
            # List needs to select/toggle/delete them individually, but
            # they're one undo step together (matches the single mouse
            # action that produced them).
            points = prompt['data']
            if not points:
                return
            self._push_prompt_history_snapshot()
            for pt in points:
                self._add_prompt_entry({'type': 'point', 'data': clamp_pt(pt), 'label': prompt.get('label', 1)})
            self._regenerate_interactive_mask()
            self._notify_prompt_list_changed()
            return
        else:
            return

        self._push_prompt_history_snapshot()
        self._add_prompt_entry(entry)
        self._regenerate_interactive_mask()
        self._notify_prompt_list_changed()

    def toggle_prompt_enabled(self, prompt_id: int):
        """Sprint 36: enable/disable a prompt without deleting it -- SAM
        only ever sees enabled prompts (see _dispatch_regenerate), so this
        is a cheap way to test "what if this stroke wasn't here" without
        losing it."""
        for p in self._interactive_prompts:
            if p.get('id') == prompt_id:
                self._push_prompt_history_snapshot()
                p['enabled'] = not p.get('enabled', True)
                self._regenerate_interactive_mask()
                self._notify_prompt_list_changed()
                return

    def delete_prompt(self, prompt_id: int):
        """Sprint 36: remove one prompt out of the list -- unlike the old
        undo (which could only remove the most recently added one), this
        can remove any prompt, from any position, without discarding the
        rest of the selection."""
        idx = next((i for i, p in enumerate(self._interactive_prompts) if p.get('id') == prompt_id), None)
        if idx is None:
            return
        self._push_prompt_history_snapshot()
        self._interactive_prompts.pop(idx)
        self._regenerate_interactive_mask()
        self._notify_prompt_list_changed()

    def undo_target_prompt(self):
        if not self._prompt_undo_stack:
            return
        import copy
        self._prompt_redo_stack.append(copy.deepcopy(self._interactive_prompts))
        self._interactive_prompts = self._prompt_undo_stack.pop()
        self._prompt_edit_seq += 1
        self._regenerate_interactive_mask()
        self._notify_prompt_list_changed()

    def redo_target_prompt(self):
        if not self._prompt_redo_stack:
            return
        import copy
        self._prompt_undo_stack.append(copy.deepcopy(self._interactive_prompts))
        self._interactive_prompts = self._prompt_redo_stack.pop()
        self._prompt_edit_seq += 1
        self._regenerate_interactive_mask()
        self._notify_prompt_list_changed()

    def clear_target_prompts(self):
        self._interactive_prompts.clear()
        self._prompt_undo_stack.clear()
        self._prompt_redo_stack.clear()
        self._live_stroke_prompt = None
        self._last_interactive_alpha = None
        self._last_confidence_info = None
        self._last_quality_gate = None
        self._quality_gate_history = []
        self._last_refinement_verdict = None
        if self.on_interactive_mask_updated:
            self.on_interactive_mask_updated(None, False)
        if self.on_interactive_points_updated:
            self.on_interactive_points_updated([])
        self._notify_prompt_list_changed()

    def _regenerate_interactive_mask(self):
        """Schedule a regenerate for the committed prompt set (called after
        a stroke/point/rectangle is finalized on mouse release, or after
        any Sprint 36 Prompt List edit -- add/delete/toggle/undo/redo)."""
        self._live_stroke_prompt = None
        if self.on_interactive_points_updated:
            self.on_interactive_points_updated(self._interactive_prompts)

        # Sprint 36: disabling every prompt (or deleting down to zero)
        # must clear the mask exactly like having no prompts at all -- SAM
        # never sees disabled prompts (see _dispatch_regenerate), so
        # there's nothing for it to run on either way.
        if not any(p.get('enabled', True) for p in self._interactive_prompts):
            self._last_interactive_alpha = None
            self._last_confidence_info = None
            self._last_quality_gate = None
            self._quality_gate_history = []
            self._last_refinement_verdict = None
            if self.on_interactive_mask_updated:
                self.on_interactive_mask_updated(None, False)
            return

        # Short debounce -- just enough to let the finished stroke render
        # before dispatching to the background worker.
        self._schedule_regenerate(debounce_ms=10)

    def set_target_object_live(self, prompt: dict):
        """In-progress version of set_target_object: called continuously
        while the user drags a stroke, without touching the committed
        prompt list or the undo/redo stacks -- a pure live preview layered
        on top of whatever is already committed. Debounced so continuous
        dragging doesn't dispatch inference on every mouse-move event."""
        if not self.video.is_loaded or self.ai_mode != "sam":
            return
        self._live_stroke_prompt = prompt
        self._schedule_regenerate(debounce_ms=150)

    def _schedule_regenerate(self, debounce_ms: int):
        from PyQt6.QtCore import QTimer
        if self._live_regenerate_timer is None:
            self._live_regenerate_timer = QTimer()
            self._live_regenerate_timer.setSingleShot(True)
            self._live_regenerate_timer.timeout.connect(self._dispatch_regenerate)
        # Restart the timer on every call -- classic debounce: only the
        # last update within the window actually triggers work.
        self._live_regenerate_timer.start(debounce_ms)

    @staticmethod
    def _flatten_prompts_to_points(prompts):
        """Reduce the raw prompt list (points/rectangles/strokes, original
        coordinates) to a flat list of (x, y, label) for the Sprint 32B
        Developer Debug Overlay 'Prompt Points' layer."""
        flat = []
        for p in prompts:
            label = p.get('label', 1)
            if p['type'] == 'point':
                flat.append((p['data'][0], p['data'][1], label))
            elif p['type'] == 'rectangle':
                x1, y1, x2, y2 = p['data']
                flat.append(((x1 + x2) / 2, (y1 + y2) / 2, label))
            elif p['type'] == 'stroke':
                for pt in p['data']:
                    flat.append((pt[0], pt[1], label))
        return flat

    @staticmethod
    def _evaluate_quality_gate(alpha, prompts_used, frame_shape):
        """Sprint 34: rigorous multi-metric selection quality gate.

        Deliberately separate from (and stricter than) the Sprint 33A live
        green/amber/red feedback shown while the user is still painting --
        this is the "is this actually good enough" check, not the "here's
        what's happening" check. Six metrics, three explicit tiers:
        GOOD / NEEDS_REFINEMENT / FAILED. All thresholds below are
        documented heuristics tuned against this session's real benchmark
        data, not derived from any formal calibration.
        """
        import cv2
        import numpy as np

        h, w = frame_shape[:2]
        frame_area = max(w * h, 1)

        empty = {
            'gate': 'FAILED',
            'largest_component_ratio': 0.0,
            'secondary_component_ratio': 0.0,
            'fragmentation': 0,
            'prompt_overlap': 0.0,
            'mask_area': 0.0,
            'edge_continuity': 0.0,
            'reasons': ['no object detected'],
        }
        if alpha is None or alpha.max() == 0:
            return empty

        binary = (alpha > 127).astype(np.uint8)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        comps = [(i, int(stats[i, cv2.CC_STAT_AREA])) for i in range(1, num_labels)
                 if stats[i, cv2.CC_STAT_AREA] > 100]
        comps.sort(key=lambda t: t[1], reverse=True)
        if not comps:
            empty['reasons'] = ['no significant components (all below noise-floor area)']
            return empty

        total_area = sum(a for _, a in comps)
        largest_idx, largest_area = comps[0]
        largest_component_ratio = largest_area / total_area

        secondary_area = comps[1][1] if len(comps) > 1 else 0
        secondary_component_ratio = (secondary_area / largest_area) if largest_area > 0 else 0.0

        fragmentation = len(comps)
        mask_area = total_area / frame_area

        # Prompt overlap: fraction of the user's actual prompt points
        # (stroke path / click points) that land on the detected mask.
        # Distinct from the existing off-target centroid check -- this asks
        # "did the mask actually cover where the user painted", not just
        # "is the mask's centroid near the prompt's bounding box".
        flat_points = AppController._flatten_prompts_to_points(prompts_used or [])
        if flat_points:
            hits = sum(
                1 for (px, py, _lbl) in flat_points
                if 0 <= int(py) < binary.shape[0] and 0 <= int(px) < binary.shape[1]
                and binary[int(py), int(px)] > 0
            )
            prompt_overlap = hits / len(flat_points)
        else:
            prompt_overlap = 0.0

        # Edge continuity: solidity of the largest component (contour area
        # / convex-hull area). A clean, continuous silhouette fills most of
        # its own hull; a broken/scattered edge leaves the hull mostly
        # empty.
        comp_mask = (labels == largest_idx).astype(np.uint8)
        contours, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        edge_continuity = 0.0
        if contours:
            c = max(contours, key=cv2.contourArea)
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            contour_area = cv2.contourArea(c)
            if hull_area > 0:
                edge_continuity = min(1.0, contour_area / hull_area)

        reasons = []
        # Explicit rule from the sprint brief: two similarly large
        # disconnected regions (e.g. the AI picked up a second object)
        # disqualifies GOOD outright, regardless of the other five metrics.
        if secondary_component_ratio >= 0.3:
            reasons.append(f"secondary region is {secondary_component_ratio*100:.0f}% of the largest -- likely two objects, not one")
        if largest_component_ratio < 0.6:
            reasons.append(f"largest region is only {largest_component_ratio*100:.0f}% of total detected area")
        if fragmentation > 5:
            reasons.append(f"{fragmentation} disconnected regions")
        if prompt_overlap < 0.5:
            reasons.append(f"only {prompt_overlap*100:.0f}% of the prompt landed on the detected mask")
        if mask_area < 0.05:
            reasons.append(f"detected area is only {mask_area*100:.1f}% of the frame")
        if edge_continuity < 0.5:
            reasons.append(f"boundary is broken/scattered (continuity {edge_continuity*100:.0f}%)")

        gate = 'GOOD' if not reasons else 'NEEDS_REFINEMENT'

        return {
            'gate': gate,
            'largest_component_ratio': round(largest_component_ratio, 3),
            'secondary_component_ratio': round(secondary_component_ratio, 3),
            'fragmentation': fragmentation,
            'prompt_overlap': round(prompt_overlap, 3),
            'mask_area': round(mask_area, 4),
            'edge_continuity': round(edge_continuity, 3),
            'reasons': reasons,
        }

    # Metrics where a HIGHER value is better; the rest (secondary_component_
    # ratio, fragmentation) are better LOWER. Used only for the improved/
    # same/regressed comparison below -- does not touch _evaluate_quality_
    # gate's own thresholds or GOOD/NEEDS_REFINEMENT/FAILED logic at all.
    _HIGHER_IS_BETTER = {
        'largest_component_ratio', 'prompt_overlap', 'mask_area', 'edge_continuity',
    }
    _LOWER_IS_BETTER = {'secondary_component_ratio', 'fragmentation'}
    _GATE_RANK = {'FAILED': 0, 'NEEDS_REFINEMENT': 1, 'GOOD': 2}

    @staticmethod
    def _compare_quality_gates(previous: dict, current: dict) -> dict:
        """Sprint 35: does this new prompt make the mask better, the same,
        or worse than the one before it? Pure comparison over the Sprint 34
        quality-gate metrics -- doesn't change how those metrics or the
        GOOD/NEEDS_REFINEMENT/FAILED tiers are computed.

        Primary signal is the gate tier itself (a tier change is decisive);
        within the same tier, whichever of the 6 metrics moved further
        (in the direction that's "better" for that metric) decides it, a
        metric only counts as moved if the change exceeds a small epsilon
        (avoids flip-flopping on floating-point noise).
        """
        if previous is None:
            return {'verdict': None, 'metric_deltas': {}}

        prev_rank = AppController._GATE_RANK.get(previous.get('gate'), 0)
        curr_rank = AppController._GATE_RANK.get(current.get('gate'), 0)

        EPS = 0.02
        deltas = {}
        improved_count = 0
        regressed_count = 0
        for key in AppController._HIGHER_IS_BETTER | AppController._LOWER_IS_BETTER:
            prev_v = previous.get(key)
            curr_v = current.get(key)
            if prev_v is None or curr_v is None:
                continue
            raw_delta = curr_v - prev_v
            deltas[key] = round(raw_delta, 4)
            if abs(raw_delta) < EPS:
                continue
            better_if_higher = key in AppController._HIGHER_IS_BETTER
            moved_up = raw_delta > 0
            if moved_up == better_if_higher:
                improved_count += 1
            else:
                regressed_count += 1

        if curr_rank > prev_rank:
            verdict = 'improved'
        elif curr_rank < prev_rank:
            verdict = 'regressed'
        elif improved_count > regressed_count:
            verdict = 'improved'
        elif regressed_count > improved_count:
            verdict = 'regressed'
        else:
            verdict = 'same'

        return {
            'verdict': verdict,
            'metric_deltas': deltas,
            'improved_count': improved_count,
            'regressed_count': regressed_count,
        }

    def _record_refinement_progress(self, gate: dict, prompts_used) -> None:
        """Sprint 35: append this result to the quality-gate progression IF
        it's the outcome of a committed prompt (mouse released, added to
        _interactive_prompts) rather than a live in-drag preview frame --
        comparing against every ~150ms live-preview tick would just be
        noise, not "first/second/third prompt quality" as the sprint asks
        for. A result is "committed" when the prompt set actually used for
        this inference matches the current *enabled* list (a live preview
        appends one extra in-progress stroke on top of it; Sprint 36
        excludes disabled prompts from what SAM sees, so this must compare
        against enabled count, not raw list length, or every result would
        look uncommitted as soon as any prompt is disabled).

        Sprint 36: de-duplicates on _prompt_edit_seq (a monotonic counter
        bumped once per edit) rather than prompt count -- count alone can
        revisit a prior value after a delete followed by a different add,
        which would wrongly look like "already recorded this" and silently
        drop a real, distinct result.
        """
        enabled_count = sum(1 for p in self._interactive_prompts if p.get('enabled', True))
        is_committed = len(prompts_used or []) == enabled_count
        if not is_committed:
            return

        edit_seq = self._prompt_edit_seq
        if self._quality_gate_history and self._quality_gate_history[-1].get('edit_seq', -1) >= edit_seq:
            return  # already recorded this edit (e.g. a redundant re-run)

        previous_gate = self._quality_gate_history[-1]['gate'] if self._quality_gate_history else None
        comparison = self._compare_quality_gates(previous_gate, gate)

        self._quality_gate_history.append({'edit_seq': edit_seq, 'prompt_count': enabled_count, 'gate': gate, 'comparison': comparison})
        self._last_refinement_verdict = {'prompt_count': enabled_count, **comparison}
        if self.on_refinement_verdict_changed:
            self.on_refinement_verdict_changed(self._last_refinement_verdict)

    def _dispatch_regenerate(self):
        # Sprint 36: SAM only ever sees enabled prompts -- a disabled
        # prompt stays in the Prompt List (and undo history) but is
        # excluded here exactly as if it had been deleted, which is the
        # whole point of "toggle on/off" as distinct from "delete".
        prompts = [p for p in self._interactive_prompts if p.get('enabled', True)]
        if self._live_stroke_prompt is not None:
            prompts.append(self._live_stroke_prompt)
        if not prompts:
            return

        timeline_frame = self.timeline_playback.current_timeline_frame
        position = self.timeline_playback.seek(timeline_frame)
        if position is None:
            return

        frame = self.video.get_frame(position.source_frame)
        if frame is None:
            error_msg = f"Failed to retrieve frame {position.source_frame} for interactive mask generation."
            print(error_msg)
            if self.on_error_occurred:
                self.on_error_occurred(error_msg)
            return

        processor = getattr(self, '_background_removal_processor', None)
        if not processor or not hasattr(processor, '_session') or processor._session is None:
            return

        if self.on_debug_prompt_points_updated:
            self.on_debug_prompt_points_updated(self._flatten_prompts_to_points(prompts))

        self._interactive_busy = True
        if self.on_interactive_busy_changed:
            self.on_interactive_busy_changed(True)
        self._interactive_worker.request(processor, frame, prompts)

    def _on_interactive_mask_ready(self, alpha, prompts_used):
        self._interactive_busy = False
        if self.on_interactive_busy_changed:
            self.on_interactive_busy_changed(False)

        if alpha is None:
            error_msg = "Failed to extract SAM mask."
            print(error_msg)
            if self.on_error_occurred:
                self.on_error_occurred(error_msg)
            return

        self._last_interactive_alpha = alpha
        print(f"SAM Output -> Mask shape: {alpha.shape}, Min: {alpha.min()}, Max: {alpha.max()}")

        frame_h, frame_w = alpha.shape[:2]
        frame_area = max(frame_w * frame_h, 1)

        # Sprint 33A: RED -- no usable object detected at all. Was previously
        # routed through on_error_occurred -> a blocking QMessageBox --
        # disruptive on its own, and especially bad now that live refinement
        # can fire this every ~150ms while the user is still mid-drag.
        # Routes through the same non-blocking status-bar mechanism used for
        # the other states so the user always gets a clear, visible reason
        # instead of either a frozen dialog or silence ("do not silently
        # fail").
        if alpha.max() == 0:
            msg = "No object detected. Try a different stroke, or add more points."
            print(msg)
            self._last_confidence_info = {
                'state': 'red', 'confidence_pct': 0, 'area_fraction': 0.0,
                'bbox_w': 0, 'bbox_h': 0, 'components': 0,
            }
            self._last_quality_gate = self._evaluate_quality_gate(alpha, prompts_used, alpha.shape)
            self._record_refinement_progress(self._last_quality_gate, prompts_used)
            if getattr(self, 'on_tracking_status_changed', None):
                self.on_tracking_status_changed(msg)
            if self.on_interactive_mask_updated:
                self.on_interactive_mask_updated(None, False)
            return

        # Sprint 30: Confidence check -- fragmented mask (many disconnected
        # components) usually means the prompt under-specifies the object.
        import cv2
        import numpy as np
        binary = (alpha > 127).astype(np.uint8)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
        valid_components = sum(1 for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] > 100)
        is_fragmented = valid_components > 5

        # B3 (Magic Mask roadmap): fragmentation count alone misses a
        # failure mode this session's benchmark suite showed is at least as
        # common -- a clean, low-fragment mask that nonetheless lands on the
        # wrong object entirely (e.g. a nearby object SAM picked instead of
        # the intended one). Flag low confidence if the mask's dominant
        # region isn't anywhere near where the user actually prompted.
        is_off_target = False
        if num_labels > 1:
            areas = [(i, stats[i, cv2.CC_STAT_AREA]) for i in range(1, num_labels)]
            largest_idx, _ = max(areas, key=lambda t: t[1])
            cx, cy = centroids[largest_idx]
            region = _prompt_bounding_region(prompts_used or [])
            if region is not None:
                rx1, ry1, rx2, ry2 = region
                rw, rh = max(rx2 - rx1, 1.0), max(ry2 - ry1, 1.0)
                pad_x = max(rw, 40.0)
                pad_y = max(rh, 40.0)
                if not (rx1 - pad_x <= cx <= rx2 + pad_x and ry1 - pad_y <= cy <= ry2 + pad_y):
                    is_off_target = True

        # Sprint 33A: total detected area vs. the frame, as a practical
        # stand-in for "relative to the expected subject size" -- there's no
        # ground-truth subject size available at inference time, so frame
        # coverage is the closest measurable proxy. A single stroke that
        # only lights up a sliver of the frame reads to users as "broken"
        # when it's really "the AI found part of the object" -- name that
        # explicitly instead of leaving it as an unexplained amber blob.
        area_px = int(binary.sum())
        area_fraction = area_px / frame_area
        is_small_region = area_fraction < 0.05

        ys, xs = np.where(binary > 0)
        bbox_w = int(xs.max() - xs.min() + 1) if len(xs) else 0
        bbox_h = int(ys.max() - ys.min() + 1) if len(ys) else 0

        is_low_confidence = is_fragmented or is_off_target or is_small_region

        # Confidence percentage: an explainable heuristic composite for
        # on-screen feedback, not a calibrated probability -- starts at 100
        # and docks points per failure signal, scaled by how far past each
        # threshold it is. Floors at 5 (not 0) here since some object was
        # found at all -- true 0 is reserved for the RED/no-object case above.
        confidence_pct = 100
        if is_fragmented:
            confidence_pct -= min(50, (valid_components - 5) * 8 + 20)
        if is_off_target:
            confidence_pct -= 40
        if is_small_region:
            confidence_pct -= min(40, int((0.05 - area_fraction) / 0.05 * 40) + 10)
        confidence_pct = max(5, min(100, confidence_pct))

        state = 'amber' if is_low_confidence else 'green'
        self._last_confidence_info = {
            'state': state,
            'confidence_pct': confidence_pct,
            'area_fraction': area_fraction,
            'bbox_w': bbox_w, 'bbox_h': bbox_h,
            'components': valid_components,
        }

        # Sprint 34: the rigorous quality gate, computed alongside (not
        # instead of) the above -- deliberately separate and stricter, so a
        # result can read 'green' here (Sprint 33A's live feedback) while
        # still landing NEEDS_REFINEMENT on the gate (e.g. two similarly
        # large disconnected regions, which the simpler check above doesn't
        # catch on its own).
        self._last_quality_gate = self._evaluate_quality_gate(alpha, prompts_used, alpha.shape)
        self._record_refinement_progress(self._last_quality_gate, prompts_used)

        if is_low_confidence:
            detail = " Only part of the object was detected." if is_small_region else ""
            msg = f"Partial object detected.{detail} Try: Add Keep (+), Add Remove (-), or zoom closer."
            print(msg)
            if getattr(self, 'on_tracking_status_changed', None):
                self.on_tracking_status_changed(msg)

        verdict = self._last_refinement_verdict
        if verdict and verdict.get('prompt_count', 0) > 1 and verdict.get('verdict'):
            v = verdict['verdict']
            label = {'improved': 'Improved', 'same': 'Stayed the same', 'regressed': 'Regressed'}[v]
            print(f"Refinement (prompt #{verdict['prompt_count']}): {label} "
                  f"({verdict['improved_count']} metrics up, {verdict['regressed_count']} down)")
            if getattr(self, 'on_tracking_status_changed', None):
                self.on_tracking_status_changed(f"Refinement: {label} vs. previous prompt")

        if self.on_interactive_mask_updated:
            self.on_interactive_mask_updated(alpha, is_low_confidence)
                
    def apply_target(self):
        if getattr(self, '_last_interactive_alpha', None) is None:
            return
        if getattr(self, '_interactive_busy', False):
            # A newer regenerate is still in flight -- _last_interactive_alpha
            # would be stale. The UI disables the Apply button for this same
            # window; this is a defensive guard against races/bypasses.
            return


        timeline_frame = self.timeline_playback.current_timeline_frame
        position = self.timeline_playback.seek(timeline_frame)
        if position is None:
            return
            
        frame = self.video.get_frame(position.source_frame)
        if frame is None:
            error_msg = f"Failed to retrieve frame {position.source_frame} for applying target."
            print(error_msg)
            if self.on_error_occurred:
                self.on_error_occurred(error_msg)
            return
            
        import cv2
        import numpy as np
        if frame.shape[2] == 4:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        else:
            frame_bgr = frame
            
        alpha = self._last_interactive_alpha
        contours, _ = cv2.findContours(alpha, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Extract points
            pos_pts = []
            neg_pts = []
            for p in self._interactive_prompts:
                if p['type'] == 'point':
                    x_p, y_p = p['data']
                    if p.get('label', 1) == 1:
                        pos_pts.append((x_p, y_p))
                    else:
                        neg_pts.append((x_p, y_p))
                elif p['type'] == 'stroke':
                    # Same density-based sampling used for the live SAM prompt
                    # (ai.background_removal_processor.sample_stroke_points),
                    # so the points carried forward for tracking match what
                    # produced the mask the user just confirmed.
                    from ai.background_removal_processor import sample_stroke_points
                    pts = p['data']
                    if len(pts) > 0:
                        for pt in sample_stroke_points(pts):
                            if p.get('label', 1) == 1:
                                pos_pts.append((pt[0], pt[1]))
                            else:
                                neg_pts.append((pt[0], pt[1]))
            
            prompt_data = {
                'type': 'rectangle', 
                'data': (x, y, w, h), 
                'label': 1,
                'positive_points': pos_pts,
                'negative_points': neg_pts
            }
            self.object_tracker.init_tracker(frame_bgr, prompt_data, frame_number=position.source_frame)

            if self._background_removal_processor:
                self._background_removal_processor.sam_prompt = self.object_tracker.get_sam_prompt()

            # Start background tracking for the rest of the clip. This is
            # also the correction path: applying a new stroke mid-review
            # (Stage 2) re-initializes the tracker at whatever frame the
            # user is currently on and re-tracks forward from there --
            # tracking_cache is keyed per-frame, so this only overwrites
            # the corrected range and leaves earlier frames untouched.
            pos = self.timeline_playback.position_at(timeline_frame)
            if pos and pos.clip:
                if self.tracking_engine.isRunning():
                    self.tracking_engine.stop()
                self.tracking_engine.start_tracking(pos.source_frame, pos.clip.end_frame)

            self.render_cache.invalidate_from(timeline_frame)
            self.clear_target_prompts()
            if self.on_tracker_initialized:
                self.on_tracker_initialized()

            # Stage 2 (Track Object) -- background removal is a separate,
            # explicit Stage 3 action the user takes after reviewing the
            # track, not an automatic follow-on to Apply Target.
            self._set_workflow_stage(2)

    def _process_frame(self, frame):
        """Sends playback frames to the AI pipeline after activation."""
        if self.is_background_removal_active:
            timeline_frame = self.timeline_playback.current_timeline_frame
            if self.render_cache.has_frame(timeline_frame):
                return

            pos = self.timeline_playback.position_at(timeline_frame)
            if pos:
                prompt = self.tracking_engine.get_tracked_prompt(pos.source_frame)
                if self._background_removal_processor:
                    self._background_removal_processor.sam_prompt = prompt
                
            self.frames_sent_to_processing += 1
            self.processing.enqueue_frame(frame)


    def increase_forward_speed(self):
        """Cycle forward speed: 1x → 2x → 4x."""
        self.timeline_playback.increase_forward_speed()

    def increase_reverse_speed(self):
        """Cycle reverse speed: -1x → -2x → -4x."""
        self.timeline_playback.increase_reverse_speed()

    def reset_playback_speed(self):
        """Reset to 1x forward."""
        self.timeline_playback.reset_playback_speed()

    # ------------------------------------------------------------------
    # Blade mode
    # ------------------------------------------------------------------

    def toggle_blade_mode(self) -> bool:
        """Toggle blade mode on/off. Returns the new state."""
        self._blade_mode = not self._blade_mode
        return self._blade_mode

    def split_at_position(self, timeline_frame: int) -> bool:
        """
        Split any clip covering *timeline_frame*.
        Returns True if a split was performed.
        """
        clip = self.project.timeline.clip_at_timeline_frame(timeline_frame)
        if clip is None:
            return False

        return self._timeline_command(
            lambda: self.project.timeline.split_clip(clip, timeline_frame)
        )

    # ------------------------------------------------------------------
    # Clip selection / editing
    # ------------------------------------------------------------------

    def selected_clip(self):
        return self.project.timeline.get_selected_clip()

    def select_clip(self, clip):
        return self.project.timeline.select_clip(clip)

    def begin_timeline_edit(self):
        if self._edit_snapshot is None:
            self._edit_snapshot = self.project.timeline.snapshot()

    def end_timeline_edit(self):
        if self._edit_snapshot is None:
            return False

        before = self._edit_snapshot
        self._edit_snapshot = None
        return self.history.record(before, self.project.timeline.snapshot())

    def _timeline_command(self, action):
        if self._edit_snapshot is not None:
            result = action()
        else:
            result = self.history.execute(self.project.timeline, action)
        
        # Refresh the current preview to prevent stale frames after edits
        self.preview_seek(self.timeline_playback.current_timeline_frame)
        
        return result

    def move_clip(self, clip, timeline_start_frame):
        return self._timeline_command(
            lambda: self.project.timeline.move_clip(clip, timeline_start_frame)
        )

    def trim_clip(self, clip, edge, timeline_frame):
        if edge == "start":
            return self._timeline_command(
                lambda: self.project.timeline.trim_clip_start(clip, timeline_frame)
            )
        if edge == "end":
            return self._timeline_command(
                lambda: self.project.timeline.trim_clip_end(clip, timeline_frame)
            )
        return False

    def split_selected_clip_at_playhead(self):
        clip = self.selected_clip()
        if clip is None:
            return False

        return self._timeline_command(
            lambda: self.project.timeline.split_clip(
                clip,
                self.timeline_playback.current_timeline_frame,
            )
        )

    def delete_selected_clip(self):
        return self._timeline_command(
            self.project.timeline.delete_selected_clip
        )

    def toggle_link_selected_clip(self):
        """Link/unlink the selected clip with its matching clip on another
        track. Missing entirely until now -- ui/main_window.py's
        toggle_link_timeline_clip() called this method on the controller,
        but only core/timeline.py ever defined it, crashing the app on use."""
        return self._timeline_command(
            self.project.timeline.toggle_link_selected_clip
        )

    def undo_timeline(self):
        return self.history.undo(self.project.timeline)

    def redo_timeline(self):
        return self.history.redo(self.project.timeline)

    def release(self):
        self.timeline_playback.release()
        self.video.release()
        self.processing.stop()
        self._interactive_worker.stop()
        self.tracking_engine.stop()
        self.render_cache.release()