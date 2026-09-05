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

STEAMDRAGON = SpiritTemplate(
    id="steamdragon",
    name="蒸汽神龙",
    description="蒸汽神龙",
    base_stats=BaseStats(hp=700, atk=130, mag_atk=100, def_=140, mag_def=120, speed=100),
    passive_skill=PassiveSkillDef(
        id="steamdragon_passive",
        name="热启动",
        description="自身回合开始时，获得1层升温。",
    ),
    normal_attack=SkillDef(
        id="steamdragon_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（50%自身物攻）点物理伤害，对其相邻精灵造成（25%×自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="steamdragon_skill1",
            name="烙印",
            description="对一个敌方场上精灵造成（50%自身物攻）点物理伤害，然后给予其5层灼烧。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
            launches_attack=True,
        ),
        SkillDef(
            id="steamdragon_skill2",
            name="嗜热",
            description="回复自身（敌方场上所有精灵灼烧层数之和 * 8）点血量。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=2,
        ),
        SkillDef(
            id="steamdragon_skill3",
            name="沸腾",
            description="消耗自身（25%自身生命上限）点生命，获得4层升温。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=0,
        ),
    ],
)

