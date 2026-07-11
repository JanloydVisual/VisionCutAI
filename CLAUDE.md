# VisionCut AI - Claude Instructions

## Project

VisionCut AI is an AI-powered desktop video editor.

Main goal:
Create an intelligent video editing assistant that helps creators produce cinematic and high-retention videos.

Target users:
- Real estate marketers
- Content creators
- Brands
- Social media editors


## Development Philosophy

Foundation first.

Do not add AI features before the editor foundation is stable.

Priority:
1. Editor core
2. Media pipeline
3. Editing tools
4. Export system
5. AI editing assistant


## Architecture Rules

UI never controls core logic.

Flow:

UI
 |
Controller
 |
Core Engine
 |
AI Modules


Important systems:

Project
- owns timeline
- owns assets

Timeline
- owns tracks

Track
- owns clips

Clip
- represents media on timeline


## Current Progress

Completed:

- Playback engine
- Video loading
- Frame seeking
- Timeline
- Clip selection
- Clip dragging
- Viewer controls
- Processing pipeline
- Background removal integration
- Video importer
- Audio track foundation


Current focus:

Audio system foundation.

Next:
- Audio import
- Audio playback
- Waveform
- Trim tools
- Export


## Coding Rules

- Keep architecture clean.
- Avoid duplicate systems.
- Test after changes.
- Preserve working features.
- Make small commits.
