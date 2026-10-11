"""南陆朱雀 static template."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    DamageType,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)


NANLUZHUQUE = SpiritTemplate(
    id="nanluzhuque",
    name="南陆朱雀",
    description="以天火引燃持续伤害的火属性输出精灵。",
    base_stats=BaseStats(hp=550, attack=140, defense=120, speed=140),
    elements=(DamageType.fire,),
    passive_skill=PassiveSkillDef(
        id="nanluzhuque_passive",
        name="天火·鹑火伏辰",
        description=(
            "天火造成基于攻击与层数的特殊火属性持续伤害，触发后层数减半。"
            "普通持续伤害会额外触发天火；燔祭目标受到持续伤害或负面效果时追加天火。"
        ),
    ),
    normal_attack=SkillDef(
        id="nanluzhuque_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（50%自身攻击）点火属性伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="nanluzhuque_skill1",
            name="燔祭",
            description=(
                "对全体敌方施加3回合燔祭与15层天火。燔祭使受到伤害提高10%，"
                "受到持续伤害额外提高20%。"
            ),
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=4,
        ),
        SkillDef(
            id="nanluzhuque_skill2",
            name="焚劫",
            description=(
                "对一个敌方施加30层天火，对其相邻精灵施加15层天火，"
                "然后触发它们持有的所有持续伤害效果。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=4,
        ),
    ],
)
