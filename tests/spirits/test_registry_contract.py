from __future__ import annotations

from roco.core.spirits import ALL_SPIRITS, get_spirit_logic


def test_every_template_has_logic_and_three_skills():
    for template in ALL_SPIRITS:
        logic = get_spirit_logic(template.id)
        assert logic is not None, template.id
        assert logic.template_id == template.id
        assert len(template.skills) >= 3
        assert len({skill.id for skill in template.skills}) == len(template.skills)
