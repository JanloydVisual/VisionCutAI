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
- [x] Background Removal Engine

### Current Sprint
- [ ] Clip Selection

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
    ¦
    +-- Media Pool
    +-- Timeline
    ¦      +-- Video Tracks
    ¦      +-- Audio Tracks
    ¦      +-- Playhead
    ¦      +-- Selection
    ¦
    +-- Viewer
    +-- Inspector
    +-- AI Engine
    +-- Export

