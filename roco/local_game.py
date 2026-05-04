"""Local hot-seat battle — two players share one terminal."""

from __future__ import annotations

import os
import sys
import uuid
from typing import Dict, List, Optional

from .battle_types import (
    ActionType,
    BattleEffect,
    BattleLogType,
    BattlePhase,
    BattleSpirit,
    EffectType,
)
from .engine import BattleEngine
from .spirits import ALL_SPIRITS, get_spirit_template


def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _wait(msg: str = "Press Enter to continue...") -> str:
    return input(f"\n{msg}")


def _divider(char: str = "─", width: int = 64) -> str:
    return char * width


# ============================================================
# 效果文本（无需 JSON 编解码）
# ============================================================

_STAT_NAMES: Dict[str, str] = {
    "atk": "物攻", "magAtk": "魔攻", "def": "物防",
    "magDef": "魔防", "speed": "速度", "hp": "HP",
}

_SKILL_NAMES: Dict[str, str] = {
    "flora_skill1": "急救", "flora_skill2": "止痛", "flora_skill3": "绷带束缚",
    "clawdragon_skill1": "利爪强化", "clawdragon_skill2": "震慑之击", "clawdragon_skill3": "狂龙裂地",
    "chaosling_skill1": "狂暴蓄力", "chaosling_skill2": "混沌风暴", "chaosling_skill3": "命运反转",
    "starweaver_skill1": "星能脉冲", "starweaver_skill2": "净化之光", "starweaver_skill3": "星能爆发",
}

_SPIRIT_ICONS: Dict[str, str] = {
    "芙萝拉": "🌸", "锐爪龙": "🐉", "混沌灵": "🌀", "星能使": "⭐",
}


def _effect_text(eff: BattleEffect) -> str:
    turns = (
        f"({eff.remaining_turns}回合)"
        if 0 < eff.remaining_turns < 900
        else "(持续)" if eff.remaining_turns == -1 else ""
    )
    t = eff.type
    if t == EffectType.stat_percent_modify:
        stat = _STAT_NAMES.get(eff.stat_type.value if eff.stat_type else "", "?")
        pct = abs(int((eff.value or 0) * 100))
        arrow = "↑" if (eff.value or 0) >= 0 else "↓"
        return f"{stat}{arrow}{pct}%{turns}"
    if t == EffectType.stat_flat_modify:
        stat = _STAT_NAMES.get(eff.stat_type.value if eff.stat_type else "", "?")
        return f"{stat}{'↑' if (eff.value or 0)>=0 else '↓'}{abs(int(eff.value or 0))}{turns}"
    if t == EffectType.stun:
        return f"💫眩晕{turns}"
    if t == EffectType.damage_modify:
        sub = (eff.damage_modify_sub_type.value if eff.damage_modify_sub_type else "")
        if "increase" in sub:
            return f"增伤{turns}"
        if "decrease" in sub:
            return f"减伤{turns}"
        return f"伤害修正{turns}"
    if t == EffectType.attack_enhance:
        et = eff.enhance_type
        if et == "magic_damage": return f"利爪强化{turns}"
        if et == "stun": return "震慑蓄力"
        if et == "aoe": return "裂地蓄力"
        return f"普攻强化{turns}"
    if t == EffectType.next_damage_reduction:
        pct = int((eff.reduction_percent or 0) * 100)
        return f"止痛({pct}%减伤)"
    if t == EffectType.debuff_immunity:
        return f"🛡免疫负面{turns}"
    if t == EffectType.channeling_skill:
        p = max(1, eff.channel_phase or 0)
        return f"蓄力中({p}/3)"
    return f"效果{turns}"


# ============================================================
# 显示
# ============================================================

def _hp_bar(current: int, max_hp: int, width: int = 14) -> str:
    pct = max(0, current / max_hp) if max_hp > 0 else 0
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {current}/{max_hp}"


def _print_spirit(s: BattleSpirit, hide_effects: bool = False) -> None:
    icon = _SPIRIT_ICONS.get(s.name, "❓")
    stunned = any(e.type == EffectType.stun for e in s.effects)
    status = " 💫STUN" if stunned else ""
    energy_str = f" ⚡{s.energy}" if s.energy is not None else ""
    flora_str = ""
    if s.template_id == "flora":
        flora_str = " 🔴被动已用" if s.passive_triggered else " 🟢被动可用"

    print(f"  {icon} {s.name}{status}{energy_str}{flora_str}  {_hp_bar(s.current_hp, s.max_hp)}")
    if not hide_effects and s.effects:
        tags = [_effect_text(e) for e in s.effects]
        print(f"    effects: {', '.join(tags)}")


def _display_state(
    eng: BattleEngine,
    pid: str,
    turn: int,
    phase: BattlePhase,
) -> None:
    opp_id = next(p for p in eng.state.players if p != pid)

    st = eng.get_visible_state(pid)
    my_data = st.players[pid]
    opp_data = st.players.get(opp_id)

    my_field = [s for s in my_data.spirits if s.is_on_field and s.is_alive]
    my_bench = [s for s in my_data.spirits if not s.is_on_field and s.is_alive]
    opp_field = [s for s in (opp_data.spirits if opp_data else []) if s.is_on_field and s.is_alive]
    opp_bench = [s for s in (opp_data.spirits if opp_data else []) if not s.is_on_field and s.is_alive]

    print()
    print(_divider("═"))
    print(f"  Round {turn}  |  Phase: {phase.value}")
    print(_divider("═"))

    print(f"\n  {'─'*28} 我方 {'─'*28}")
    if my_field:
        for s in my_field:
            _print_spirit(s)
    else:
        print("  (无场上精灵)")

    if my_bench:
        print(f"\n  [后备]")
        for s in my_bench:
            _print_spirit(s)

    print(f"\n  {'─'*28} 敌方 {'─'*28}")
    if opp_field:
        for s in opp_field:
            _print_spirit(s)
    else:
        print("  (无场上精灵)")

    if opp_bench:
        print(f"\n  [后备]")
        for s in opp_bench:
            _print_spirit(s, hide_effects=True)


def _display_logs(eng: BattleEngine, *, last: int = 10) -> None:
    logs = eng.state.battle_log
    if not logs:
        return
    print(f"\n  {'─'*28} 战斗日志 {'─'*28}")
    for lg in logs[-last:]:
        tag = lg.type.value
        print(f"  [R{lg.turn}][{tag}] {lg.message}")


# ============================================================
# 阵容选择
# ============================================================

def _select_team(player_num: int) -> List:
    _clear()
    print()
    print(_divider("═"))
    print(f"  Player {player_num} — 选择 4 只精灵")
    print(_divider("═"))
    print()
    print("  可用精灵：")
    print()
    for i, t in enumerate(ALL_SPIRITS, 1):
        bs = t.base_stats
        icon = _SPIRIT_ICONS.get(t.name, "❓")
        print(f"  [{i}] {icon} {t.name} ({t.id})")
        print(f"      {t.description}")
        print(f"      HP:{bs.hp}  ATK:{bs.atk}  MATK:{bs.mag_atk}  DEF:{bs.def_}  MDEF:{bs.mag_def}  SPD:{bs.speed}")
        print(f"      被动: {t.passive_skill.name}")
        for sk in t.skills:
            cost = f"[能量:{sk.energy_cost}]" if sk.energy_cost is not None else f"[CD:{sk.cooldown}]"
            print(f"      技能: {sk.name} {cost} — {sk.description}")
        print()

    while True:
        raw = input("  输入 4 个序号（空格分隔，如 1 2 3 4）: ").strip().split()
        if len(raw) != 4:
            print("  ⚠ 需要恰好 4 个序号！")
            continue
        templates = []
        ok = True
        for s in raw:
            try:
                idx = int(s) - 1
                if not (0 <= idx < len(ALL_SPIRITS)):
                    print(f"  ⚠ 序号超出范围: {s}")
                    ok = False
                    break
                templates.append(ALL_SPIRITS[idx])
            except ValueError:
                print(f"  ⚠ 无效序号: {s}")
                ok = False
                break
        if ok:
            print(f"\n  ✅ 已选择: {', '.join(t.name for t in templates)}")
            _wait()
            return templates


# ============================================================
# 首发选择
# ============================================================

def _select_starters(player_num: int, eng: BattleEngine, pid: str) -> List[str]:
    _clear()
    st = eng.get_visible_state(pid)
    spirits = st.players[pid].spirits

    print()
    print(_divider("═"))
    print(f"  Player {player_num} — 选择首发精灵（1~4 只）")
    print(_divider("═"))
    print()
    print("  你的精灵：")
    for i, s in enumerate(spirits, 1):
        bs = s.base_stats
        icon = _SPIRIT_ICONS.get(s.name, "❓")
        print(f"  [{i}] {icon} {s.name}  HP:{s.current_hp}  ATK:{bs.atk}  SPD:{bs.speed}  ID:{s.unique_id[:8]}...")

    while True:
        raw = input("\n  输入编号（空格分隔，1~4 个）: ").strip().split()
        try:
            idxes = [int(x) - 1 for x in raw]
        except ValueError:
            print("  ⚠ 请输入数字编号！")
            continue
        if not (1 <= len(idxes) <= 4):
            print("  ⚠ 请选择 1 到 4 个！")
            continue
        if any(i < 0 or i >= len(spirits) for i in idxes):
            print("  ⚠ 编号超出范围！")
            continue
        starter_ids = [spirits[i].unique_id for i in idxes]
        print(f"\n  ✅ 已选择 {len(starter_ids)} 只首发")
        _wait()
        return starter_ids


# ============================================================
# 行动输入
# ============================================================

def _get_action(eng: BattleEngine, pid: str) -> dict:
    """获取一个玩家的回合行动."""
    st = eng.state
    pd = st.players[pid]
    field = [s for s in pd.spirits if s.is_on_field and s.is_alive]
    bench = [s for s in pd.spirits if not s.is_on_field and s.is_alive]

    if not field:
        print("\n  ⚠ 你场上没有存活的精灵，只能上场或跳过。")
        return _action_deploy_or_skip(pid, bench)

    # 选择行动精灵
    print()
    print("  选择行动精灵：")
    for i, s in enumerate(field, 1):
        stunned = any(e.type == EffectType.stun for e in s.effects)
        tag = " [STUN]" if stunned else ""
        print(f"    [{i}] {_SPIRIT_ICONS.get(s.name,'❓')} {s.name}{tag}  ID:{s.unique_id[:8]}...")

    print(f"    [d] 上场后备精灵")
    print(f"    [s] 跳过本回合")

    while True:
        sel = input("  > ").strip().lower()
        if sel == "s":
            return {"type": "skip", "playerId": pid}
        if sel == "d":
            if not bench:
                print("  ⚠ 没有可上场的后备精灵！")
                continue
            return _action_deploy_or_skip(pid, bench)

        try:
            idx = int(sel) - 1
            if 0 <= idx < len(field):
                actor = field[idx]
                return _choose_action_type(eng, pid, actor, field, bench)
        except ValueError:
            pass
        print("  ⚠ 无效选择！")


def _action_deploy_or_skip(pid: str, bench: List[BattleSpirit]) -> dict:
    if not bench:
        return {"type": "skip", "playerId": pid}
    print("  选择上场的精灵：")
    for i, s in enumerate(bench, 1):
        print(f"    [{i}] {s.name}  ID:{s.unique_id[:8]}...  {_hp_bar(s.current_hp, s.max_hp)}")
    print("    [s] 跳过")
    while True:
        sel = input("  > ").strip().lower()
        if sel == "s":
            return {"type": "skip", "playerId": pid}
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(bench):
                return {"type": "deploy", "playerId": pid, "deployId": bench[idx].unique_id}
        except ValueError:
            pass
        print("  ⚠ 无效选择！")


def _choose_action_type(
    eng: BattleEngine,
    pid: str,
    actor: BattleSpirit,
    field: List[BattleSpirit],
    bench: List[BattleSpirit],
) -> dict:
    """选择行动类型（普攻/技能/下场/换人）."""
    stunned = any(e.type == EffectType.stun for e in actor.effects)
    tpl = get_spirit_template(actor.template_id)
    skills = tpl.skills if tpl else []

    while True:
        print(f"\n  ── {_SPIRIT_ICONS.get(actor.name,'❓')} {actor.name} 的行动 ──")
        if stunned:
            print("  ⚠ 精灵处于眩晕状态，只能下场/换人/跳过！")
        else:
            print("  [a] 普攻 — 对一名敌人造成物攻伤害")
        for i, sk in enumerate(skills):
            name = _SKILL_NAMES.get(sk.id, sk.name)
            available, reason = _skill_available(actor, sk)
            if available and not stunned:
                print(f"  [{i+1}] {name} — {sk.description}")
            else:
                print(f"  [{i+1}] {name} — {reason}")
        print("  [w] 下场")
        if bench:
            print("  [k] 换人（下场+上场）")
        print("  [x] 返回")

        cmd = input("  > ").strip().lower()
        if cmd == "x":
            return _get_action(eng, pid)  # 重新选精灵
        if cmd == "a":
            if stunned:
                print("  ⚠ 眩晕中无法普攻！")
                continue
            tid = _pick_target(eng, pid, "enemy_field")
            return {"type": "normal_attack", "playerId": pid, "actorId": actor.unique_id, "targetId": tid}
        if cmd == "w":
            return {"type": "withdraw", "playerId": pid, "withdrawId": actor.unique_id}
        if cmd == "k":
            if not bench:
                print("  ⚠ 无后备精灵！")
                continue
            dep_id = _pick_bench(pid, bench)
            return {"type": "swap", "playerId": pid, "withdrawId": actor.unique_id, "deployId": dep_id}
        try:
            si = int(cmd) - 1
            if 0 <= si < len(skills):
                sk = skills[si]
                available, reason = _skill_available(actor, sk)
                if not available or stunned:
                    print(f"  ⚠ {reason}")
                    continue
                tid = _pick_skill_target(eng, pid, sk, actor)
                act: dict = {
                    "type": "use_skill",
                    "playerId": pid,
                    "actorId": actor.unique_id,
                    "skillId": sk.id,
                }
                if tid:
                    act["targetId"] = tid
                return act
        except ValueError:
            pass
        print("  ⚠ 无效选择！")


def _skill_available(actor: BattleSpirit, sk) -> tuple:
    """(available, reason)."""
    if actor.template_id == "starweaver":
        ec = sk.energy_cost
        if ec is not None:
            if ec == -1:
                if (actor.energy or 0) <= 0:
                    return False, "能量不足"
            elif ec > 0:
                if (actor.energy or 0) < ec:
                    return False, f"需要{ec}能量"
        return True, ""
    cd = actor.skill_cooldowns.get(sk.id, 0)
    if cd > 0:
        return False, f"CD {cd}回合"
    return True, ""


def _pick_target(eng: BattleEngine, pid: str, mode: str) -> str:
    """选择一个目标精灵 ID."""
    opp_id = next(p for p in eng.state.players if p != pid)
    opp_data = eng.state.players[opp_id]
    pd = eng.state.players[pid]

    if mode == "enemy_field":
        targets = [s for s in opp_data.spirits if s.is_on_field and s.is_alive]
    elif mode == "enemy_any":
        targets = [s for s in opp_data.spirits if s.is_alive]
    elif mode == "ally_field":
        targets = [s for s in pd.spirits if s.is_on_field and s.is_alive]
    elif mode == "ally_any":
        targets = [s for s in pd.spirits if s.is_alive]
    elif mode == "any_field":
        f1 = [s for s in pd.spirits if s.is_on_field and s.is_alive]
        f2 = [s for s in opp_data.spirits if s.is_on_field and s.is_alive]
        targets = f1 + f2
    else:
        targets = [s for s in opp_data.spirits if s.is_on_field and s.is_alive]

    if not targets:
        if mode == "enemy_field":
            targets = [s for s in opp_data.spirits if s.is_alive]
        else:
            print("  ⚠ 没有可选目标！")
            return ""

    print(f"\n  选择目标 ({len(targets)} 个):")
    for i, t in enumerate(targets, 1):
        side = "敌方" if t.owner_id != pid else "己方"
        print(f"    [{i}] {side} {t.name}  {_hp_bar(t.current_hp, t.max_hp)}  ID:{t.unique_id[:8]}...")
    print("    [x] 取消")

    while True:
        c = input("  > ").strip().lower()
        if c == "x":
            return ""
        try:
            idx = int(c) - 1
            if 0 <= idx < len(targets):
                return targets[idx].unique_id
        except ValueError:
            pass
        print("  ⚠ 无效选择！")


def _pick_skill_target(eng: BattleEngine, pid: str, sk, actor: BattleSpirit) -> Optional[str]:
    """按技能目标类型选目标."""
    tt = sk.target_type.value
    if tt in ("self", "none"):
        return None
    if tt == "all_enemies":
        return None
    if tt == "single_enemy":
        return _pick_target(eng, pid, "enemy_field")
    if tt == "single_ally":
        return _pick_target(eng, pid, "ally_any")
    if tt == "single_ally_on_field":
        return _pick_target(eng, pid, "ally_field")
    if tt == "any_on_field":
        return _pick_target(eng, pid, "any_field")
    return None


def _pick_bench(pid: str, bench: List[BattleSpirit]) -> str:
    print("\n  选择上场精灵：")
    for i, s in enumerate(bench, 1):
        print(f"    [{i}] {s.name}  {_hp_bar(s.current_hp, s.max_hp)}  ID:{s.unique_id[:8]}...")
    print("    [x] 取消")
    while True:
        c = input("  > ").strip().lower()
        if c == "x":
            return ""
        try:
            idx = int(c) - 1
            if 0 <= idx < len(bench):
                return bench[idx].unique_id
        except ValueError:
            pass
        print("  ⚠ 无效选择！")


# ============================================================
# 主流程
# ============================================================

class LocalGame:
    def __init__(self) -> None:
        self.p1 = "p1"
        self.p2 = "p2"
        self.eng: Optional[BattleEngine] = None

    def run(self) -> None:
        _clear()
        print()
        print(_divider("═"))
        print("            Roco · 回合制精灵对战（本地热坐）")
        print(_divider("═"))
        _wait()

        # ── 阵容选择 ──
        p1_team = _select_team(1)
        p2_team = _select_team(2)

        # ── 创建引擎 ──
        self.eng = BattleEngine(
            battle_id=str(uuid.uuid4()),
            player1_id=self.p1,
            player2_id=self.p2,
            p1_templates=p1_team,
            p2_templates=p2_team,
        )

        # ── 首发选择 ──
        st1 = _select_starters(1, self.eng, self.p1)
        self.eng.select_starters(self.p1, st1)

        st2 = _select_starters(2, self.eng, self.p2)
        self.eng.select_starters(self.p2, st2)

        # ── 战斗循环 ──
        self._battle_loop()

    def _battle_loop(self) -> None:
        eng = self.eng
        if not eng:
            return

        while eng.state.phase != BattlePhase.finished:
            # P1 行动
            if eng.state.phase == BattlePhase.waiting_for_actions:
                self._player_turn(1, self.p1)
            if eng.state.phase == BattlePhase.finished:
                break

            _clear()
            _wait("已隐藏 Player 1 的输入。Player 2 请按 Enter...")

            # P2 行动
            if eng.state.phase == BattlePhase.waiting_for_actions:
                self._player_turn(2, self.p2)
            if eng.state.phase == BattlePhase.finished:
                break

            # 展示回合结果
            _clear()
            self._show_turn_result()
            _wait()

        # 战斗结束
        _clear()
        self._show_end()

    def _player_turn(self, player_num: int, pid: str) -> None:
        eng = self.eng
        if not eng or eng.state.phase != BattlePhase.waiting_for_actions:
            return

        _clear()
        _display_state(eng, pid, eng.state.current_turn, eng.state.phase)
        print(f"\n  ▶ Player {player_num} 的回合")

        action = _get_action(eng, pid)
        turn_before = eng.state.current_turn
        eng.submit_action(pid, action)

        if eng.state.phase == BattlePhase.waiting_for_actions and eng.state.current_turn == turn_before:
            print("\n  ✅ 行动已提交，等待对手...")
        elif eng.state.phase == BattlePhase.finished:
            return

    def _show_turn_result(self) -> None:
        eng = self.eng
        if not eng:
            return
        st = eng.state
        print()
        print(_divider("═"))
        print(f"  Round {st.current_turn} 结果")
        print(_divider("═"))

        # 展示双方场上状态（使用 P1 视角，简化）
        for pid in [self.p1, self.p2]:
            vis = eng.get_visible_state(pid)
            pd = vis.players[pid]
            label = "Player 1" if pid == self.p1 else "Player 2"
            print(f"\n  [{label}]")
            for s in pd.spirits:
                if s.is_alive:
                    side = "场上" if s.is_on_field else "后备"
                    _print_spirit(s, hide_effects=(not s.is_on_field and pid != pid))

        _display_logs(eng, last=15)

    def _show_end(self) -> None:
        eng = self.eng
        if not eng:
            return
        wid = eng.state.winner_id
        label = "Player 1 🏆" if wid == self.p1 else "Player 2 🏆"
        print()
        print(_divider("═"))
        print(f"          战斗结束！{label} 获胜！")
        print(_divider("═"))
        print()
        _display_logs(eng, last=20)
        print()
        _wait("按 Enter 退出...")


def main() -> None:
    try:
        LocalGame().run()
    except KeyboardInterrupt:
        print("\n\n已退出。")
        sys.exit(0)
    except EOFError:
        print("\n\n已退出。")
        sys.exit(0)
