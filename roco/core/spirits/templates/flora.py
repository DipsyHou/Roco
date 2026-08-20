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

FLORA = SpiritTemplate(
    id="flora",
    name="蹦蹦种子",
    description="蹦蹦种子",
    base_stats=BaseStats(hp=700, atk=100, mag_atk=120, def_=130, mag_def=130, speed=120),
    passive_skill=PassiveSkillDef(
        id="flora_passive",
        name="紧急支援",
        description=(
            "某个己方精灵血量低于30%时，立刻为其回复（100%自身魔攻）点血量，"
            "净化其所有负面效果并提升其25%速度（1回合）。每局对战最多触发一次。"
        ),
    ),
    normal_attack=SkillDef(
        id="flora_normal",
        name="普通攻击",
        description="对一个敌方场上精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="flora_skill1",
            name="光合作用",
            description="为一个己方精灵回复（80%自身魔攻）点血量；若目标是自身，则额外解除随机一个负面效果。",
            cooldown=0,
            target_type=TargetType.single_ally,
            energy_cost=2,
        ),
        SkillDef(
            id="flora_skill2",
            name="抗逆",
            description="使一个己方精灵获得20%减伤，持续2回合。",
            cooldown=0,
            target_type=TargetType.single_ally,
            energy_cost=2,
        ),
        SkillDef(
            id="flora_skill3",
            name="麻醉",
            description="对敌方所有精灵造成（50%自身魔攻）点魔法伤害，并降低10%速度（2回合）。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=3,
            launches_attack=True,
        ),
    ],
)

