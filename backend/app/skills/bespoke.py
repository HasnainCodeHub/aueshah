"""Bespoke skill for custom requests."""
from app.config.prompts import SKILL_PROMPTS
from app.skills.base import Skill


def create_bespoke_skill() -> Skill:
    """Create and return the bespoke skill."""
    return Skill(
        name="bespoke",
        prompt_template=SKILL_PROMPTS["bespoke"],
        use_rag=True,
        allow_tool=False,
    )
