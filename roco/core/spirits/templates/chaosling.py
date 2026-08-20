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

CHAOSLING = SpiritTemplate(
    id="chaosling",
    name="梦想龙",
    description="梦想龙",
    base_stats=BaseStats(hp=600, atk=140, mag_atk=100, def_=120, mag_def=120, speed=130),
    passive_skill=PassiveSkillDef(
        id="chaosling_passive",
        name="梦想潮汐",
        description="行动后随机获得一项正面效果和一项负面效果（物攻/魔攻/物防/魔防/速度的提升或降低10%）。自身受到的所有伤害降低（2% * 自身负面效果数，最高10%）。",
    ),
    normal_attack=SkillDef(
        id="chaosling_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="chaosling_skill1",
            name="愿力凝聚",
            description="蓄力3回合：每回合提升自身10%物攻；第一、二、三回合分别降低自身10%魔攻、10%物防、10%魔防。再次释放此技能会打断蓄力。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
        SkillDef(
            id="chaosling_skill2",
            name="精神风暴",
            description="对敌方所有精灵造成（60%自身物攻）点物理伤害。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=2,
            launches_attack=True,
        ),
        SkillDef(
            id="chaosling_skill3",
            name="命运逆转",
            description="反转自身所有能力值降低类型的负面效果，然后对一个敌方精灵造成（150%自身物攻）点物理伤害。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=4,
            launches_attack=True,
        ),
    ],
)

