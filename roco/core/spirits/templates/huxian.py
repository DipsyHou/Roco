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

HUXIAN = SpiritTemplate(
    id="huxian",
    name="尖嘴狐仙",
    description="尖嘴狐仙",
    base_stats=BaseStats(hp=500, atk=120, mag_atk=100, def_=140, mag_def=150, speed=140),
    passive_skill=PassiveSkillDef(
        id="huxian_passive",
        name="内爆",
        description=(
            "对敌方给予灼烧或中毒时（合并施加多层仍算 1 次）："
            "给予灼烧后触发该目标的中毒 1 次；给予中毒后触发该目标每个灼烧来源各 1 次。"
            "由内爆触发的结算不会再次触发内爆。"
        ),
    ),
    normal_attack=SkillDef(
        id="huxian_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="huxian_skill1",
            name="烙印",
            description="对一个敌方精灵造成（50%自身物攻）点物理伤害，然后赋予其5层灼烧。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
            launches_attack=True,
        ),
        SkillDef(
            id="huxian_skill2",
            name="鬼火",
            description="对一个敌方精灵赋予4层中毒，然后赋予其4层灼烧。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=3,
        ),
        SkillDef(
            id="huxian_skill3",
            name="扇风",
            description=(
                "对一个敌方精灵赋予4层灼烧，"
                "然后对其相邻敌方精灵各赋予（该目标灼烧层数一半，向下取整）层灼烧。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=3,
        ),
    ],
)

