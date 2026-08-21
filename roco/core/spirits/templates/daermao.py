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

DAERMAO = SpiritTemplate(
    id="daermao",
    name="大耳帽兜",
    description="以纯白净化与冰冻处决控场的霜系精灵。",
    base_stats=BaseStats(hp=600, atk=120, mag_atk=110, def_=140, mag_def=140, speed=120),
    passive_skill=PassiveSkillDef(
        id="daermao_passive",
        name="纯白",
        description=(
            "释放技能时，若目标的正面效果数为2或3，则随机清除其1个正面效果；"
            "若为4或更多，则随机清除其2个正面效果。"
        ),
    ),
    normal_attack=SkillDef(
        id="daermao_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="daermao_skill1",
            name="轻雾",
            description="能量 2。使目标所有技能能耗+1，持续3回合；已有此效果时重置持续时间。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
        ),
        SkillDef(
            id="daermao_skill2",
            name="飞霰",
            description="能量 2。赋予目标6层冰冻，并赋予其相邻精灵3层冰冻（回合结束时生命不高于1%最大生命×层数则立刻阵亡）。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
        ),
        SkillDef(
            id="daermao_skill3",
            name="萌化",
            description="能量 4。使目标造成的伤害降低33%，持续2回合。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=4,
        ),
    ],
)

