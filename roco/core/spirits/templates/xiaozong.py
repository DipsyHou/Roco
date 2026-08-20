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

XIAOZONG = SpiritTemplate(
    id="xiaozong",
    name="小琮",
    description="以灵气护体、濒死通灵的灵珏之灵。",
    base_stats=BaseStats(hp=600, atk=110, mag_atk=140, def_=120, mag_def=130, speed=110),
    passive_skill=PassiveSkillDef(
        id="xiaozong_passive",
        name="灵珏御光",
        description=(
            "灵珏护体：受到每段伤害时，降低（10%自身灵气层数，向下取整）点伤害，并赋予自身本段实际减少的伤害值层灵气。"
            "自身死亡时，若尚无通灵且有灵气层数，则将生命续至（自身灵气层数）点并获得通灵。"
            "通灵状态：受到每段伤害时，降低（10%自身灵气层数，向下取整）点伤害。"
            "灵气上限为对战开始时的生命上限。"
        ),
    ),
    normal_attack=SkillDef(
        id="xiaozong_normal",
        name="普通攻击",
        description=(
            "对一个敌方精灵造成（100%自身物攻）点物理伤害。"
            "通灵状态：消耗30层灵气，改为造成（100%自身魔攻）点魔法伤害。"
        ),
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="xiaozong_skill1",
            name="日月齐光",
            description=(
                "能量 3。对一个敌方场上精灵造成（80%自身魔攻）点魔法伤害，对其相邻精灵造成（40%自身魔攻）点魔法伤害，并赋予自身30层灵气。"
                "通灵状态：消耗30层灵气，主目标改为（120%自身魔攻），相邻改为（60%自身魔攻），不再赋予灵气。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=3,
            launches_attack=True,
        ),
        SkillDef(
            id="xiaozong_skill2",
            name="华采若英",
            description=(
                "能量 3。对一个敌方场上精灵造成（80%自身魔攻+20%自身灵气层数）点魔法伤害，并赋予自身30层灵气。"
                "通灵状态：消耗30层灵气，造成同样伤害并回复（30%此伤害值）点血量，不再赋予灵气。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=3,
            launches_attack=True,
        ),
        SkillDef(
            id="xiaozong_skill3",
            name="远举云中",
            description=(
                "能量 3。获得10%减伤，并使日月齐光与华采若英的能量消耗减少1点，均持续3回合，"
                "期间再次使用本技能刷新持续时间；赋予自身30层灵气。"
                "通灵状态：消耗30层灵气，获得15%减伤，并使日月齐光与华采若英能量消耗减少1点，"
                "均持续3回合，期间再次使用本技能刷新持续时间。"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=3,
        ),
    ],
)

