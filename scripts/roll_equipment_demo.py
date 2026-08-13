"""局外装备养成模拟：刷装备入仓库、自由装配给精灵。

规则见 docs/mechanics.md「局外养成 - 装备系统」。
存档默认：scripts/equipment_demo_save.json

用法：
  python scripts/roll_equipment_demo.py          # 命令行
  python scripts/roll_equipment_demo.py --gui  # 图形界面
  python scripts/roll_equipment_gui.py
"""
from __future__ import annotations

import json
import random
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

# 允许从项目根目录运行
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from roco.core.spirits.templates import ALL_SPIRITS  # noqa: E402

SAVE_PATH = Path(__file__).resolve().parent / "equipment_demo_save.json"

SLOTS = ("头饰", "护甲", "鞋子", "武器")
TIERS = ("绿", "蓝", "紫", "金")
HP_VAL = (12, 14, 16, 18)
OTHER_VAL = (2.4, 2.8, 3.2, 3.6)
STATS = ("生命", "物攻", "魔攻", "物防", "魔防", "速度")
STAT_KEYS = {
    "生命": "hp",
    "物攻": "atk",
    "魔攻": "mag_atk",
    "物防": "def_",
    "魔防": "mag_def",
    "速度": "speed",
}
SLOT_FIRST_STAT = {
    "头饰": ("生命",),
    "护甲": ("物防", "魔防"),
    "鞋子": ("速度",),
    "武器": ("物攻", "魔攻"),
}
ITEM_NAMES = {
    "头饰": ("蔓绕冠", "灵叶箍", "晨露饰"),
    "护甲": ("夜纹袍", "鳞甲衣", "藤织甲"),
    "鞋子": ("疾行履", "风踪靴", "沙纹履"),
    "武器": ("秘仪杖", "锋鸣刃", "灵息弓"),
}


@dataclass
class Affix:
    stat: str
    value: float

    def fmt(self) -> str:
        return f"{self.stat}+{self.value:g}"


@dataclass
class Equipment:
    uid: str
    slot: str
    name: str
    affixes: list[Affix]
    upgrades_left: int = 3
    equipped_spirit_id: Optional[str] = None

    def summary(self) -> str:
        aff = "｜".join(a.fmt() for a in self.affixes)
        where = f" → {self.equipped_spirit_id}" if self.equipped_spirit_id else ""
        up = f" 升级×{self.upgrades_left}" if self.upgrades_left else " 已满升级"
        return f"[{self.uid[:8]}] {self.slot}·{self.name}{where}  {aff}{up}"

    def totals(self) -> dict[str, float]:
        out = {s: 0.0 for s in STATS}
        for a in self.affixes:
            out[a.stat] += a.value
        return out


@dataclass
class GameState:
    equipment: dict[str, Equipment] = field(default_factory=dict)
    # spirit_id -> slot -> equipment uid
    loadouts: dict[str, dict[str, Optional[str]]] = field(default_factory=dict)

    def ensure_spirits(self) -> None:
        for t in ALL_SPIRITS:
            if t.id not in self.loadouts:
                self.loadouts[t.id] = {s: None for s in SLOTS}

    def inventory(self) -> list[Equipment]:
        return [e for e in self.equipment.values() if e.equipped_spirit_id is None]

    def spirit_equipment(self, spirit_id: str) -> dict[str, Optional[Equipment]]:
        self.ensure_spirits()
        slots = self.loadouts[spirit_id]
        return {
            slot: self.equipment[uid] if uid else None
            for slot, uid in slots.items()
        }


def roll_tier_index() -> int:
    return random.randint(0, 3)


def tier_val(stat: str, idx: int) -> float:
    return HP_VAL[idx] if stat == "生命" else OTHER_VAL[idx]


def roll_affix(stat: str) -> Affix:
    idx = roll_tier_index()
    return Affix(stat=stat, value=tier_val(stat, idx))


def create_equipment(slot: str) -> Equipment:
    first_pool = SLOT_FIRST_STAT[slot]
    first_stat = random.choice(first_pool)
    used = {first_stat}
    affixes = [roll_affix(first_stat)]
    pool = [s for s in STATS if s not in used]
    random.shuffle(pool)
    for stat in pool[:2]:
        affixes.append(roll_affix(stat))
    return Equipment(
        uid=uuid.uuid4().hex,
        slot=slot,
        name=random.choice(ITEM_NAMES[slot]),
        affixes=affixes,
        upgrades_left=3,
    )


def upgrade_equipment(eq: Equipment) -> str:
    if eq.upgrades_left <= 0:
        return "该装备已无升级次数。"
    idx = random.randint(0, 2)
    tier_i = roll_tier_index()
    add = tier_val(eq.affixes[idx].stat, tier_i)
    eq.affixes[idx].value += add
    eq.upgrades_left -= 1
    tier = TIERS[tier_i]
    return (
        f"升级 [{eq.uid[:8]}]：{eq.affixes[idx].stat}+{add:g}({tier})，"
        f"该条现为 {eq.affixes[idx].fmt()}，剩余升级 {eq.upgrades_left} 次。"
    )


def spirit_base(spirit_id: str) -> dict[str, float]:
    t = next(x for x in ALL_SPIRITS if x.id == spirit_id)
    bs = t.base_stats
    return {
        "生命": float(bs.hp),
        "物攻": float(bs.atk),
        "魔攻": float(bs.mag_atk),
        "物防": float(bs.def_),
        "魔防": float(bs.mag_def),
        "速度": float(bs.speed),
    }


def spirit_panel(spirit_id: str, state: GameState) -> str:
    t = next(x for x in ALL_SPIRITS if x.id == spirit_id)
    base = spirit_base(spirit_id)
    gear = {s: 0.0 for s in STATS}
    lines = [f"=== {t.name} ({spirit_id}) ===", "挡位基础（当前模板数值）："]
    for s in STATS:
        lines.append(f"  {s} {base[s]:g}")

    lines.append("\n已装备：")
    equipped_any = False
    for slot in SLOTS:
        uid = state.loadouts[spirit_id][slot]
        if not uid:
            lines.append(f"  {slot}：（空）")
            continue
        equipped_any = True
        eq = state.equipment[uid]
        lines.append(f"  {slot}：{eq.summary()}")
        for s, v in eq.totals().items():
            gear[s] += v

    if not equipped_any:
        lines[-1] = "  （无）"

    lines.append("\n开局面板（基础 + 装备）：")
    for s in STATS:
        if gear[s]:
            end = int(base[s] + gear[s]) if s == "生命" else base[s] + gear[s]
            lines.append(f"  {s}：{base[s]:g} + {gear[s]:g} = {end:g}")
        else:
            lines.append(f"  {s}：{base[s]:g}")
    return "\n".join(lines)


def equip(state: GameState, eq_uid: str, spirit_id: str) -> str:
    state.ensure_spirits()
    uid, err = resolve_equipment_uid(state, eq_uid)
    if err:
        return err
    assert uid is not None
    eq_uid = uid

    eq = state.equipment[eq_uid]
    if eq.equipped_spirit_id:
        return f"该装备已装在 {eq.equipped_spirit_id} 上，请先卸下。"

    slot = eq.slot
    old_uid = state.loadouts[spirit_id][slot]
    if old_uid:
        state.equipment[old_uid].equipped_spirit_id = None

    state.loadouts[spirit_id][slot] = eq.uid
    eq.equipped_spirit_id = spirit_id
    t = next(x for x in ALL_SPIRITS if x.id == spirit_id)
    return f"已将 [{eq.uid[:8]}] {eq.slot}·{eq.name} 装备给 {t.name}。"


def unequip(state: GameState, spirit_id: str, slot: str) -> str:
    state.ensure_spirits()
    if slot not in SLOTS:
        return f"部位须为：{' / '.join(SLOTS)}"
    uid = state.loadouts[spirit_id][slot]
    if not uid:
        return "该部位没有装备。"
    eq = state.equipment[uid]
    eq.equipped_spirit_id = None
    state.loadouts[spirit_id][slot] = None
    t = next(x for x in ALL_SPIRITS if x.id == spirit_id)
    return f"已从 {t.name} 卸下 {slot}·{eq.name}，已回到仓库。"


def resolve_equipment_uid(state: GameState, token: str) -> tuple[Optional[str], Optional[str]]:
    """按完整 uid 或前缀解析装备。返回 (uid, 错误信息)。"""
    token = token.strip()
    if token in state.equipment:
        return token, None
    matches = [u for u in state.equipment if u.startswith(token)]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, f"短 id「{token}」匹配到多件装备，请写更长前缀。"
    return None, f"找不到装备：{token}"


def delete_equipment(state: GameState, eq_uid: str) -> str:
    """删除装备；若已装备则先自动从精灵身上卸下。"""
    uid, err = resolve_equipment_uid(state, eq_uid)
    if err:
        return err
    assert uid is not None
    state.ensure_spirits()
    eq = state.equipment[uid]
    label = f"[{uid[:8]}] {eq.slot}·{eq.name}"
    if eq.equipped_spirit_id:
        spirit_id = eq.equipped_spirit_id
        state.loadouts[spirit_id][eq.slot] = None
        eq.equipped_spirit_id = None
    del state.equipment[uid]
    return f"已删除 {label}。"
    token = token.strip()
    if token in {t.id for t in ALL_SPIRITS}:
        return token
    try:
        i = int(token)
        if 1 <= i <= len(ALL_SPIRITS):
            return ALL_SPIRITS[i - 1].id
    except ValueError:
        pass
    for t in ALL_SPIRITS:
        if t.name == token:
            return t.id
    return None


def save_state(state: GameState) -> None:
    payload = {
        "equipment": {
            uid: {
                **asdict(eq),
                "affixes": [asdict(a) for a in eq.affixes],
            }
            for uid, eq in state.equipment.items()
        },
        "loadouts": state.loadouts,
    }
    SAVE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> GameState:
    state = GameState()
    state.ensure_spirits()
    if not SAVE_PATH.exists():
        return state
    data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
    for uid, raw in data.get("equipment", {}).items():
        affixes = [Affix(**a) for a in raw["affixes"]]
        state.equipment[uid] = Equipment(
            uid=uid,
            slot=raw["slot"],
            name=raw["name"],
            affixes=affixes,
            upgrades_left=raw.get("upgrades_left", 0),
            equipped_spirit_id=raw.get("equipped_spirit_id"),
        )
    state.loadouts = data.get("loadouts", {})
    state.ensure_spirits()
    return state


def print_help() -> None:
    print(
        """
命令：
  刷 <部位>          刷一件装备入仓库（头饰 / 护甲 / 鞋子 / 武器）
  仓库               列出未装备的装备
  精灵               列出精灵与已装部位
  查看 <精灵>        查看精灵面板（序号 / id / 中文名）
  装备 <装备id> <精灵>   将仓库装备装给精灵（部位由装备决定）
  卸下 <精灵> <部位>     卸下回仓库
  升级 <装备id>      消耗 1 次升级机会（已装备也可升）
  删除 <装备id>      永久删除装备（已装备会先卸下）
  保存 / 读取        手动存盘 / 重载
  帮助               显示本页
  退出               保存并退出
精灵可用序号 1–{n}、template_id（如 guifashi）或中文名。
""".format(n=len(ALL_SPIRITS)).strip()
    )


def cmd_loop() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    state = load_state()
    print("局外装备养成模拟（存档：equipment_demo_save.json）")
    print_help()

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            save_state(state)
            break
        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()

        if cmd in ("退出", "quit", "q", "exit"):
            save_state(state)
            print("已保存，再见。")
            break

        if cmd in ("帮助", "help", "h", "?"):
            print_help()
            continue

        if cmd in ("保存", "save"):
            save_state(state)
            print(f"已保存到 {SAVE_PATH}")
            continue

        if cmd in ("读取", "load"):
            state = load_state()
            print("已读取存档。")
            continue

        if cmd in ("刷", "farm", "drop"):
            if len(parts) < 2:
                print(f"请指定部位：{' / '.join(SLOTS)}")
                continue
            slot = parts[1]
            if slot not in SLOTS:
                print(f"未知部位：{slot}")
                continue
            eq = create_equipment(slot)
            state.equipment[eq.uid] = eq
            save_state(state)
            print(f"获得新装备：{eq.summary()}")
            continue

        if cmd in ("仓库", "inv", "inventory", "列表"):
            inv = state.inventory()
            if not inv:
                print("仓库为空，用「刷 <部位>」获取装备。")
            else:
                print(f"仓库（{len(inv)} 件）：")
                for eq in inv:
                    print(f"  {eq.summary()}")
            continue

        if cmd in ("精灵", "spirits"):
            state.ensure_spirits()
            print("精灵列表：")
            for i, t in enumerate(ALL_SPIRITS, 1):
                slots = state.loadouts[t.id]
                worn = [s for s in SLOTS if slots[s]]
                worn_txt = "、".join(worn) if worn else "无"
                print(f"  {i:2}. {t.name} ({t.id})  已装：{worn_txt}")
            continue

        if cmd in ("查看", "show", "panel"):
            if len(parts) < 2:
                print("用法：查看 <精灵>")
                continue
            sid = resolve_spirit_id(parts[1])
            if not sid:
                print("找不到该精灵。")
                continue
            print(spirit_panel(sid, state))
            continue

        if cmd in ("装备", "equip", "wear"):
            if len(parts) < 3:
                print("用法：装备 <装备id> <精灵>")
                continue
            sid = resolve_spirit_id(parts[2])
            if not sid:
                print("找不到该精灵。")
                continue
            msg = equip(state, parts[1], sid)
            save_state(state)
            print(msg)
            continue

        if cmd in ("卸下", "unequip"):
            if len(parts) < 3:
                print("用法：卸下 <精灵> <部位>")
                continue
            sid = resolve_spirit_id(parts[1])
            if not sid:
                print("找不到该精灵。")
                continue
            msg = unequip(state, sid, parts[2])
            save_state(state)
            print(msg)
            continue

        if cmd in ("升级", "upgrade", "up"):
            if len(parts) < 2:
                print("用法：升级 <装备id>")
                continue
            uid, err = resolve_equipment_uid(state, parts[1])
            if err:
                print(err)
                continue
            assert uid is not None
            msg = upgrade_equipment(state.equipment[uid])
            save_state(state)
            print(msg)
            continue

        if cmd in ("删除", "delete", "del"):
            if len(parts) < 2:
                print("用法：删除 <装备id>")
                continue
            msg = delete_equipment(state, parts[1])
            save_state(state)
            print(msg)
            continue

        print("未知命令，输入「帮助」查看。")


def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            # 非交互：快速演示刷装 + 装配
            sys.stdout.reconfigure(encoding="utf-8")
            state = GameState()
            state.ensure_spirits()
            for slot in SLOTS:
                eq = create_equipment(slot)
                state.equipment[eq.uid] = eq
                equip(state, eq.uid, "guifashi")
            print(spirit_panel("guifashi", state))
            return
        if sys.argv[1] in ("--gui", "-g"):
            scripts_dir = Path(__file__).resolve().parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            from roll_equipment_gui import main as gui_main

            gui_main()
            return
    cmd_loop()


if __name__ == "__main__":
    main()
