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

SHENGYU = SpiritTemplate(
    id="shengyu",
    name="圣域祭司",
    description="圣域祭司",
    base_stats=BaseStats(hp=500, atk=110, mag_atk=140, def_=130, mag_def=150, speed=100),
    passive_skill=PassiveSkillDef(
        id="shengyu_passive",
        name="月盈",
        description=(
            "自身技能固定不消耗能量。秘能上限为5点。回合开始时获得5点秘能；"
            "回合结束时，消耗所有秘能，使自身速度提高（20*消耗秘能点数）点，持续2回合。"
            "己方精灵获得秘能后，使其额外获得1点秘能。"
        ),
    ),
    normal_attack=SkillDef(
        id="shengyu_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="shengyu_skill1",
            name="圣洁",
            description=(
                "秘能不少于2点时可以使用。目标为一个己方精灵。"
                "消耗2点秘能，为目标回复（60%自身魔攻）点血量；"
                "若目标拥有秘能，则额外使其回复1点秘能。"
            ),
            cooldown=0,
            target_type=TargetType.single_ally,
            energy_cost=2,
        ),
        SkillDef(
            id="shengyu_skill2",
            name="指引",
            description=(
                "秘能不少于4点时可以使用。目标为一个敌方精灵。"
                "消耗4点秘能，使目标受到的伤害提高16%，持续3回合。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=4,
        ),
        SkillDef(
            id="shengyu_skill3",
            name="再现",
            description=(
                "秘能不少于5点时可以使用。目标为一个敌方精灵。消耗5点秘能，"
                "将目标的随机一个能力值降低、造成伤害降低或受到伤害提高类型的负面效果"
                "（百分比或固定值）复制给除目标外的敌方所有精灵，"
                "以这种方式复制出的负面效果无法再次被复制。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=5,
        ),
    ],
)

