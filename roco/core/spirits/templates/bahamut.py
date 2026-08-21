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

BAHAMUT = SpiritTemplate(
    id="bahamut",
    name="巴哈姆特",
    description="巴哈姆特",
    base_stats=BaseStats(hp=550, atk=140, mag_atk=100, def_=140, mag_def=140, speed=120),
    passive_skill=PassiveSkillDef(
        id="bahamut_passive",
        name="气蕴沧溟",
        description=(
            "战斗开始时，赋予自身10层“罡气”；"
            "若自身处于队伍首位，赋予自身“彻甲”；否则赋予自身“寸劲”。"
        ),
    ),
    normal_attack=SkillDef(
        id="bahamut_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="bahamut_skill1",
            name="疾风拳",
            description="能量 1。对一个敌方精灵造成3段物理伤害，每段倍率为（50%自身物攻）。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=1,
            launches_attack=True,
        ),
        SkillDef(
            id="bahamut_skill2",
            name="迎击",
            description="能量 1。获得1层“招架”。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=1,
        ),
        SkillDef(
            id="bahamut_skill3",
            name="龙之舞",
            description="能量 3。永久提高自身20%物攻与20%速度。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
        SkillDef(
            id="bahamut_zhaojia_jiequan",
            name="截拳",
            description="消耗全部招架，对目标造成（招架层数）段物理伤害，每段（30%自身物攻）。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=0,
            special=True,
            launches_attack=True,
        ),
        SkillDef(
            id="bahamut_zhaojia_fanpu",
            name="反扑",
            description=(
                "消耗全部招架，对目标造成（30%自身物攻）点物理伤害，"
                "然后重复（招架层数）次：对随机敌方造成（30%自身物攻）点物理伤害。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=0,
            special=True,
            launches_attack=True,
        ),
    ],
)

