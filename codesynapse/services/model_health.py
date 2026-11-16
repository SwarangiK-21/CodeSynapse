"""Remembers which Gemini models are struggling, so later requests try a healthy one first.

Without this, every request starts with the first configured model. When that model is
overloaded, each of an analysis's many calls waits for it to time out before falling back.
A struggling model rests at the back of the order for a while instead. It is still tried
as a last resort, so requests never fail just because every model is resting.

State lives in this process, like the rate limits; that suits the single-server deployment.
"""
import threading
import time

# How long a model rests after timing out or reporting overload
SLOW_SECONDS = 5 * 60
# How long it rests after using up its daily quota
EXHAUSTED_SECONDS = 60 * 60

_resting_until = {}
_lock = threading.Lock()

def ordered(models):
    """Healthy models in their configured order, then resting ones, soonest to recover first."""
    now = time.monotonic()
    with _lock:
        resting = {m: t for m, t in _resting_until.items() if t > now}
    healthy = [m for m in models if m not in resting]
    return healthy + sorted((m for m in models if m in resting), key=resting.get)

def mark_slow(model, seconds=SLOW_SECONDS):
    with _lock:
        _resting_until[model] = time.monotonic() + seconds

def mark_ok(model):
    with _lock:
        _resting_until.pop(model, None)

def reset():
    with _lock:
        _resting_until.clear()
