"""General/fallback skill for unclassified intents."""
from app.config.prompts import SKILL_PROMPTS
from app.skills.base import Skill


def create_general_skill() -> Skill:
    """Create and return the general (fallback) skill."""
    return Skill(
        name="general",
        prompt_template=SKILL_PROMPTS["general"],
        use_rag=False,
        allow_tool=False,
    )
