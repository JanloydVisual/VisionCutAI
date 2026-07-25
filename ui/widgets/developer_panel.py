import logging
import psutil
import subprocess
import html
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QCheckBox
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

class QTextEditLogger(logging.Handler, QObject):
    appendHtml = pyqtSignal(str)
    def __init__(self, parent):
        super().__init__()
        QObject.__init__(self)
        self.widget = QTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setStyleSheet("background-color: #1e1e1e; font-family: Consolas; font-size: 11px;")
        self.appendHtml.connect(self.widget.append)
        
    def emit(self, record):
        msg = self.format(record)
        safe_msg = html.escape(msg)
        
        color = "#d4d4d4"
        if record.levelno >= logging.ERROR:
            color = "#ff5555" # Red
        elif record.levelno >= logging.WARNING:
            color = "#f1fa8c" # Yellow
        elif record.levelno >= logging.INFO:
            color = "#50fa7b" # Green
            
        html_msg = f'<span style="color: {color};">{safe_msg}</span>'
        self.appendHtml.emit(html_msg)

class DeveloperPanel(QDockWidget):
    def __init__(self, controller, parent=None):
        super().__init__("Developer Panel", parent)
        self.controller = controller
        
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Compact Developer Status Bar
        status_bar = QHBoxLayout()
        status_bar.setSpacing(10)
        
        self.lbl_fps = QLabel("FPS: 0")
        self.lbl_cpu = QLabel("CPU: 0%")
        self.lbl_gpu = QLabel("GPU: 0%")
        self.lbl_vram = QLabel("VRAM: 0 MB")
        self.lbl_queue = QLabel("AI Queue: 0")
        self.lbl_cache = QLabel("Cache: 0")
        self.lbl_tracking = QLabel("Tracking: Idle")
        self.lbl_confidence = QLabel("Prompt Confidence: -")

        for lbl in [self.lbl_fps, self.lbl_cache, self.lbl_queue, self.lbl_cpu, self.lbl_gpu, self.lbl_vram, self.lbl_tracking, self.lbl_confidence]:
            lbl.setStyleSheet("font-weight: bold; color: #5dade2; font-size: 11px;")
            status_bar.addWidget(lbl)
            
        status_bar.addStretch()
        layout.addLayout(status_bar)

        # Sprint 34: Selection Quality Gate -- every metric feeding the
        # GOOD / NEEDS_REFINEMENT / FAILED classification, on its own row
        # since six metrics plus the verdict is too much for the compact
        # status bar above without crowding it (same lesson as the
        # playback-controls row split earlier this session).
        quality_bar = QHBoxLayout()
        quality_bar.setSpacing(10)

        self.lbl_gate = QLabel("Quality Gate: -")
        self.lbl_gate_largest = QLabel("Largest: -")
        self.lbl_gate_secondary = QLabel("Secondary: -")
        self.lbl_gate_fragmentation = QLabel("Fragments: -")
        self.lbl_gate_overlap = QLabel("Overlap: -")
        self.lbl_gate_area = QLabel("Area: -")
        self.lbl_gate_edge = QLabel("Edge: -")

        self._gate_metric_labels = [
            self.lbl_gate_largest, self.lbl_gate_secondary, self.lbl_gate_fragmentation,
            self.lbl_gate_overlap, self.lbl_gate_area, self.lbl_gate_edge,
        ]
        for lbl in self._gate_metric_labels:
            lbl.setStyleSheet("font-size: 11px; color: #d4d4d4;")
            quality_bar.addWidget(lbl)

        self.lbl_gate.setStyleSheet("font-weight: bold; font-size: 11px; color: #5dade2;")
        quality_bar.insertWidget(0, self.lbl_gate)
        quality_bar.addStretch()
        layout.addLayout(quality_bar)

        # Sprint 35: Iterative Mask Refinement -- whether the most recent
        # committed Keep(+)/Remove(-) prompt made the mask better, the
        # same, or worse than the prompt before it, plus the full
        # prompt-by-prompt quality progression for this selection.
        refine_bar = QHBoxLayout()
        refine_bar.setSpacing(10)
        self.lbl_refinement = QLabel("Refinement: -")
        self.lbl_refinement.setStyleSheet("font-weight: bold; font-size: 11px; color: #5dade2;")
        self.lbl_refinement_history = QLabel("History: -")
        self.lbl_refinement_history.setStyleSheet("font-size: 11px; color: #d4d4d4;")
        refine_bar.addWidget(self.lbl_refinement)
        refine_bar.addWidget(self.lbl_refinement_history)
        refine_bar.addStretch()
        layout.addLayout(refine_bar)

        # Sprint 32B: temporary Developer Debug Overlay -- toggle each stage
        # of the interactive segmentation pipeline independently to see
        # exactly where it breaks down.
        debug_bar = QHBoxLayout()
        debug_bar.setSpacing(10)
        debug_bar.addWidget(QLabel("Debug Overlay:"))

        self.chk_debug_points = QCheckBox("Prompt Points")
        self.chk_debug_raw_mask = QCheckBox("Raw Mask")
        self.chk_debug_cleaned_mask = QCheckBox("Cleaned Mask")
        self.chk_debug_final_overlay = QCheckBox("Final Overlay")
        self.chk_debug_final_overlay.setChecked(True)

        for chk in [self.chk_debug_points, self.chk_debug_raw_mask, self.chk_debug_cleaned_mask, self.chk_debug_final_overlay]:
            chk.setStyleSheet("color: #d4d4d4; font-size: 11px;")
            debug_bar.addWidget(chk)
        debug_bar.addStretch()
        layout.addLayout(debug_bar)

        # Setup Logging Console
        self.log_handler = QTextEditLogger(container)
        self.log_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logging.getLogger().addHandler(self.log_handler)
        
        layout.addWidget(self.log_handler.widget)
        self.setWidget(container)
        
        # Timer for polling metrics
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_telemetry)
        self.timer.start(1000)
        
    def update_telemetry(self):
        # FPS
        if hasattr(self.controller, 'video') and self.controller.video:
            fps = getattr(self.controller.video, 'fps', 0)
            self.lbl_fps.setText(f"FPS: {fps:.1f}")

        # CPU & RAM (Skipping RAM for space if needed, but we can keep CPU)
        cpu = psutil.cpu_percent()
        self.lbl_cpu.setText(f"CPU: {cpu}%")
        
        # GPU & VRAM
        try:
            res = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                encoding="utf-8", stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW
            ).strip()
            if res:
                parts = res.split(",")
                if len(parts) >= 2:
                    self.lbl_gpu.setText(f"GPU: {parts[0].strip()}%")
                    self.lbl_vram.setText(f"VRAM: {parts[1].strip()} MB")
        except Exception:
            self.lbl_gpu.setText("GPU: N/A")
            self.lbl_vram.setText("VRAM: N/A")
            
        # Pipeline State
        if hasattr(self.controller, 'processing') and self.controller.processing:
            try:
                qsize = self.controller.processing._queue.qsize()
                self.lbl_queue.setText(f"AI Queue: {qsize}")
            except:
                pass
            
        if hasattr(self.controller, 'render_cache') and self.controller.render_cache:
            try:
                frames = list(self.controller.render_cache.cache_dir.glob("*.png"))
                self.lbl_cache.setText(f"Cache: {len(frames)}")
            except Exception:
                pass
                
        if hasattr(self.controller, 'tracking_engine') and self.controller.tracking_engine:
            state = "Active" if self.controller.tracking_engine._is_running else "Idle"
            self.lbl_tracking.setText(f"Tracking: {state}")

        # Sprint 33A: full confidence-state readout for the last interactive
        # mask -- confidence %, detected area, bounding box size, and
        # connected-component count, so a developer (or a curious user) can
        # see exactly why a result landed in GREEN/AMBER/RED without
        # guessing.
        info = getattr(self.controller, '_last_confidence_info', None)
        if info is not None:
            state = info['state']
            area_pct = info['area_fraction'] * 100
            self.lbl_confidence.setText(
                f"Confidence: {info['confidence_pct']}% ({state.upper()})  |  "
                f"Area: {area_pct:.1f}%  |  "
                f"BBox: {info['bbox_w']}x{info['bbox_h']}px  |  "
                f"Regions: {info['components']}"
            )
            color = {"green": "#4CAF50", "amber": "#FFB300", "red": "#F44336"}[state]
            self.lbl_confidence.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {color};")

        # Sprint 34: Selection Quality Gate -- all six metrics plus the
        # GOOD / NEEDS_REFINEMENT / FAILED verdict, so the reasoning behind
        # the classification is fully visible, not just the verdict itself.
        gate_info = getattr(self.controller, '_last_quality_gate', None)
        if gate_info is not None:
            gate = gate_info['gate']
            self.lbl_gate.setText(f"Quality Gate: {gate}")
            gate_color = {"GOOD": "#4CAF50", "NEEDS_REFINEMENT": "#FFB300", "FAILED": "#F44336"}[gate]
            self.lbl_gate.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {gate_color};")

            self.lbl_gate_largest.setText(f"Largest: {gate_info['largest_component_ratio']*100:.0f}%")
            self.lbl_gate_secondary.setText(f"Secondary: {gate_info['secondary_component_ratio']*100:.0f}%")
            self.lbl_gate_fragmentation.setText(f"Fragments: {gate_info['fragmentation']}")
            self.lbl_gate_overlap.setText(f"Overlap: {gate_info['prompt_overlap']*100:.0f}%")
            self.lbl_gate_area.setText(f"Area: {gate_info['mask_area']*100:.1f}%")
            self.lbl_gate_edge.setText(f"Edge: {gate_info['edge_continuity']*100:.0f}%")

            # Flag the two metrics most likely to be the actual culprit
            # (secondary-region and edge-continuity) so they're visible at
            # a glance, not just buried in a uniform grey row.
            self.lbl_gate_secondary.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #FFB300;"
                if gate_info['secondary_component_ratio'] >= 0.3 else "font-size: 11px; color: #d4d4d4;"
            )
            self.lbl_gate_edge.setStyleSheet(
                "font-size: 11px; font-weight: bold; color: #FFB300;"
                if gate_info['edge_continuity'] < 0.5 else "font-size: 11px; color: #d4d4d4;"
            )

        # Sprint 35: refinement verdict for the most recent committed
        # prompt, plus the full per-prompt quality-gate progression for
        # this selection (e.g. "1:NEEDS_REFINEMENT -> 2:GOOD -> 3:GOOD").
        verdict = getattr(self.controller, '_last_refinement_verdict', None)
        if verdict is not None and verdict.get('verdict'):
            v = verdict['verdict']
            label = {'improved': 'Improved', 'same': 'Stayed the same', 'regressed': 'Regressed'}[v]
            self.lbl_refinement.setText(
                f"Refinement (prompt #{verdict['prompt_count']}): {label} "
                f"({verdict['improved_count']}up/{verdict['regressed_count']}down)"
            )
            v_color = {"improved": "#4CAF50", "same": "#5dade2", "regressed": "#F44336"}[v]
            self.lbl_refinement.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {v_color};")
        elif getattr(self.controller, '_quality_gate_history', None):
            self.lbl_refinement.setText("Refinement: prompt #1 (baseline, nothing to compare yet)")
            self.lbl_refinement.setStyleSheet("font-weight: bold; font-size: 11px; color: #5dade2;")
        else:
            self.lbl_refinement.setText("Refinement: -")
            self.lbl_refinement.setStyleSheet("font-weight: bold; font-size: 11px; color: #5dade2;")

        history = getattr(self.controller, '_quality_gate_history', None)
        if history:
            chain = " -> ".join(f"{h['prompt_count']}:{h['gate']['gate']}" for h in history)
            self.lbl_refinement_history.setText(f"History: {chain}")
        else:
            self.lbl_refinement_history.setText("History: -")
