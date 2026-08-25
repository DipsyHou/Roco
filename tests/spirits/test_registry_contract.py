from __future__ import annotations

from roco.core.spirits import ALL_SPIRITS, get_spirit_logic


def test_every_template_has_logic_and_unique_skills():
    for template in ALL_SPIRITS:
        logic = get_spirit_logic(template.id)
        assert logic is not None, template.id
        assert logic.template_id == template.id
        # 部分精灵将技能改为被动（如梅花鹿「敏锐」、石化刺蜥蜴），故下限为 2。
        assert len(template.skills) >= 2, template.id
        assert len({skill.id for skill in template.skills}) == len(template.skills)
