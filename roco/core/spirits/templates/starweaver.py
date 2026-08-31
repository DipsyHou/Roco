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

STARWEAVER = SpiritTemplate(
    id="starweaver",
    name="黑猫巫师",
    description="黑猫巫师",
    base_stats=BaseStats(hp=550, atk=100, mag_atk=110, def_=140, mag_def=140, speed=150),
    passive_skill=PassiveSkillDef(
        id="starweaver_passive",
        name="共振",
        description=(
            "自身技能固定不消耗能量。秘能上限为8点。对局开始时获得4点秘能。"
            "队友对敌方目标发动攻击时，若自身拥有不少于1点秘能，则消耗1点秘能"
            "对随机一个目标造成40点固伤附加伤害。"
        ),
    ),
    normal_attack=SkillDef(
        id="starweaver_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="starweaver_skill1",
            name="汲取",
            description="对敌方所有精灵造成（20%自身魔攻）点魔法伤害，然后获得（敌方精灵数量）点秘能。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=0,
            launches_attack=True,
        ),
        SkillDef(
            id="starweaver_skill2",
            name="净化",
            description="秘能不少于4点时可使用。消耗4点秘能，净化一个己方精灵的所有负面效果，并使其免疫负面效果（2回合）。",
            cooldown=0,
            target_type=TargetType.single_ally,
            energy_cost=4,
        ),
        SkillDef(
            id="starweaver_skill3",
            name="星爆",
            description="消耗全部秘能，对敌方场上所有精灵造成（（40 + 5 * 消耗秘能数）%自身魔攻）魔法伤害，然后使自己眩晕2回合并获得4点秘能。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=-1,
            launches_attack=True,
        ),
    ],
)

