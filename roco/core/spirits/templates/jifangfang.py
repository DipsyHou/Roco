"""机械方方 template."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

JIFANGFANG = SpiritTemplate(
    id="jifangfang",
    name="机械方方",
    description="机械方方",
    base_stats=BaseStats(hp=650, atk=130, mag_atk=100, def_=130, mag_def=100, speed=130),
    passive_skill=PassiveSkillDef(
        id="jifangfang_passive",
        name="多色模块",
        description=(
            "游戏开始时获得「强化模块」。使用技能后，若自身拥有强化 / 急速 / 抵御模块之一，"
            "则移除并获得下一个（强化→急速→抵御→强化）。"
            "（强化模块：拥有自身提供护盾的目标造成的伤害提高12%。"
            "急速模块：拥有自身提供护盾的目标速度提高6%。"
            "抵御模块：拥有自身提供护盾的目标受到的伤害降低12%。）"
        ),
    ),
    normal_attack=SkillDef(
        id="jifangfang_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="jifangfang_skill1",
            name="防火墙",
            description=(
                "能量 4。目标为全体己方精灵。赋予所有目标（90%自身物攻）护盾，持续3回合，"
                "持续期间再次获得自身赋予的护盾会累积护盾量并刷新持续时间，上限为（120%施加者物攻）。"
            ),
            cooldown=0,
            target_type=TargetType.all_allies,
            energy_cost=4,
        ),
        SkillDef(
            id="jifangfang_skill2",
            name="便携防火墙",
            description=(
                "能量 0。目标为一个己方精灵。赋予目标（30%自身物攻）护盾，持续3回合，"
                "持续期间再次获得自身赋予的护盾会累积护盾量并刷新持续时间，上限为（120%施加者物攻）。"
            ),
            cooldown=0,
            target_type=TargetType.single_ally,
            energy_cost=0,
        ),
        SkillDef(
            id="jifangfang_skill3",
            name="超限模块",
            description=(
                "能量 3。目标为自身。获得「超限模块」状态效果，持续4回合。"
                "拥有「超限模块」时，同时获得强化、急速与抵御模块的效果。"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
    ],
)
