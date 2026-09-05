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

PARSAS = SpiritTemplate(
    id="parsas",
    name="帕尔萨斯",
    description="帕尔萨斯",
    base_stats=BaseStats(hp=650, atk=100, mag_atk=130, def_=120, mag_def=120, speed=120),
    passive_skill=PassiveSkillDef(
        id="parsas_passive",
        name="收藏灵魂",
        description=(
            "自身技能固定不消耗能量。对局开始时获得2点秘能，秘能上限为20点。"
            "自身成为己方精灵技能的唯一目标时，回复2点秘能。"
            "当自身秘能从小于13点增长至大于等于13点时，使自身下回合提前100%，"
            "并使自身的「恐怖」效果延长1回合。"
        ),
    ),
    normal_attack=SkillDef(
        id="parsas_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害，并回复1点秘能。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="parsas_skill1",
            name="恶魔契约",
            description="消耗自身当前生命值的10%，回复3点秘能。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=None,
        ),
        SkillDef(
            id="parsas_skill2",
            name="巨魔之眼",
            description=(
                "秘能不少于7点时可以使用。消耗7点秘能，赋予自身「恐怖」效果，"
                "持续3回合，期间再次赋予此效果会重置持续时间；"
                "然后对一个敌方精灵造成（120%自身魔攻）点魔法伤害。"
                "（恐怖：正面效果。携带者造成伤害时，无视10%的魔防。）"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=7,
            launches_attack=True,
        ),
        SkillDef(
            id="parsas_skill3",
            name="新月乱舞",
            description=(
                "秘能不少于13点时可以使用。消耗13点秘能，"
                "对一个敌方精灵造成（120%自身魔攻）点魔法伤害，"
                "随后对全体敌方精灵造成（80%自身魔攻）点魔法伤害。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=13,
            launches_attack=True,
        ),
    ],
)

