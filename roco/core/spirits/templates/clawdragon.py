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

CLAWDRAGON = SpiritTemplate(
    id="clawdragon",
    name="上古战龙",
    description="上古战龙",
    base_stats=BaseStats(hp=550, atk=150, mag_atk=100, def_=110, mag_def=100, speed=140),
    passive_skill=PassiveSkillDef(
        id="clawdragon_passive",
        name="守护者",
        description=(
            "受到伤害时，提升自身15%物防与魔防，持续2回合。"
            "此效果每回合最多触发1次，自身回合开始时重置次数。"
        ),
    ),
    normal_attack=SkillDef(
        id="clawdragon_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="clawdragon_skill1",
            name="传说力量",
            description="对一个敌方精灵造成一段（50%自身物攻+10%目标当前生命值）点物理伤害。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
            launches_attack=True,
        ),
        SkillDef(
            id="clawdragon_skill2",
            name="龙之舞",
            description="提高自身20%物攻与20%速度。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
        SkillDef(
            id="clawdragon_skill3",
            name="过肩摔",
            description="对一个敌方精灵造成（120%自身物攻）点物理伤害，并使其眩晕1回合。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=4,
            launches_attack=True,
        ),
    ],
)

