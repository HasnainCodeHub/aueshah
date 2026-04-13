"""Compare skill for comparing two catalog items."""
from app.config.prompts import SKILL_PROMPTS
from app.skills.base import Skill


def create_compare_skill() -> Skill:
    """Create and return the compare skill."""
    return Skill(
        name="compare",
        prompt_template=SKILL_PROMPTS["compare"],
        use_rag=True,
        allow_tool=False,
    )
