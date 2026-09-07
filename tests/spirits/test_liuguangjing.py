from __future__ import annotations

from tests.conftest import P1, P2, by_template, cast_skill, normal_attack, submit
from roco.core.battle.types import ActionType, DamageType, EffectType
from roco.core.battle.effect_display import format_spirit_effects
from roco.core.battle.utils import calculate_damage, make_effect
from roco.core.spirits.liuguangjing import (
    add_mirror_energy,
    get_mirror_damage,
    get_mirror_energy,
)
from roco.core.spirits.xiaozong import add_lingqi, get_lingqi_stacks


def test_mirror_records_before_lingjue(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("xiaozong", "qiuka", "fanying", "tita", "cuiding"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    flora = by_template(engine, P1, "flora")
    xz = by_template(engine, P2, "xiaozong")
    add_lingqi(xz, 50)
    xz.base_stats.def_ = 100
    flora.base_stats.atk = 100

    before_lingqi = get_lingqi_stacks(xz)
    dmg = calculate_damage(100, DamageType.physical, flora, xz)
    assert dmg == 95
    assert get_lingqi_stacks(xz) == before_lingqi + 5
    assert get_mirror_damage(mirror) == 100


def test_self_damage_grants_mirror(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    enemy = by_template(engine, P2, "qiuka")
    engine.state.active_actor_id = mirror.unique_id
    engine.state.turn_prepared_actor_id = mirror.unique_id
    assert normal_attack(engine, mirror, enemy)
    assert get_mirror_damage(mirror) > 0


def test_poison_does_not_grant_mirror(engine_factory):
    from roco.core.battle.dot import trigger_poison_damage
    from roco.core.battle.effects import apply_poison_stacks

    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    flora = by_template(engine, P1, "flora")
    enemy = by_template(engine, P2, "qiuka")
    apply_poison_stacks(enemy, flora.unique_id, 5)
    trigger_poison_damage(engine, enemy)
    assert get_mirror_damage(mirror) == 0


def test_ally_energy_spend_and_gain_grant_mirror_energy(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    flora = by_template(engine, P1, "flora")
    engine.state.players[P1].team_energy = 10
    engine.state.active_actor_id = flora.unique_id
    engine.state.turn_prepared_actor_id = flora.unique_id

    assert cast_skill(engine, flora, "flora_skill2", mirror)  # cost 2
    assert get_mirror_energy(mirror) == 2

    engine.state.players[P1].team_energy = 0
    engine.state.active_actor_id = flora.unique_id
    engine.state.turn_prepared_actor_id = flora.unique_id
    assert submit(engine, flora, ActionType.gather_energy.value)
    assert get_mirror_energy(mirror) == 4  # +2 from ally gather


def test_self_energy_gain_grants_mirror_energy(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    engine.state.players[P1].team_energy = 0
    engine.state.active_actor_id = mirror.unique_id
    engine.state.turn_prepared_actor_id = mirror.unique_id
    assert submit(engine, mirror, ActionType.gather_energy.value)
    assert get_mirror_energy(mirror) == 2


def test_spend_converts_mirror_energy_once(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    flora = by_template(engine, P1, "flora")
    add_mirror_energy(mirror, 12)
    engine.state.players[P1].team_energy = 10
    engine.state.players[P1].max_team_energy = 10
    engine.state.active_actor_id = flora.unique_id
    engine.state.turn_prepared_actor_id = flora.unique_id

    assert cast_skill(engine, flora, "flora_skill2", mirror)  # cost 2
    # 耗能 +2 映像 → 14；流转兑一次 −6 +1 队伍能量且 +1 映像 → 9
    assert engine.state.players[P1].team_energy == 9  # 10 - 2 + 1
    assert get_mirror_energy(mirror) == 9


def test_flow_does_not_chain_on_bonus_gain(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    flora = by_template(engine, P1, "flora")
    add_mirror_energy(mirror, 18)
    engine.state.players[P1].team_energy = 10
    engine.state.players[P1].max_team_energy = 10
    engine.state.active_actor_id = flora.unique_id
    engine.state.turn_prepared_actor_id = flora.unique_id

    assert cast_skill(engine, flora, "flora_skill2", mirror)
    # 仅兑 1 次：18+2-6+1=15，能量 10-2+1=9（不会用剩余映像再兑）
    assert engine.state.players[P1].team_energy == 9
    assert get_mirror_energy(mirror) == 15


def test_flow_skips_when_energy_full(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    add_mirror_energy(mirror, 30)
    engine.state.players[P1].team_energy = 10
    engine.state.players[P1].max_team_energy = 10

    # 满能回能：队伍不变，但仍计入映像能量
    engine.gain_team_energy(P1, 1, source=mirror)
    assert engine.state.players[P1].team_energy == 10
    assert get_mirror_energy(mirror) == 31


def test_tita_shunt_overflow_grants_mirror_energy(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "tita", "flora", "clawdragon", "chaosling"),
        ("qiuka", "fanying", "cuiding", "guifashi", "steamdragon"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    tita = by_template(engine, P1, "tita")
    flora = by_template(engine, P1, "flora")

    engine.state.active_actor_id = tita.unique_id
    engine.state.turn_prepared_actor_id = tita.unique_id
    engine.state.players[P1].team_energy = 12  # 扩容上限
    assert cast_skill(engine, tita, "tita_skill1")  # 分流；耗 5 → 映像 +5，可能流转

    # 清空映像后只测分流溢出；能量打满
    mirror.effects = [
        e for e in mirror.effects if e.type != EffectType.state_mirror_energy
    ]
    engine.state.players[P1].team_energy = engine.state.players[P1].max_team_energy
    engine.state.players[P1].team_energy_spent_tracker = 0  # 避免缓冲再回能

    before = get_mirror_energy(mirror)
    engine.state.active_actor_id = flora.unique_id
    engine.state.turn_prepared_actor_id = flora.unique_id
    assert submit(engine, flora, ActionType.skip.value)

    assert engine.state.players[P1].team_energy == engine.state.players[P1].max_team_energy
    assert get_mirror_energy(mirror) == before + 1


def test_yinyang_threshold_includes_exactly_half(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    engine.state.players[P1].team_energy = 5
    engine.state.players[P1].max_team_energy = 10
    engine.state.active_actor_id = mirror.unique_id
    engine.state.turn_prepared_actor_id = mirror.unique_id
    assert cast_skill(engine, mirror, "liuguangjing_skill1")
    assert engine.state.players[P1].team_energy == 7
    assert get_mirror_energy(mirror) == 2  # 自身回能计入


def test_mirror_pour_six_percent_and_halve(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    enemy = by_template(engine, P2, "qiuka")
    mirror.effects.append(
        make_effect(
            EffectType.state_mirror_damage,
            mirror.unique_id,
            stacks=200,
            display_name="映像伤害",
        )
    )
    assert get_mirror_damage(mirror) == 200
    assert format_spirit_effects(
        [e for e in mirror.effects if e.type == EffectType.state_mirror_damage], {}
    ) == ["[state]映像伤害: 200"]

    engine.state.active_actor_id = mirror.unique_id
    engine.state.turn_prepared_actor_id = mirror.unique_id
    engine.state.players[P1].team_energy = 10
    before_hp = enemy.current_hp
    adjacents = engine.get_adjacent_enemies(enemy)
    assert cast_skill(engine, mirror, "liuguangjing_skill2", enemy)
    assert before_hp - enemy.current_hp == 12  # 6% of 200
    # 自身伤害记账后再半额：200 + 12*(1+相邻数)
    recorded = 200 + 12 * (1 + len(adjacents))
    assert get_mirror_damage(mirror) == recorded // 2


def test_gather_advances_timeline(engine_factory):
    engine = engine_factory(
        ("liuguangjing", "flora", "clawdragon", "chaosling", "steamdragon"),
        ("qiuka", "fanying", "tita", "cuiding", "guifashi"),
    )
    mirror = by_template(engine, P1, "liuguangjing")
    engine.state.active_actor_id = mirror.unique_id
    engine.state.turn_prepared_actor_id = mirror.unique_id
    before = mirror.charge
    assert submit(engine, mirror, ActionType.gather_energy.value)
    assert mirror.charge <= before
