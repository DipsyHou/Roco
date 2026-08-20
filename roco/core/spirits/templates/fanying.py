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

FANYING = SpiritTemplate(
    id="fanying",
    name="凡鹰",
    description="凡鹰",
    base_stats=BaseStats(hp=550, atk=130, mag_atk=100, def_=110, mag_def=130, speed=140),
    passive_skill=PassiveSkillDef(
        id="fanying_passive",
        name="破风",
        description="开局获得破风：自身速度+8%，相邻己方精灵速度+4%。",
    ),
    normal_attack=SkillDef(
        id="fanying_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="fanying_skill1",
            name="气旋",
            description="能量 1。对一名敌方精灵造成（80%自身物攻）点物理伤害并降低15%速度（1回合）；对相邻槽位敌方造成（40%自身物攻）点物理伤害。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=1,
            launches_attack=True,
        ),
        SkillDef(
            id="fanying_skill2",
            name="羽翼守护",
            description="能量 2。清除我方所有羽翼守护，再指定一名己方精灵获得羽翼守护（速度+8%，受伤时下一回合提前5%）。",
            cooldown=0,
            target_type=TargetType.single_ally,
            energy_cost=2,
        ),
        SkillDef(
            id="fanying_skill3",
            name="该你上场了",
            description="能量 3。指定场上精灵，使其下一回合提前100%；若为友方则获得20%伤害提升（1回合），若为敌方则眩晕1回合。",
            cooldown=0,
            target_type=TargetType.any_on_field,
            energy_cost=3,
        ),
    ],
)

