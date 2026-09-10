"""Static spirit templates."""

from __future__ import annotations

from ...battle.types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

LIUGUANGJING = SpiritTemplate(
    id="liuguangjing",
    name="流光镜",
    description="映照我方伤害与能量、以映像倾泻的辅助输出。",
    base_stats=BaseStats(hp=650, atk=110, mag_atk=100, def_=120, mag_def=120, speed=110),
    passive_skill=PassiveSkillDef(
        id="liuguangjing_passive",
        name="鉴中乾坤 / 流转",
        description=(
            "鉴中乾坤：我方精灵造成伤害时（灵珏前记账；含灼烧/寄生，不含中毒），"
            "获得等量「映像伤害」；我方精灵消耗或回复队伍能量时（含溢出），获得等量「映像能量」。"
            "流转：聚能使自身下回合提前24%；我方精灵消耗队伍能量后，若队伍能量未达上限且映像能量不少于6，"
            "消耗6点映像能量并回复1点。"
        ),
    ),
    normal_attack=SkillDef(
        id="liuguangjing_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（50%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="liuguangjing_skill1",
            name="阴阳",
            description=(
                "目标为自身。若当前队伍能量不大于上限的50%，回复2点能量；"
                "自身下一次正常回合开始时再次触发一次此效果"
                "（开始时无论是否仍满足条件都会消耗此次延迟；满足则再回2点）。"
            ),
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=0,
        ),
        SkillDef(
            id="liuguangjing_skill2",
            name="镜倾",
            description=(
                "目标为一个敌方精灵。对目标与其相邻精灵各造成（6%「映像伤害」）固定伤害，"
                "然后清除50%自身「映像伤害」。"
            ),
            cooldown=0,
            target_type=TargetType.single_enemy,
            energy_cost=2,
            launches_attack=True,
        ),
    ],
)
