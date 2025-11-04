"""Utility functions for event classification and processing."""

import re
from enum import Enum


class EventType(str, Enum):
    """Event type classification."""

    PPV = "ppv"
    FIGHT_NIGHT = "fight_night"
    UFC_ON_ESPN = "ufc_on_espn"
    UFC_ON_ABC = "ufc_on_abc"
    TUF_FINALE = "tuf_finale"
    CONTENDER_SERIES = "contender_series"
    OTHER = "other"


def detect_event_type(event_name: str) -> EventType:
    """
    Detect event type from event name.

    PPV events are numbered UFC events (UFC 300, UFC 323, etc.)
    Fight Night events contain "Fight Night"
    Special events include TUF Finale, Contender Series, etc.

    Args:
        event_name: The name of the event

    Returns:
        EventType enum value
    """
    name_lower = event_name.lower()

    # PPV: UFC followed by a number (UFC 300, UFC 323)
    if re.match(r"^ufc\s+\d+:", name_lower):
        return EventType.PPV

    # Fight Night
    if "fight night" in name_lower:
        return EventType.FIGHT_NIGHT

    # UFC on ESPN
    if "ufc on espn" in name_lower or "espn" in name_lower:
        return EventType.UFC_ON_ESPN

    # UFC on ABC
    if "ufc on abc" in name_lower or "abc" in name_lower:
        return EventType.UFC_ON_ABC

    # TUF Finale
    if "tuf" in name_lower and "finale" in name_lower:
        return EventType.TUF_FINALE

    # Contender Series
    if "contender series" in name_lower or "dwcs" in name_lower:
        return EventType.CONTENDER_SERIES

    return EventType.OTHER


def get_event_type_label(event_type: EventType) -> str:
    """Get human-readable label for event type."""
    labels = {
        EventType.PPV: "PPV",
        EventType.FIGHT_NIGHT: "Fight Night",
        EventType.UFC_ON_ESPN: "UFC on ESPN",
        EventType.UFC_ON_ABC: "UFC on ABC",
        EventType.TUF_FINALE: "TUF Finale",
        EventType.CONTENDER_SERIES: "Contender Series",
        EventType.OTHER: "Other",
    }
    return labels.get(event_type, "Other")


def is_ppv_event(event_name: str) -> bool:
    """Quick check if event is a PPV."""
    return detect_event_type(event_name) == EventType.PPV
