"""Centralized battle rules/constants used by engine orchestration."""

from __future__ import annotations

MIN_TEAM_SIZE = 1
MAX_TEAM_SIZE = 5
TEAM_ENERGY_MAX = 10
TEAM_ENERGY_CAP_MAX = 15
TEAM_GATHER_ENERGY_GAIN = 3

# Upper bound on consecutive auto-skips when advancing past dead actors.
# One pass should clear at most every spirit on the field (2 * MAX_TEAM_SIZE);
# the extra headroom absorbs extra-action slots queued during those skips.
# Purely a runaway-loop backstop — hitting it means a scheduling bug, not
# normal play.
MAX_DEAD_ACTOR_SKIPS = 2 * MAX_TEAM_SIZE + 4

