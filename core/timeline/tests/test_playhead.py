import pytest
from core.timeline.playhead import Playhead

def test_playhead_initialization():
    ph = Playhead()
    assert ph.current_frame == 0
    assert ph.fps == 30.0
    assert ph.is_playing is False

def test_playhead_custom_fps():
    ph = Playhead(fps=60.0)
    assert ph.fps == 60.0

def test_invalid_fps():
    with pytest.raises(ValueError):
        Playhead(fps=0)
    with pytest.raises(ValueError):
        Playhead(fps=-10.0)

def test_seek():
    ph = Playhead()
    ph.seek(100)
    assert ph.current_frame == 100
    
def test_seek_negative():
    ph = Playhead()
    ph.seek(-50)
    assert ph.current_frame == 0

def test_advance():
    ph = Playhead()
    ph.advance(10)
    assert ph.current_frame == 10
    ph.advance(5)
    assert ph.current_frame == 15

def test_advance_negative():
    ph = Playhead()
    ph.seek(20)
    ph.advance(-5)
    assert ph.current_frame == 15
    ph.advance(-30)
    assert ph.current_frame == 0

def test_time_conversion():
    ph = Playhead(fps=30.0)
    ph.seek(30)
    assert ph.get_time() == 1.0
    ph.seek(45)
    assert ph.get_time() == 1.5
