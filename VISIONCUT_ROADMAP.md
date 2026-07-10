# VisionCut AI

## Vision

A lightweight DaVinci Resolve with AI-first tools.

VisionCut AI is a professional, non-destructive video editor built for creators who want the speed of AI without sacrificing manual control.

---

# Development Principles

- Professional architecture
- Non-destructive editing
- AI assists the editor
- Track-based timeline
- GPU accelerated
- Modular codebase
- One feature per sprint
- One complete file replacement for core widgets
- Test after every sprint
- Git commit after every sprint

---

# Version Roadmap

## v0.1 Alpha

### Core
- [x] Project
- [x] Asset Manager
- [x] Timeline
- [x] Track
- [x] Clip
- [x] Transform

### Playback
- [x] Viewer
- [x] Timeline
- [x] Playback Controls

### Import
- [x] Project Importer

### AI
- [x] Background Removal Engine (ProcessingEngine + rembg processor; verify GPU vs CPU via `controller.ai_device_label`)

### Cleanup & Reconciliation Sprint (completed)
- [x] Removed duplicate/orphaned timeline implementations
- [x] Removed dead legacy `gui.py` entry point
- [x] Fixed VideoReader file-handle leak in ProjectImporter
- [x] Fixed requirements.txt encoding (UTF-16 -> UTF-8), added AI deps
- [x] Preserved TimelineClip scaffold (reserved for Sprint 10+), removed only its unused import

---

## Timeline System - Architecture

## Timeline Feature Sprints

### Sprint 9 - Functional core (completed)
- [x] Playhead follows playback (auto-scroll keeps it visible in viewport)
- [x] Clicking the ruler seeks the video
- [x] Ruler seconds now computed from real video fps (was hardcoded to 30, wrong on 50/59.94fps footage)

### Sprint 10 - Clip selection (next)
- [ ] Click a clip -> selected (yellow border)
- [ ] TimelineClip scaffold becomes active here

### Sprint 11 - Clip dragging
- [ ] Drag clips left/right along the track

### Sprint 12 - Trim handles
- [ ] Trim clip start/end edges

### Sprint 13 - Multiple tracks
- [ ] Video 2, Audio 1 track support

---

## UI Polish Backlog (tracked, intentionally deferred)

- [ ] Ruler tick spacing refinement (currently fixed 100px steps regardless of zoom)
- [ ] Track header alignment with ruler/track rows (header is 120px/60px; canvas ruler+track offsets don't currently match pixel-for-pixel)
- [ ] Long clip names truncated with ellipsis
- [ ] Shorter track rows to fit more tracks on screen

---

## v0.2

- Inspector
- Drag Clips
- Split Tool
- Audio Tracks
- Export

---

## v0.3

- Timeline Zoom
- Ripple Editing
- Speed Ramp
- Keyframes

---

## v0.4

- Color
- LUT
- Proxy
- Cache

---

## v1.0

Professional AI Video Editor

# Architecture

Project
    |
    +-- Media Pool
    +-- Timeline
    |      +-- Video Tracks
    |      +-- Audio Tracks
    |      +-- Playhead
    |      +-- Selection
    |
    +-- Viewer
    +-- Inspector
    +-- AI Engine
    +-- Export
