"""Static spirit templates."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

QIUKA = SpiritTemplate(
    id="qiuka",
    name="裘卡",
    description="裘卡",
    base_stats=BaseStats(hp=500, atk=150, mag_atk=100, def_=110, mag_def=120, speed=150),
    passive_skill=PassiveSkillDef(
        id="qiuka_passive",
        name="痛苦",
        description="造成伤害时，若目标有中毒，此次伤害提升25%。",
    ),
    normal_attack=SkillDef(
        id="qiuka_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="qiuka_skill1",
            name="毒刺",
            description="能量 3。重复5次：对敌方随机目标造成（25%自身物攻）物理伤害，并赋予2层中毒。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=3,
            launches_attack=True,
        ),
        SkillDef(
            id="qiuka_skill2",
            name="厉毒",
            description="能量 2。指定一名敌方精灵，赋予4层中毒并使其触发一次中毒效果。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
        ),
        SkillDef(
            id="qiuka_skill3",
            name="毒爪",
            description=(
                "能量 3。对一名敌方精灵造成（80%自身物攻）物理伤害；"
                "目标每层中毒使此次伤害倍率+16%自身物攻，最多计入10层；然后使其触发一次中毒效果。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=3,
            launches_attack=True,
        ),
    ],
)

