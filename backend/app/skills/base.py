"""Base skill class and interface."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Skill:
    """Base skill class defining interface."""
    name: str
    prompt_template: str
    use_rag: bool = False
    allow_tool: bool = False
    output_schema: Optional[str] = None

    def get_prompt(self) -> str:
        """Return the skill's prompt template."""
        return self.prompt_template

    def should_use_rag(self) -> bool:
        """Check if this skill should use RAG retrieval."""
        return self.use_rag

    def can_use_tools(self) -> bool:
        """Check if this skill can invoke tools."""
        return self.allow_tool
