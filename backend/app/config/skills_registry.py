"""Skill registry and definitions."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SkillDefinition:
    """Definition of a skill: name, prompt, flags."""
    name: str
    prompt_key: str  # Key in SKILL_PROMPTS dict
    use_rag: bool = False
    allow_tool: bool = False
    output_schema: Optional[str] = None


# Registry of all available skills
SKILLS_REGISTRY = {
    "product": SkillDefinition(
        name="product",
        prompt_key="product",
        use_rag=True,
        allow_tool=False,
    ),
    "compare": SkillDefinition(
        name="compare",
        prompt_key="compare",
        use_rag=True,
        allow_tool=False,
    ),
    "noor": SkillDefinition(
        name="noor",
        prompt_key="noor",
        use_rag=False,
        allow_tool=False,  # No tool execution in Phase 1
    ),
    "bespoke": SkillDefinition(
        name="bespoke",
        prompt_key="bespoke",
        use_rag=True,
        allow_tool=False,
    ),
    "general": SkillDefinition(
        name="general",
        prompt_key="general",
        use_rag=False,
        allow_tool=False,
    ),
}


def get_skill(name: str) -> Optional[SkillDefinition]:
    """Get a skill definition by name."""
    return SKILLS_REGISTRY.get(name.lower())


def get_all_skills() -> list[str]:
    """Get list of all skill names."""
    return list(SKILLS_REGISTRY.keys())
