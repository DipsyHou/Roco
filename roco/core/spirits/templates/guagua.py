"""呱呱 template."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

GUAGUA = SpiritTemplate(
    id="guagua",
    name="呱呱",
    description="呱呱",
    base_stats=BaseStats(hp=600, atk=120, mag_atk=120, def_=120, mag_def=120, speed=140),
    passive_skill=PassiveSkillDef(
        id="guagua_passive",
        name="必有我师",
        description=(
            "游戏开始时，我方首位精灵获得“师傅”状态效果。场上存在“师傅”时，"
            "自身双攻提高12%，攻击伤害暴击率提升30%，暴击效果提升60%。"
            "师傅发动攻击后，自身每回合最多1次自动释放特殊技能“学会了！”。"
        ),
    ),
    normal_attack=SkillDef(
        id="guagua_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="guagua_learned",
            name="学会了！",
            description=(
                "特殊技能。对一个敌方精灵造成（50%自身物攻）物理伤害；"
                "使“师傅”获得自身“必有我师”的双攻、暴击率和暴击效果提升效果，持续2回合。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=0,
            special=True,
            launches_attack=True,
        ),
        SkillDef(
            id="guagua_skill1",
            name="师傅请喝茶",
            description=(
                "能量 2。选择除自身外的一名己方精灵；清除我方所有精灵的“师傅”状态效果，"
                "使目标获得“师傅”状态；自身速度提高10%，持续2回合。"
            ),
            cooldown=0,
            target_type=TargetType.single_ally_on_field,
            energy_cost=2,
        ),
        SkillDef(
            id="guagua_skill2",
            name="百家拳法",
            description=(
                "能量 2。对一个敌方精灵造成（100%自身物攻）物理伤害；"
                "若场上存在师傅，则额外造成一段（100%师傅双攻的较高值）物理伤害。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
            launches_attack=True,
        ),
        SkillDef(
            id="guagua_skill3",
            name="学神不学形",
            description=(
                "能量 5。使自身获得“学神”状态效果：自身发动攻击后，若场上存在师傅，"
                "使师傅对此次攻击的随机一个目标造成一段（30%师傅双攻的较高值）物理附加伤害。"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=5,
        ),
    ],
)
