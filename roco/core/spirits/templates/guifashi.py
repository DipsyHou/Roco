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

GUIFASHI = SpiritTemplate(
    id="guifashi",
    name="诡法师",
    description="以牌库与额外行动征战的策士。",
    base_stats=BaseStats(hp=600, atk=100, mag_atk=130, def_=130, mag_def=130, speed=110),
    passive_skill=PassiveSkillDef(
        id="guifashi_passive",
        name="塔罗",
        description="开局加入11种大阿卡纳各1张。每回合开始抽3张，回合结束将所有手牌洗回牌堆。",
    ),
    normal_attack=SkillDef(
        id="guifashi_normal",
        name="普通攻击",
        description="对一个敌方精灵造成（100%自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
        launches_attack=True,
    ),
    skills=[
        SkillDef(
            id="guifashi_draw",
            name="占卜",
            description="能量 1。从牌堆随机抽1张牌；然后可再行动一次（占卜/揭晓/逆位/跳过）。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=1,
        ),
        SkillDef(
            id="guifashi_show",
            name="揭晓",
            description="能量 1。打出1张手牌并触发牌面效果；然后可再行动一次（占卜/揭晓/逆位/跳过）。",
            cooldown=0,
            target_type=TargetType.any_on_field,
            energy_cost=1,
        ),
        SkillDef(
            id="guifashi_cheat",
            name="逆位",
            description="能量 2。将一张手牌变为指定的另一种阿卡纳牌；然后可再行动一次（占卜/揭晓/逆位/跳过）。",
            cooldown=0,
            target_type=TargetType.self,
            energy_cost=2,
        ),
    ],
)

