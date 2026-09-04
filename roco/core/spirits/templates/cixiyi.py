"""石化刺蜥蜴 template."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

CIXIYI = SpiritTemplate(
    id="cixiyi",
    name="石化刺蜥蜴",
    description="石化刺蜥蜴",
    base_stats=BaseStats(hp=550, atk=100, mag_atk=100, def_=150, mag_def=150, speed=120),
    passive_skill=PassiveSkillDef(
        id="cixiyi_passive",
        name="硬化肌肤 / 再生",
        description=(
            "【硬化肌肤】受到的固定伤害降低50%。"
            "【再生】自身受到伤害后，提升自身20%双防，并减少「棘皮」技能2点能耗，"
            "持续1回合，期间再次获得会延长1回合，最多持续2回合。"
        ),
    ),
    normal_attack=SkillDef(
        id="cixiyi_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="cixiyi_skill1",
            name="棘皮",
            description=(
                "能量 3。目标为全体己方精灵。给予所有目标「棘皮」正面效果："
                "受到伤害后，移除此效果并获得施加者给予的（30%施加者物防）护盾，持续3回合，"
                "以这种方式再次获得护盾时可累积护盾量并刷新持续时间，上限为（60%施加者物防）。"
                "若目标已拥有「棘皮」效果则不再给予。"
            ),
            cooldown=0,
            target_type=TargetType.all_allies,
            energy_cost=3,
        ),
        SkillDef(
            id="cixiyi_skill2",
            name="岩刺",
            description=(
                "能量 1。目标为一个敌方精灵。对自身造成（20%自身物攻）物理伤害，"
                "然后对目标造成（120%自身物防 + 100%自身护盾量）物理伤害。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=1,
            launches_attack=True,
        ),
    ],
)
