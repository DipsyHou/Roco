"""Shared desktop UI constants."""

from __future__ import annotations

from typing import Dict

DEFAULT_P1 = ["flora", "clawdragon", "guifashi"]
DEFAULT_P2 = ["starweaver", "steamdragon", "qiuka"]
UI_FONT = ("Microsoft YaHei UI", 10)
UI_FONT_TITLE = ("Microsoft YaHei UI", 11, "bold")
UI_FONT_BADGE = ("Microsoft YaHei UI", 8, "bold")
UI_MONO_FONT = ("Consolas", 10)

# Avatar PNG basename by template id (stable even if display name encoding breaks).
AVATAR_BY_TEMPLATE_ID: Dict[str, str] = {
    "flora": "蹦蹦种子",
    "clawdragon": "上古战龙",
    "chaosling": "梦想龙",
    "starweaver": "黑猫巫师",
    "steamdragon": "蒸汽神龙",
    "qiuka": "裘卡",
    "fanying": "凡鹰",
    "tita": "缇塔",
    "guifashi": "诡法师",
    "cuiding": "翠顶夫人",
    "xiaozong": "小琮",
    "daermao": "大耳帽兜",
    "bahamut": "巴哈姆特",
    "huxian": "尖嘴狐仙",
    "parsas": "帕尔萨斯",
    "shengyu": "圣域祭司",
    "deerle": "梅花德尔勒",
    "tengjiao": "藤椒小巴",
}

# Corner-mark PNG stem under ``assets/marks/`` (same stem as portrait when shared).
MARK_BY_TEMPLATE_ID: Dict[str, str] = {
    "flora": "蹦蹦种子",
    "deerle": "梅花德尔勒",
    "parsas": "秘能",
    "starweaver": "秘能",
    "shengyu": "秘能",
}
