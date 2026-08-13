from __future__ import annotations

from tests.conftest import P1, by_template, submit
from roco.core.battle.types import ActionType, EffectType
from roco.core.spirits.guifashi_cards import CardState, TAROT_CARDS, card_label


def _ready_guifashi(engine, guifashi, hand):  # noqa: ANN001
    guifashi.card_state = CardState(deck=["moon", "star", "fool"], hand=list(hand)).to_dict()
    engine.state.active_actor_id = guifashi.unique_id
    engine.state.turn_prepared_actor_id = guifashi.unique_id


def test_battle_start_initializes_tarot_deck(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    state = CardState.from_dict(guifashi.card_state)

    assert sorted(state.deck) == sorted(TAROT_CARDS)
    assert state.hand == []


def test_draw_skill_grants_extra_action_without_ending_turn(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    _ready_guifashi(engine, guifashi, [])
    action_count = engine.state.action_count
    charge = guifashi.charge

    assert submit(engine, guifashi, ActionType.use_skill.value, skillId="guifashi_draw")

    slot = engine.current_extra_slot()
    assert slot is not None
    assert slot.actor_id == guifashi.unique_id
    assert slot.policy_id == "guifashi_chain"
    assert engine.state.active_actor_id == guifashi.unique_id
    assert engine.state.action_count == action_count
    assert guifashi.charge == charge
    assert CardState.from_dict(guifashi.card_state).hand


def test_sun_card_adds_one_turn_damage_buff(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    _ready_guifashi(engine, guifashi, ["sun"])

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
    )

    effect = next(e for e in guifashi.effects if e.type == EffectType.buff_damage_percent_boost)
    assert effect.duration_turns == 1
    assert effect.value == 0.24


def test_moon_card_advances_next_turn_and_sets_next_turn_energy(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    _ready_guifashi(engine, guifashi, ["moon"])
    charge_before = guifashi.charge

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
    )

    state = CardState.from_dict(guifashi.card_state)
    assert guifashi.charge == charge_before - 2400
    assert state.pending_moon_energy


def test_moon_card_does_not_stack_while_pending(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    _ready_guifashi(engine, guifashi, ["moon", "moon"])
    charge_before = guifashi.charge

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
    )
    charge_after_first = guifashi.charge
    assert CardState.from_dict(guifashi.card_state).pending_moon_energy

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
    )

    assert guifashi.charge == charge_after_first
    assert CardState.from_dict(guifashi.card_state).pending_moon_energy


def test_demon_show_consumes_other_hand_cards_after_shown_card_removed(engine_factory):
    engine = engine_factory(("guifashi", "flora", "clawdragon", "chaosling", "starweaver"))
    guifashi = by_template(engine, P1, "guifashi")
    _ready_guifashi(engine, guifashi, ["demon", "judgment"])

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
        consumeHandIndices=[1],
    )

    state = CardState.from_dict(guifashi.card_state)
    assert "judgment" in state.consumed
    assert state.hand
    assert not any("行动执行时发生了异常" in e.message for e in engine.state.battle_log)


def test_show_judgment_launches_attack_for_resonance(engine_factory):
    from tests.conftest import P2

    engine = engine_factory(
        ("guifashi", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    guifashi = by_template(engine, P1, "guifashi")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    _ready_guifashi(engine, guifashi, ["judgment"])
    star.energy = 3

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
        targetId=enemy.unique_id,
    )

    assert star.energy == 2
    assert sum(1 for e in engine.state.battle_log if "共振" in e.message) == 1


def test_show_death_launches_attack_once_for_resonance(engine_factory):
    engine = engine_factory(
        ("guifashi", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    guifashi = by_template(engine, P1, "guifashi")
    star = by_template(engine, P1, "starweaver")
    _ready_guifashi(engine, guifashi, ["death"])
    star.energy = 4

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
    )

    assert star.energy == 3
    assert sum(1 for e in engine.state.battle_log if "共振" in e.message) == 1


def test_show_temperance_does_not_launch_attack(engine_factory):
    from tests.conftest import P2

    engine = engine_factory(
        ("guifashi", "starweaver", "flora", "chaosling", "tita"),
        ("clawdragon", "flora", "chaosling", "tita", "fanying"),
    )
    guifashi = by_template(engine, P1, "guifashi")
    star = by_template(engine, P1, "starweaver")
    enemy = by_template(engine, P2, "clawdragon")
    _ready_guifashi(engine, guifashi, ["temperance"])
    star.energy = 4

    assert submit(
        engine,
        guifashi,
        ActionType.use_skill.value,
        skillId="guifashi_show",
        cardHandIndex=0,
        targetId=enemy.unique_id,
    )

    assert star.energy == 4
    assert not any("共振" in e.message for e in engine.state.battle_log)


def test_card_labels_cover_every_tarot_card():
    assert all(card_label(card_id) != card_id for card_id in TAROT_CARDS)
