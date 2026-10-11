"""Static spirit templates."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    DamageType,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

CLAWDRAGON = SpiritTemplate(
    id="clawdragon",
    name="上古战龙",
    description="上古战龙",
    base_stats=BaseStats(hp=550, attack=150, defense=110, speed=130),
    elements=(DamageType.dragon, DamageType.physical),
    passive_skill=PassiveSkillDef(
        id="clawdragon_passive",
        name="守护者",
        description=(
            "受到伤害时提升自身15%防御，持续2回合。"
            "此效果每回合最多触发1次，自身回合开始时重置次数。"
        ),
    ),
    normal_attack=SkillDef(
        id="clawdragon_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（50%自身攻击）点龙属性伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="clawdragon_skill1",
            name="传说力量",
            description=(
                "对一个敌方精灵造成一段（50%自身攻击+10%目标当前生命）点龙属性伤害。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
            launches_attack=True,
        ),
        SkillDef(
            id="clawdragon_skill2",
            name="龙之舞",
            description="提高自身20%攻击与20%速度。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
        SkillDef(
            id="clawdragon_skill3",
            name="过肩摔",
            description=(
                "对一个敌方精灵造成（120%自身攻击）点物理属性伤害，并使其眩晕1回合。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=4,
            launches_attack=True,
        ),
    ],
)
