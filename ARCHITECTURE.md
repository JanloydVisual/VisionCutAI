# VisionCut AI Architecture

## Structure

Project
 |
 +-- Assets
 |
 +-- Timeline
       |
       +-- Video Tracks
       |
       +-- Audio Tracks
       |
       +-- Clips


## Core Systems

VideoEngine
- playback
- seeking
- frame control


ProcessingEngine
- background removal
- AI processing


Timeline
- editing structure


Importers
- video importer
- audio importer


## Rules

UI communicates through Controller.

Core systems should not depend on UI.

Keep modules replaceable.
