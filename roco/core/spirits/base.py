"""Spirit hooks (timing) and modifiers (queries) — base class for all spirits."""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..battle.actions import ActionDict
from ..battle.context import BattleContext
from ..battle.events import DamageEvent
from ..battle.types import BattleSpirit, StatType, TargetType

__all__ = ["BattleContext", "SpiritLogic"]


class SpiritLogic:
    """Override only the hooks and modifiers your spirit needs.

    Skill dispatch: set ``SKILLS = {"skill_id": "_skill_method"}`` and implement
    each handler as ``(self, ctx, player_id, actor, action)``. The default
    ``execute_skill`` looks up the table; do not hand-write ``if sk == ...`` chains.
    """

    template_id: str
    SKILLS: ClassVar[Dict[str, str]] = {}

    # --- lifecycle ---

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        pass

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        pass

    # --- turn phases (see turn_pipeline.py for the begin/act/end order) ---

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        """Actor's turn begins (burn/poison already applied). Runs even if stunned."""
        pass

    def on_turn_end(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
        *,
        stunned: bool = False,
    ) -> None:
        """Actor's turn ends (before default duration tick). Runs even if stunned."""
        pass

    def on_ally_turn_start(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        actor: BattleSpirit,
    ) -> None:
        """Ally ``actor``'s normal turn begins (mirrors ``on_ally_turn_end``).

        Runs even if ``actor`` is stunned, right after ``actor.on_turn_start``.
        Called for every living spirit on ``actor``'s team, including ``actor``
        itself (``observer is actor``) — same convention as ``on_ally_turn_end``.
        Implementations should filter by ``observer.template_id`` and check
        ``observer is not actor`` if they want teammates only.
        """
        pass

    def on_ally_turn_end(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        actor: BattleSpirit,
    ) -> None:
        """Ally ``actor`` finished a turn."""
        pass

    def on_team_energy_spent(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        amount: int,
        spender: BattleSpirit,
    ) -> None:
        """Team energy was spent by ``spender`` (``amount`` points)."""
        pass

    def on_after_actor_acts(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        """After ``ACTION_GAP`` is added to ``actor.charge`` at turn end."""
        pass

    # --- damage observers ---

    def adjust_incoming_damage(self, spirit: BattleSpirit, damage: int) -> int:
        """Last-chance mutation before HP reduction (rare; prefer damage pipeline hooks)."""
        return damage

    def apply_passive_flat_mitigation(self, spirit: BattleSpirit, damage: float) -> float:
        """Passive flat reduction on this segment, after ``BattleEffect`` flat mods.

        Called from ``calculate_damage``; return the remaining damage. May mutate
        ``spirit`` (e.g. stack resources). Default is a no-op.
        """
        return damage

    def get_damage_share_for_ally(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        ally: BattleSpirit,
        segment_amount: int,
    ) -> int:
        """How much of ``ally``'s incoming segment ``observer`` absorbs (pre-shield)."""
        del ctx, observer, ally, segment_amount
        return 0

    def on_death(
        self,
        spirit: BattleSpirit,
        ctx: Optional[BattleContext] = None,
    ) -> bool:
        """Called right after ``spirit`` drops to 0 HP (``is_alive`` already False).

        Return True to cancel the death (revive); implementations must restore
        ``current_hp`` and ``is_alive`` themselves. Default keeps the spirit dead.
        """
        return False

    def on_damage(self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent) -> None:
        """Any damage on the field."""
        pass

    def on_ally_damage_dealt(
        self, ctx: BattleContext, observer: BattleSpirit, event: DamageEvent
    ) -> None:
        """Ally dealt damage (``event.attacker`` is on observer's team)."""
        pass

    def on_ally_action(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> None:
        """Teammate ``actor`` finished a normal attack or skill (not self)."""
        pass

    def on_became_sole_target(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        action: ActionDict,
    ) -> None:
        """Called when ``spirit`` is the sole designated target of a NA/skill.

        Fires after that action resolves. AOE / no-target skills do not count.
        Includes self-targeted skills (the actor is the sole target).
        """
        pass

    def on_attack(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: ActionDict,
        targets: List[BattleSpirit],
    ) -> None:
        """Called once when ``actor`` launches an attack against enemy target(s).

        Fires after that action's own damage segments. Multi-hit skills still count
        as one launch. Not used for ally/self skills or non-attack actions.
        """
        pass

    def on_ally_attack(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        actor: BattleSpirit,
        action: ActionDict,
        targets: List[BattleSpirit],
    ) -> None:
        """Teammate ``actor`` launched an attack against enemy target(s).

        Fires after the teammate action's own damage segments.
        """
        pass

    def on_attack_hit(
        self,
        ctx: BattleContext,
        player_id: str,
        attacker: BattleSpirit,
        target: BattleSpirit,
        damage: int,
    ) -> None:
        """Attacker hit target with attack or skill damage."""
        pass

    def on_spirit_defeated(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        defeated: BattleSpirit,
    ) -> None:
        pass

    def on_passive_check(self, ctx: BattleContext, player_id: str) -> None:
        """After a turn ends — scan team for conditional passives."""
        pass

    def suppress_skill_use_log(self, actor: BattleSpirit, skill) -> bool:
        """Return True to skip the engine default \"使用了 XX！\" log."""
        return False

    def can_execute_action(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: ActionDict,
        *,
        in_extra_action: bool,
        stunned: bool,
    ) -> Optional[tuple]:
        """Return (allowed, reason) to override default action validation.

        ``in_extra_action`` 表示当前正处在某个 ExtraActionSlot 里；
        基础合法性应优先靠 slot 的 policy 表达，这里只用于精灵特有的硬约束。
        """
        return None

    def preview_action(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> Optional[bool]:
        """Handle a non-consuming pre-submit action for multi-step skills.

        Return ``True`` or ``False`` when this logic recognizes and fully handles
        the preview action. Return ``None`` to let the engine continue with normal
        submission. Preview actions must not advance the turn.
        """
        return None

    def on_action_end(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
        *,
        stunned: bool,
    ) -> None:
        """After the actor's action resolves, before turn-end bookkeeping."""
        pass

    # --- actions ---

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> None:
        """Dispatch via ``SKILLS`` (skill_id -> method name)."""
        name = type(self).SKILLS.get(action.get("skillId") or "")
        if name:
            getattr(self, name)(ctx, player_id, actor, action)

    def execute_normal_attack(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> bool:
        """Return True to skip engine default normal attack."""
        return False

    # --- modifiers (queries, not timing) ---

    def can_use_skill(self, spirit: BattleSpirit, skill) -> Optional[tuple]:
        return None

    def consume_skill_resources(self, spirit: BattleSpirit, skill) -> None:
        pass

    def should_use_team_energy(self, spirit: BattleSpirit, skill) -> bool:
        return True

    def get_skill_energy_cost(self, spirit: BattleSpirit, skill, base_cost: int) -> int:
        """Override to adjust a skill's team-energy cost dynamically."""
        return base_cost

    def get_skill_target_type(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        skill,
    ) -> Optional[TargetType]:
        """Override skill ``target_type`` for UI / AI (e.g. dish-dependent skills).

        Return ``None`` to keep the template declaration.
        """
        return None

    def get_attack_launch_targets(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: ActionDict,
        skill,
    ) -> Optional[List[BattleSpirit]]:
        """Override whether / whom this skill use launches an attack against.

        Return ``None`` to keep the default ``SkillDef.launches_attack`` + target-type
        rules. Return a non-empty list to launch against those enemies; return ``[]``
        to explicitly not launch (e.g. card skills whose face has no damage).
        """
        return None

    def get_damage_reduction(self, spirit: BattleSpirit) -> float:
        return 0.0

    def get_incoming_damage_reduction(
        self, spirit: BattleSpirit, damage_type: "DamageType"
    ) -> float:
        """按伤害类型区分的受到伤害减免（如仅减固定伤害）。加到该类型的减伤上。"""
        return 0.0

    def get_crit_rate_bonus(
        self, spirit: BattleSpirit, target: Optional[BattleSpirit] = None
    ) -> float:
        """Additive crit rate (0.25 = +25%)."""
        return 0.0

    def get_crit_damage_bonus(
        self, spirit: BattleSpirit, target: Optional[BattleSpirit] = None
    ) -> float:
        """Additive crit damage percent points (40 = +40% on top of base 150%)."""
        return 0.0

    def get_stat_percent_bonus(self, spirit: BattleSpirit, stat: StatType) -> float:
        return 0.0

    def get_aura_stat_percent_bonus(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        target: BattleSpirit,
        stat: StatType,
    ) -> float:
        return 0.0

    def get_aura_damage_percent_bonus(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        spirit: BattleSpirit,
    ) -> float:
        """``source`` 为同队的 ``spirit`` 提供的「造成伤害提高」光环（加性叠加）。"""
        return 0.0

    def get_aura_taken_damage_reduction(
        self,
        ctx: BattleContext,
        source: BattleSpirit,
        spirit: BattleSpirit,
    ) -> float:
        """``source`` 为同队的 ``spirit`` 提供的「受到伤害降低」光环（加性叠加）。"""
        return 0.0

    def get_team_energy_cap_bonus(self, ctx: BattleContext, spirit: BattleSpirit) -> int:
        return 0

    def get_ally_energy_gain_bonus(
        self, ctx: BattleContext, observer: BattleSpirit, gainer: BattleSpirit
    ) -> int:
        """Extra personal-energy points ``gainer`` gets whenever it gains any.

        Queried by :func:`_combat.grant_personal_energy` across every living
        ally of ``gainer`` (including ``gainer`` itself). Return 0 unless this
        spirit amplifies teammates' energy gains (e.g. 圣域祭司的月盈).
        """
        return 0

    # --- UI description (presentation, not mechanics) ---
    #
    # Panels need to know how to *label* a spirit's resources and states. These
    # hooks keep that knowledge on the spirit instead of forcing every UI to
    # grow a ``template_id == "..."`` branch.

    def get_resource_label(self) -> Optional[str]:
        """Name of the personal resource replacing team energy, if any.

        Return e.g. ``"秘能"`` when this spirit pays from ``spirit.energy``
        rather than the shared pool. ``None`` means it uses team energy.
        """
        return None

    def describe_skill_cost(self, spirit: BattleSpirit, skill) -> Optional[str]:
        """Cost label for a skill button, or ``None`` for the team-energy default."""
        name = self.get_resource_label()
        if name is None:
            return None
        cost = skill.energy_cost
        if cost == self.SPEND_ALL_RESOURCE:
            return f"{name} 全部"
        return f"{name} {cost or 0}"

    def check_skill_resource(self, spirit: BattleSpirit, skill) -> Optional[tuple]:
        """Return ``(usable, reason)`` for the personal resource, else ``None``.

        ``None`` defers to the engine's team-energy check.
        """
        name = self.get_resource_label()
        if name is None:
            return None
        cost = skill.energy_cost
        if cost is None:
            return True, ""
        have = spirit.energy or 0
        if cost == self.SPEND_ALL_RESOURCE:
            return (False, f"{name}不足") if have <= 0 else (True, "")
        if cost > 0 and have < cost:
            return False, f"需要{cost}{name}"
        return True, ""

    def describe_extra_states(self, spirit: BattleSpirit) -> list:
        """Extra status-bar lines for state not stored as a ``BattleEffect``."""
        name = self.get_resource_label()
        if name is not None and isinstance(spirit.energy, int) and spirit.energy >= 0:
            return [f"[state]{name} - {spirit.energy}点"]
        return []

    def describe_avatar_badge(self, spirit: BattleSpirit) -> Optional[tuple]:
        """Pet-strip corner badge: ``(mark_basename, caption)`` or ``None``.

        ``mark_basename`` is the PNG stem under ``assets/marks/`` (e.g. ``梅花德尔勒``).
        ``caption`` is short text drawn beside the mark (e.g. ``4/12``).

        Default: 秘能 spirits show ``current/cap`` using the shared ``秘能`` mark.
        """
        if self.get_resource_label() == "秘能" and spirit.max_energy is not None:
            cur = max(0, int(spirit.energy or 0))
            cap = max(0, int(spirit.max_energy or 0))
            return ("秘能", f"{cur}/{cap}")
        return None

    def describe_detail_sections(self, spirit: BattleSpirit) -> list:
        """Extra sections for the detail panel, below the effect list.

        Returns ``[(title, [(label, value), ...]), ...]``. A ``value`` of
        ``None`` renders ``label`` alone as an empty-state line.
        """
        return []

    # Sentinel ``energy_cost`` meaning "spend the entire personal resource".
    SPEND_ALL_RESOURCE: ClassVar[int] = -1
