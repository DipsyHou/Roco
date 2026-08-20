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

DEERLE = SpiritTemplate(
    id="deerle",
    name="梅花德尔勒",
    description="梅花德尔勒",
    base_stats=BaseStats(hp=550, atk=120, mag_atk=100, def_=130, mag_def=130, speed=140),
    passive_skill=PassiveSkillDef(
        id="deerle_passive",
        name="看破",
        description=(
            "战斗开始时，赋予随机两个敌方精灵「破绽」效果，持续3回合。"
            "对敌方目标释放普通攻击时，若目标拥有「破绽」，则清除其一条「破绽」"
            "（优先清除持续时间较短的「破绽」），并赋予除目标外随机两个敌方精灵"
            "「破绽」，持续3回合。（破绽：负面效果。物防降低5%。）"
        ),
    ),
    normal_attack=SkillDef(
        id="deerle_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="deerle_skill1",
            name="剑花",
            description=(
                "目标为自身。若拥有「剑舞」，则将「剑舞」的持续时间重置为5回合，"
                "并叠加一层「剑舞」；否则获得1层「剑舞」，持续5回合。"
                "（剑舞：状态效果，可叠加，最多6层。每层提升5%物攻与20%速度；"
                "释放普通攻击后叠加一层「剑舞」，不重置持续时间。"
                "游戏开始时，获得1层「剑舞」，持续5回合。）"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
        SkillDef(
            id="deerle_skill2",
            name="穿刺",
            description="对一个敌方精灵赋予「破绽」，持续3回合；然后对其造成（100%自身物攻）点物理伤害。",
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=1,
            launches_attack=True,
        ),
        SkillDef(
            id="deerle_skill3",
            name="敏锐",
            description=(
                "对敌方所有精灵造成（25%自身物攻）点物理伤害；"
                "然后赋予所有拥有不少于3条「破绽」，且未拥有「漏洞百出」效果的目标「漏洞百出」。"
                "（漏洞百出：状态效果。施加者对持有者释放普通攻击时，"
                "施加者的此次普通攻击伤害提高25%，并获得一次额外行动；"
                "随后解除持有者的此效果。）"
            ),
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=1,
            launches_attack=True,
        ),
    ],
)

