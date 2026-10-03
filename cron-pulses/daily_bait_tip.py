#!/usr/bin/env python3
"""Print a generic draft fishing tip for optional content workflows."""

import os
import random


TIPS = [
    "Try varying retrieve speed and note which pace gets follows.",
    "Check water clarity before selecting natural or high-visibility lure colors.",
    "After a cold front, test slower retrieves and deeper structure.",
    "At the end of a retrieve, keep the lure moving near the boat and watch for follows.",
    "Keep a log of conditions, lure choice, and observed strikes.",
]


if __name__ == "__main__":
    print(os.environ.get("CONTENT_BRAND", "Fishing tip of the day"))
    print(random.choice(TIPS))
    print(os.environ.get("CONTENT_TAGS", "#fishing #fishingtips"))
