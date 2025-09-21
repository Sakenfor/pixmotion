"""Default qualitative scale definitions contributed by the core plugin."""
from __future__ import annotations

from typing import List, Dict, Any


DEFAULT_QUALITATIVE_SCALES: List[Dict[str, Any]] = [
    {
        "id": "core.trust",
        "label": "Trust",
        "default_descriptor": "neutral",
        "bounds": [0, 100],
        "metadata": {
            "description": "Baseline trust scale used for relationship edges.",
        },
        "descriptors": [
            {
                "name": "ice_cold",
                "aliases": ["hostile", "frosty"],
                "range": [0, 15],
                "jitter": 2,
                "metadata": {
                    "label": "Ice Cold",
                    "description": "Actively distrustful; expects the worst.",
                },
            },
            {
                "name": "wary",
                "range": [15, 35],
                "jitter": 3,
                "metadata": {
                    "label": "Wary",
                    "description": "Guarded but willing to keep engaging.",
                },
            },
            {
                "name": "neutral",
                "aliases": ["steady"],
                "range": [35, 55],
                "jitter": 4,
                "metadata": {
                    "label": "Neutral",
                    "description": "Baseline trust without major history.",
                },
            },
            {
                "name": "open",
                "range": [55, 75],
                "jitter": 4,
                "metadata": {
                    "label": "Open",
                    "description": "Comfortable sharing plans and thoughts.",
                },
            },
            {
                "name": "bonded",
                "aliases": ["loyal"],
                "range": [75, 90],
                "jitter": 3,
                "metadata": {
                    "label": "Bonded",
                    "description": "Reliable partner with long term goodwill.",
                },
            },
            {
                "name": "ride_or_die",
                "aliases": ["unshakable"],
                "range": [90, 100],
                "jitter": 2,
                "metadata": {
                    "label": "Ride or Die",
                    "description": "Absolute loyalty; would take major risks.",
                },
            },
        ],
    },
    {
        "id": "core.arousal",
        "label": "Arousal",
        "default_descriptor": "calm",
        "bounds": [0, 100],
        "metadata": {
            "description": "Baseline arousal meter for chemistry scenes.",
        },
        "descriptors": [
            {
                "name": "flat",
                "aliases": ["cooldown"],
                "range": [0, 10],
                "jitter": 1,
                "metadata": {
                    "label": "Flat",
                    "description": "No spark; uninterested right now.",
                },
            },
            {
                "name": "calm",
                "range": [10, 35],
                "jitter": 3,
                "metadata": {
                    "label": "Calm",
                    "description": "Relaxed baseline state.",
                },
            },
            {
                "name": "curious",
                "range": [35, 60],
                "jitter": 4,
                "metadata": {
                    "label": "Curious",
                    "description": "Open to playful advances.",
                },
            },
            {
                "name": "flirty",
                "aliases": ["spark"],
                "range": [60, 80],
                "jitter": 5,
                "metadata": {
                    "label": "Flirty",
                    "description": "Actively engaged and teasing.",
                },
            },
            {
                "name": "charged",
                "aliases": ["heated"],
                "range": [80, 95],
                "jitter": 4,
                "metadata": {
                    "label": "Charged",
                    "description": "High energy pull; decisions escalate quickly.",
                },
            },
            {
                "name": "overdrive",
                "range": [95, 100],
                "jitter": 2,
                "metadata": {
                    "label": "Overdrive",
                    "description": "Barely restrained; outcomes may spill over.",
                },
            },
        ],
    },
]
