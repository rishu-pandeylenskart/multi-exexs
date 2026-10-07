"""Small, dependency-free time helpers used by the UI."""
from __future__ import annotations

import time
from datetime import datetime


def greeting(hour: int) -> str:
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    return "Good evening"


def relative_time(ts: float | None, now: float | None = None) -> str:
    """'Just now', '5 minutes ago', 'Today, 14:32', 'Yesterday', '3 days ago'..."""
    if not ts:
        return ""
    now = time.time() if now is None else now
    delta = now - ts
    if delta < 0:
        delta = 0
    if delta < 60:
        return "Just now"
    if delta < 3600:
        minutes = int(delta // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    then = datetime.fromtimestamp(ts)
    today = datetime.fromtimestamp(now).date()
    days = (today - then.date()).days
    if days <= 0:
        return f"Today, {then:%H:%M}"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return f"{then.day} {then:%b %Y}"
