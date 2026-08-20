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

TENGJIAO = SpiritTemplate(
    id="tengjiao",
    name="藤椒小巴",
    description="藤椒小巴",
    base_stats=BaseStats(hp=700, atk=140, mag_atk=100, def_=110, mag_def=110, speed=120),
    passive_skill=PassiveSkillDef(
        id="tengjiao_passive",
        name="热火朝天",
        description=(
            "我方精灵每消耗1点能量，积攒1层“火力”。当“火力”从小于10/20/30层增长至"
            "大于等于该层数时，分别获得一次额外行动：强制释放“出锅！”，菜品分别固定为"
            "“辣子鸡”/“水煮鱼”/“毛血旺”，此次不消耗能量。一次增长跨越多个阈值时各触发一次；"
            "须回落后再越过才会再次触发。"
        ),
    ),
    normal_attack=SkillDef(
        id="tengjiao_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="tengjiao_skill1",
            name="浇油",
            description="获得5层“火力”；提升自身20%物攻，持续3回合。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=2,
        ),
        SkillDef(
            id="tengjiao_skill2",
            name="炝锅",
            description=(
                "延长场上所有菜品效果（辣子鸡、水煮鱼、毛血旺）持续时间1回合，"
                "但不会超过该效果原本的持续时间。"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=2,
        ),
        SkillDef(
            id="tengjiao_skill3",
            name="出锅！",
            description=(
                "随机端出一道川菜：辣子鸡（点名己方，基于施加者物攻10%提升双攻，3回合）/"
                "水煮鱼（自身，基于携带者物攻10%提升全体己方含自身双攻，2回合）/"
                "毛血旺（全体敌方，消耗全部火力，每3层给予1层灼烧，并提高15%受到的持续伤害，3回合）。"
                "初始权重1:1:1；无水煮鱼时水煮鱼权重翻倍；火力≥20时毛血旺权重翻倍。"
                "辣子鸡需指定己方目标；水煮鱼与毛血旺无需点选。"
            ),
            cooldown=0,
            target_type=TargetType.none,
            energy_cost=3,
        ),
    ],
)

