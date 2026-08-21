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

CUIDING = SpiritTemplate(
    id="cuiding",
    name="翠顶夫人",
    description="翠顶夫人",
    base_stats=BaseStats(hp=700, atk=100, mag_atk=100, def_=130, mag_def=130, speed=140),
    passive_skill=PassiveSkillDef(
        id="cuiding_passive",
        name="澄净",
        description="治疗我方精灵时，若其有浸润效果则回复1点能量，否则赋予其浸润（1回合）。",
    ),
    normal_attack=SkillDef(
        id="cuiding_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="cuiding_skill1",
            name="暖流",
            description="能量 3。指定一名己方精灵，为其与相邻精灵回复（10%自身最大生命）点生命。",
            cooldown=0,
            target_type=TargetType.single_ally_on_field,
            energy_cost=3,
        ),
        SkillDef(
            id="cuiding_skill2",
            name="涟漪",
            description="能量 3。对敌方全体造成（8%自身最大生命）点魔法伤害，并随机驱散其各一个正面效果。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=3,
            launches_attack=True,
        ),
        SkillDef(
            id="cuiding_skill3",
            name="共舞",
            description="能量 5。为我方全体回复（10%自身最大生命）点生命；然后使除自身外的队友立刻获得一次额外行动（按队伍编号顺序），并使全体下一回合延后50%。",
            cooldown=0,
            target_type=TargetType.all_allies,
            energy_cost=5,
        ),
    ],
)

