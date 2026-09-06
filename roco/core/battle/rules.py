"""Centralized battle rules/constants used by engine orchestration."""

from __future__ import annotations

MIN_TEAM_SIZE = 1
TEAM_ENERGY_MAX = 10
TEAM_ENERGY_CAP_MAX = 15
TEAM_GATHER_ENERGY_GAIN = 3

# Upper bound on consecutive auto-skips when advancing past dead actors.
# Purely a runaway-loop backstop — hitting it means a scheduling bug, not
# normal play. Sized for very large teams without enforcing a roster cap.
MAX_DEAD_ACTOR_SKIPS = 256
