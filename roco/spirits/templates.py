"""Static spirit templates (ported from server/src/models/spirits)."""

from __future__ import annotations

from typing import Dict, List, Optional

from ..battle_types import (
    BaseStats,
    PassiveSkillDef,
    SkillDef,
    SpiritTemplate,
    TargetType,
)

FLORA = SpiritTemplate(
    id="flora",
    name="芙萝拉",
    description="温柔的治疗者，擅长回复和支援队友。",
    base_stats=BaseStats(hp=810, atk=120, mag_atk=270, def_=300, mag_def=320, speed=300),
    passive_skill=PassiveSkillDef(
        id="flora_passive",
        name="后勤支援",
        description="场上某个己方精灵血量低于25%时，立刻为其回复（100%×自身魔攻）点血量，净化其所受的负面效果并提升其30%速度持续1回合。每局对战所有队友共计最多触发一次。",
    ),
    normal_attack=SkillDef(
        id="flora_normal",
        name="普通攻击",
        description="对一名场上敌人造成（100%×自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
    ),
    skills=[
        SkillDef(
            id="flora_skill1",
            name="急救",
            description="CD 0回合。为指定精灵回复（80%×自身魔攻）点血量；若目标在场上，额外回复（40%×自身魔攻）点血量。",
            cooldown=0,
            target_type=TargetType.single_ally,
        ),
        SkillDef(
            id="flora_skill2",
            name="止痛",
            description="CD 1回合。指定一个场上精灵，使其受到的下一次伤害减少15%。",
            cooldown=1,
            target_type=TargetType.single_ally_on_field,
        ),
        SkillDef(
            id="flora_skill3",
            name="绷带束缚",
            description="CD 12回合。对对方场上所有精灵造成（80%×自身魔攻）点魔法伤害，并降低10%速度，持续2回合。",
            cooldown=12,
            target_type=TargetType.all_enemies,
        ),
    ],
)

CLAWDRAGON = SpiritTemplate(
    id="clawdragon",
    name="锐爪龙",
    description="凶猛的物理战士，每次使用技能都会自动追加一次普攻。",
    base_stats=BaseStats(hp=600, atk=280, mag_atk=150, def_=200, mag_def=180, speed=260),
    passive_skill=PassiveSkillDef(
        id="clawdragon_passive",
        name="追击本能",
        description="每次使用技能时都会自动触发一次普攻，目标为敌方场上随机一位精灵。",
    ),
    normal_attack=SkillDef(
        id="clawdragon_normal",
        name="普通攻击",
        description="对一名场上敌人造成（100%×自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
    ),
    skills=[
        SkillDef(
            id="clawdragon_skill1",
            name="利爪强化",
            description="CD 6回合。强化自身普攻，额外造成（150%×自身魔攻）点魔法伤害。持续3回合。",
            cooldown=6,
            target_type=TargetType.self,
        ),
        SkillDef(
            id="clawdragon_skill2",
            name="震慑之击",
            description="CD 6回合。下一次非自动触发的普攻对敌人造成2回合眩晕。换下失效。",
            cooldown=6,
            target_type=TargetType.self,
        ),
        SkillDef(
            id="clawdragon_skill3",
            name="狂龙裂地",
            description="CD 6回合。下一次非自动触发的普攻会对敌方场上全体造成伤害。换下失效。",
            cooldown=6,
            target_type=TargetType.self,
        ),
    ],
)

CHAOSLING = SpiritTemplate(
    id="chaosling",
    name="混沌灵",
    description="混沌之力的化身，每次行动都伴随着随机的能力波动。",
    base_stats=BaseStats(hp=600, atk=250, mag_atk=170, def_=220, mag_def=200, speed=240),
    passive_skill=PassiveSkillDef(
        id="chaosling_passive",
        name="混沌波动",
        description="行动后随机获得一项正面效果和一项负面效果（物攻/魔攻/物防/魔防/速度的提升或降低10%），持续999回合。自身受到的所有伤害降低（2%×自身负面效果数，最高10%）。",
    ),
    normal_attack=SkillDef(
        id="chaosling_normal",
        name="普通攻击",
        description="对一名场上敌人造成（100%×自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
    ),
    skills=[
        SkillDef(
            id="chaosling_skill1",
            name="狂暴蓄力",
            description="CD 5回合。连续3回合发动：每回合提升自身10%物攻；第一、二、三回合分别降低自身10%魔攻、10%物防、10%魔防。换下打断。",
            cooldown=5,
            target_type=TargetType.self,
        ),
        SkillDef(
            id="chaosling_skill2",
            name="混沌风暴",
            description="CD 2回合。对敌方场上所有精灵造成（80%×自身物攻）点物理伤害。",
            cooldown=2,
            target_type=TargetType.all_enemies,
        ),
        SkillDef(
            id="chaosling_skill3",
            name="命运反转",
            description="CD 8回合。反转自身所有能力值降低类型的负面效果（变为增益），然后对指定敌方场上精灵造成（140%×自身物攻）点物理伤害。",
            cooldown=8,
            target_type=TargetType.single_enemy,
        ),
    ],
)

STARWEAVER = SpiritTemplate(
    id="starweaver",
    name="星能使",
    description="操纵星辰能量的法师，不依赖CD而消耗能量释放技能。",
    base_stats=BaseStats(hp=600, atk=160, mag_atk=200, def_=230, mag_def=250, speed=220),
    passive_skill=PassiveSkillDef(
        id="starweaver_passive",
        name="星能共振",
        description="释放技能没有CD，转而消耗能量。初始4点能量，最多8点。每次队友造成伤害时若自己有能量，则消耗1点能量额外对目标造成40点固伤（多目标只对其中一个生效）。",
    ),
    normal_attack=SkillDef(
        id="starweaver_normal",
        name="普通攻击",
        description="对一名场上敌人造成（100%×自身物攻）点物理伤害。",
        cooldown=0,
        target_type=TargetType.single_enemy,
    ),
    skills=[
        SkillDef(
            id="starweaver_skill1",
            name="星能脉冲",
            description="不消耗能量。对敌方场上所有精灵造成40点固伤，回复自身（敌方场上精灵数量）点能量。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=0,
        ),
        SkillDef(
            id="starweaver_skill2",
            name="净化之光",
            description="消耗2点能量。净化场上一个己方精灵的所有负面效果，并使其免疫负面效果2回合。",
            cooldown=0,
            target_type=TargetType.single_ally_on_field,
            energy_cost=2,
        ),
        SkillDef(
            id="starweaver_skill3",
            name="星能爆发",
            description="消耗全部能量。对敌方场上所有精灵造成（20×消耗能量数）点固伤，然后使自己下场并获得4点能量。",
            cooldown=0,
            target_type=TargetType.all_enemies,
            energy_cost=-1,
        ),
    ],
)

ALL_SPIRITS: List[SpiritTemplate] = [FLORA, CLAWDRAGON, CHAOSLING, STARWEAVER]
SPIRIT_BY_ID: Dict[str, SpiritTemplate] = {s.id: s for s in ALL_SPIRITS}


def get_spirit_template(sid: str) -> Optional[SpiritTemplate]:
    return SPIRIT_BY_ID.get(sid)
