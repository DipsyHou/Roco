# Battle core architecture

This document is the map for `roco.core.battle`. The code is intentionally split
into small modules, but the public entry point remains one object:

```python
from roco.core.battle.engine import BattleEngine
```

`BattleEngine` owns the mutable `BattleState` and wires the battle subsystems
together. Other battle modules should either be pure helpers or operate through
that engine instance.

## Layer overview

```text
roco/core/battle/
  engine.py                 BattleEngine composition and initial state setup
  types.py / enums.py        data structures and enums
  rules.py                  constants and rule limits

  action_submission.py       submit_action lifecycle and transaction/rollback
  turn_pipeline.py           turn begin / action / turn end hook order
  action_executor.py         concrete action effects: attack, skill, gather, skip
  lifecycle.py               defeat notifications and battle-end checks

  timeline.py                pure action-value math helpers
  timeline_controller.py     stateful timeline controller used by BattleEngine
  timeline_api.py            BattleEngine timeline-facing API/mixin

  context_api.py             API exposed to spirit logic: logs, lookup, damage hooks
  energy.py                  team-energy accounting implementation
  energy_facade.py           BattleEngine energy-facing API/mixin
  extra_action.py            extra-action data and policy definitions
  extra_action_queue.py      queue operations for inserted extra actions
```

## Main action flow

A normal player action starts at `BattleEngine.submit_action`, implemented by
`ActionSubmissionMixin`:

```text
BattleEngine.submit_action(player_id, action)
  -> reject if battle is not waiting for action
  -> locate and validate the active actor
  -> handle non-consuming preview actions, if any
  -> if resolving an extra-action slot:
       TurnPipeline.resolve_inserted_extra_action(...)
       pop/advance the extra-action queue
       resume the suspended normal turn if the queue is empty
  -> otherwise:
       ensure_active_turn_begun()
       take_snapshot()
       TurnPipeline.resolve_turn(...)
       check battle end
       if extra actions were queued:
           suspend normal turn end and activate first extra slot
       else:
           finish normal turn
```

`action_submission.py` is deliberately the orchestration layer. It should not
contain skill-specific damage or spirit-specific rules.

## Turn pipeline responsibilities

`TurnPipeline` defines the timing of battle hooks:

```text
begin_turn(actor)
  -> stun/block check
  -> actor.on_turn_start
  -> allies.on_ally_turn_start

resolve_turn(actor, action)
  -> execute action or log stun
  -> actor.on_action_end
  -> end_turn unless deferred

end_turn(actor, action)
  -> actor.on_turn_end
  -> allies.on_ally_turn_end
  -> tick/expire effects
  -> process system effects on action end
  -> after_actor_acts timeline hook
  -> passive checks
```

Inserted extra actions are different from normal turns: they execute a single
action through `resolve_inserted_extra_action` and do **not** trigger normal turn
start/end timing or advance the timeline by themselves.

## Concrete action execution

`ActionExecutor` resolves the effect of an already accepted action:

- normal attack
- skill use
- team-energy gather
- skip
- attack-launch notifications
- skill-target resolution
- calling spirit logic for skill effects

It should not decide whose turn it is, whether a turn should end, or how the
timeline advances. Those decisions belong to `action_submission.py`,
`turn_pipeline.py`, and the timeline modules.

## Timeline responsibilities

Timeline code is split into three roles:

- `timeline.py`: pure action-value math. It should not import `BattleEngine`.
- `timeline_controller.py`: stateful controller that reads/writes spirit charge.
- `timeline_api.py`: methods exposed on `BattleEngine`, such as
  `advance_action`, `delay_action`, and `ensure_active_turn_begun`.

The controller answers "who acts next" and updates charge. Turn hook ordering
stays outside the controller.

## Context and spirit-facing API

Spirit logic should interact with battle state through `BattleEngine` methods
from `context_api.py`, `timeline_api.py`, and `energy_facade.py` instead of
reaching into controllers directly.

Common spirit-facing operations include:

- `find_spirit`, `find_spirit_anywhere`
- `get_active_spirits`, `get_all_spirits`
- `add_log`
- `execute_normal_attack`
- `notify_damage_taken`
- `advance_action`, `delay_action`
- `gain_team_energy`, `sync_team_energy_cap`
- `queue_extra_actions`

## Dependency direction rules

Keep these rules when changing battle code:

1. `engine.py` may compose subsystems.
2. Pure helpers like `timeline.py`, `damage.py`, and `rules.py` should not import
   `BattleEngine`.
3. Controllers/managers may hold a `BattleEngine` reference, but should keep a
   narrow responsibility.
4. `*_api.py` and `*_facade.py` mixins expose engine capabilities; they should
   not become hidden orchestration layers.
5. Spirit-specific behavior belongs in `roco.core.spirits`, not in generic battle
   modules, unless it is a reusable core rule.

## Where to start when debugging

- Action rejected or rollback? Start with `action_submission.py`.
- Hook order / turn start / turn end issue? Start with `turn_pipeline.py`.
- Skill or attack result wrong? Start with `action_executor.py`, then the spirit
  logic file.
- Actor order or timeline preview wrong? Start with `timeline_controller.py`,
  then `timeline.py`.
- Energy cost/gain wrong? Start with `energy.py` and `energy_facade.py`.
- Extra action chain wrong? Start with `extra_action_queue.py`, then
  `action_submission.py`.
