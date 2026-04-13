"""Noor skill - intent-only stub for Phase 1."""
from app.config.prompts import SKILL_PROMPTS
from app.skills.base import Skill


def create_noor_skill() -> Skill:
    """Create and return the noor skill (intent-only stub)."""
    return Skill(
        name="noor",
        prompt_template=SKILL_PROMPTS["noor"],
        use_rag=False,
        allow_tool=False,  # No tool execution in Phase 1
    )
