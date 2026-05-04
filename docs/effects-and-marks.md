# Roco CLI — 增益 / 减益 / 标记一览

本文档对应 `cli/roco/battle_types.py` 中的枚举与字段，便于开发与排查。

---

## 1. `EffectType`（挂在 `BattleSpirit.effects` 上的效果）

| 枚举值 | 含义 | 典型来源 | 关键附加字段 |
|--------|------|----------|----------------|
| `stat_percent_modify` | 按百分比修改种族值（战斗内计算用） | 混沌波动、绷带束缚、狂暴蓄力各阶段、芙萝拉被动加速等 | `stat_type`, `value`（如 `0.1` = +10%，`-0.1` = -10%） |
| `stat_flat_modify` | 按固定值修改种族值 | （协议预留，当前实现少用） | `stat_type`, `value` |
| `stun` | 眩晕：无法普攻/技能 | 震慑之击强化普攻、狂龙裂地 AOE 等 | `remaining_turns`（展示上多为「持续若干回合」） |
| `damage_modify` | 增伤/减伤（参与伤害公式） | 预留 / 扩展用 | `damage_modify_sub_type`, `value` |
| `attack_enhance` | 普攻强化（锐爪龙独有抽象） | 利爪强化 / 震慑之击 / 狂龙裂地 | `enhance_type`: `magic_damage` \| `stun` \| `aoe`；`magic_damage_ratio`（魔伤倍率） |
| `next_damage_reduction` | 下一次受伤减免（一次性） | 芙萝拉「止痛」 | `reduction_percent`（如 `0.15`） |
| `debuff_immunity` | 免疫负面效果 | 星能使「净化之光」 | `remaining_turns` |
| `channeling_skill` | 多回合蓄力/引导 | 混沌灵「狂暴蓄力」 | `channel_phase`（阶段计数）, `channel_skill_id` |

---

## 2. `DamageModifySubType`（仅当 `EffectType.damage_modify` 时使用）

| 枚举值 | 含义 |
|--------|------|
| `physical_increase` / `physical_decrease` | 物理增伤 / 物理减伤 |
| `magical_increase` / `magical_decrease` | 魔法增伤 / 魔法减伤 |
| `all_increase` / `all_decrease` | 全类型增伤 / 减伤 |

当前精灵技能逻辑里主要用百分比词条叠在 `stat_percent_modify`；`damage_modify` 类型保留给后续扩展。

---

## 3. `StatType`（属性维度）

`hp`, `atk`, `mag_atk`, `def`, `mag_def`, `speed`

计算有效属性时：`hp` 在引擎里用 `max_hp` 参与展示；伤害公式读取 `def` / `mag_def`。

---

## 4. `BattleLogType`（战斗日志类型，非状态字段）

回合开始、行动执行、伤害、治疗、效果施加/移除、下场、换人、被动、战斗结束、眩晕提示等 —— 用于回放与 CLI 文本输出，不挂在精灵身上。

---

## 5. 非 `EffectType` 的「标记 / 资源」（存在 `BattleSpirit` 字段上）

| 字段 | 含义 | 适用精灵 |
|------|------|----------|
| `passive_triggered` | 一次性被动是否已用掉 | 芙萝拉「后勤支援」整局队友合计最多一次 |
| `energy` / `max_energy` | 能量点数 | 星能使（技能消耗能量，不用常规 CD） |
| `skill_cooldowns` | `skill_id -> 剩余回合 CD` | 除星能使外有 CD 的技能 |

---

## 6. 不写进 `effects` 的全局/被动逻辑（代码内特殊分支）

| 机制 | 说明 |
|------|------|
| **星能使 · 星能共振** | 任意己方伤害命中后，若场上星能使存活且 `energy > 0`，对目标追加固伤并扣 1 能量（引擎内钩子，非 Effect） |
| **混沌灵 · 混沌波动** | 每次「非自动」普攻/技能行动后随机 +10%/-10% 属性（生成两条 `stat_percent_modify`） |
| **混沌灵 · 混沌被动减伤** | 按自身「负面效果数量」额外百分比减伤（伤害公式内直接计算，非单独 Effect） |

---

## 7. `is_debuff` 标记

每条 `BattleEffect` 均有 `is_debuff: bool`，用于：

- 混沌被动减伤计数  
- 「净化」类技能移除负面  
- UI/CLI 区分buff/debuff样式  

---

## 8. `remaining_turns` 约定

| 值 | 含义 |
|----|------|
| `-1` | 永久直到被清除（换下、消耗、被动移除等） |
| `999` 或极大值 | 逻辑上的「永久」类随机波动（混沌波动等） |
| 正整数 | 每回合结束 tick -1，至 0 移除 |

---

以上为当前 Python CLI 版本与原版 TS 对齐的状态设计清单。
