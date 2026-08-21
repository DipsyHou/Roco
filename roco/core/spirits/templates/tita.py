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

TITA = SpiritTemplate(
    id="tita",
    name="缇塔",
    description="缇塔",
    base_stats=BaseStats(hp=750, atk=100, mag_atk=100, def_=140, mag_def=110, speed=100),
    passive_skill=PassiveSkillDef(
        id="tita_passive",
        name="缓存",
        description="若我方精灵在一回合内消耗不少于5点能量，回合结束时回复1点能量。",
    ),
    normal_attack=SkillDef(
        id="tita_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="tita_skill1",
            name="分流",
            description="能量 5。获得2层分流；若已有分流则置为2层（友方回合结束后回复1能量，自身回合开始减1层）。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=5,
        ),
        SkillDef(
            id="tita_skill2",
            name="扩容",
            description="能量 5。获得1层扩容（最多5层，使己方能量上限提升对应点数）。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=5,
        ),
        SkillDef(
            id="tita_skill3",
            name="过载",
            description="能量 3。对一名敌方精灵造成（175%自身魔攻）点魔法伤害，并使双方速度降低30%（1回合）。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=3,
            launches_attack=True,
        ),
    ],
)

