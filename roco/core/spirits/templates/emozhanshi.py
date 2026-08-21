"""恶魔战士 template."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

EMOZHANSHI = SpiritTemplate(
    id="emozhanshi",
    name="恶魔战士",
    description="恶魔战士",
    base_stats=BaseStats(hp=750, atk=100, mag_atk=100, def_=120, mag_def=130, speed=110),
    passive_skill=PassiveSkillDef(
        id="emozhanshi_passive",
        name="肉盾",
        description=(
            "基于自身物防与魔防之和的8%，提高全体己方精灵（含自身）的物防与魔防；"
            "自身受到的伤害提高50%。"
        ),
    ),
    normal_attack=SkillDef(
        id="emozhanshi_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="emozhanshi_skill1",
            name="血墙",
            description=(
                "固定不消耗能量。目标为自身。消耗10%最大生命值（至少保留1点，不视为受到伤害），"
                "获得“血墙”正面效果，持续4回合，期间再次获得此效果会重置持续时间：提高自身50%双防。"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=0,
        ),
        SkillDef(
            id="emozhanshi_skill2",
            name="狂宴",
            description="能量 4。目标为自身。回复（50%自身已损生命）生命。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=4,
        ),
        SkillDef(
            id="emozhanshi_skill3",
            name="临行留念",
            description=(
                "固定不消耗能量。目标为全体敌方精灵。对所有目标造成"
                "（50%自身魔攻+10%自身当前生命）魔法伤害；随后自身直接倒下。"
            ),
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=0,
            launches_attack=True,
        ),
    ],
)
