"""agents 包 - Agent 角色实现"""

from agents.assembler import ChapterAssemblerAgent
from agents.chapter_architect import ChapterArchitectAgent
from agents.citation_guard import CitationGuardAgent
from agents.director import DirectorAgent
from agents.editor import EditorAgent
from agents.expander import ExpanderAgent
from agents.fact_checker import FactCheckerAgent
from agents.planner import PlannerAgent
from agents.research import ResearchAgent
from agents.style_guard import StyleGuardAgent
from agents.writer import WriterAgent

__all__ = [
    "ChapterArchitectAgent",
    "ChapterAssemblerAgent",
    "CitationGuardAgent",
    "DirectorAgent",
    "EditorAgent",
    "ExpanderAgent",
    "FactCheckerAgent",
    "PlannerAgent",
    "ResearchAgent",
    "StyleGuardAgent",
    "WriterAgent",
]
