"""Product skill for describing specific catalog items."""
from app.config.prompts import SKILL_PROMPTS
from app.skills.base import Skill


def create_product_skill() -> Skill:
    """Create and return the product skill."""
    return Skill(
        name="product",
        prompt_template=SKILL_PROMPTS["product"],
        use_rag=True,
        allow_tool=False,
    )
