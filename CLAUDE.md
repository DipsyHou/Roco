# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the local hot-seat battle game
python -m roco

# Install as editable (no external dependencies — pure stdlib)
pip install -e .
```

No build step, no linter configured, no test suite (the `tests/` directory referenced in README does not exist yet).

## Architecture

This is a Python port of a TypeScript turn-based spirit battle game. The original had a WebSocket server/client architecture; this version retains the **game engine + data model** but currently only has a **local hot-seat CLI** (`roco/local_game.py`). Networked play (server, client, room manager) is referenced in the README but the source files have been removed or not yet ported.

### Data model (`roco/battle_types.py`)

All enums and dataclasses live here — this is the schema. `BattleSpirit`, `BattleEffect`, `BattleState`, `SpiritTemplate`, etc. JSON-friendly naming conventions (camelCase for serialized fields). The `player_action_from_dict()` helper normalizes client payloads (snake_case or camelCase) into the engine's expected shape.

### Engine (`roco/engine.py` + `roco/battle_utils.py`)

`BattleEngine` implements the `BattleContext` protocol (defined in `spirit_logic.py`). Key flow:
1. Both players select starters → `select_starters()`
2. Each turn, both submit actions → `submit_action()`
3. When both submitted, `_execute_turn()` sorts actions by effective speed, executes them sequentially, runs end-of-turn processing (effect ticks, cooldown ticks, passive triggers)
4. Battle ends when all spirits of one player are defeated

`battle_utils.py` contains the damage formula (`calculate_damage`), stat calculation (base × (1 + Σpercent) + Σflat), effect lifecycle (`tick_effects`, `consume_next_damage_reduction`, `purge_debuffs`).

### Spirit system (`roco/spirits/`)

- **`templates.py`** — static data: 4 spirits (Flora, Clawdragon, Chaosling, Starweaver) with base stats, skill definitions, and passive descriptions. These are pure data, no logic.
- **`{spirit}.py`** — per-spirit `SpiritLogic` subclass implementing skill execution and passive hooks.
- **`registry.py`** — maps `template_id` → `SpiritLogic` singleton.
- **`spirit_logic.py`** — `BattleContext` protocol + `SpiritLogic` base class with hook methods: `on_init`, `execute_skill`, `on_after_skill`, `on_after_normal_attack`, `check_passive`, `on_end_of_turn`.

To add a new spirit: define a `SpiritTemplate` in `templates.py`, create a `SpiritLogic` subclass, and register it in `registry.py`.

### Key design details

- **Starweaver uses energy** instead of cooldowns. The engine has special-case branches for `template_id == "starweaver"` in `_validate_action()` and `_execute_skill()`. Energy is checked/consumed there; skill CD is skipped.
- **Clawdragon's passive** (auto-attack after skill) is triggered via `on_after_skill` hook, which calls `ctx.execute_normal_attack()` with `is_auto_triggered=True`. Auto-triggered attacks skip stun checks and attack-enhance consumables.
- **Chaosling's channeling** (rage buildup) uses `EffectType.channeling_skill` with phase tracking — phases advance in `on_end_of_turn`, effects clear on withdraw/swap.
- **Flora's passive** is one-shot per battle (`passive_triggered` flag on the spirit).
- **`remaining_turns: -1`** means permanent until explicitly removed (e.g., on withdraw/swap). `999` means effectively permanent (Chaosling's random stat modifications).
- The engine clears `stun`/`aoe` attack-enhance effects and `channeling_skill` effects when a spirit withdraws or swaps.
