"""格鲁姆 template."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

GULUM = SpiritTemplate(
    id="gulum",
    name="格鲁姆",
    description="格鲁姆",
    base_stats=BaseStats(hp=800, atk=100, mag_atk=120, def_=110, mag_def=110, speed=100),
    passive_skill=PassiveSkillDef(
        id="gulum_passive",
        name="养分输送",
        description=(
            "队友受到伤害时，若自身生命值比例高于50%，则为该队友回复（2%自身最大生命值）点生命值；"
            "否则为自己回复（2%自身最大生命值）点生命值。"
        ),
    ),
    normal_attack=SkillDef(
        id="gulum_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="gulum_skill1",
            name="寄生种子",
            description="目标为一个敌方精灵。赋予目标4层「寄生」效果。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=1,
        ),
        SkillDef(
            id="gulum_skill2",
            name="深根",
            description=(
                "目标为自身。获得「深根」，持续3回合，期间再次使用此技能会重置「深根」持续时间。"
                "（深根：速度降低40%，队友受到伤害时自身分摊50%的伤害量。）"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=4,
        ),
        SkillDef(
            id="gulum_skill3",
            name="紧缠",
            description="目标为全体敌方精灵。赋予全体目标2层「寄生」效果，然后触发所有目标的「寄生」效果。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=3,
        ),
    ],
)
