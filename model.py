# model.py
from pydantic import BaseModel
from typing import List, Dict, Any


class AgentTopic(BaseModel):
    topic: str
    relevant_code: str
    context: str


class TopicSelectorInput(BaseModel):
    changes: List[Dict[str, Any]]
    recent_topics: List[Dict[str, Any]]


class TopicSelectorOutput(BaseModel):
    selected_topics: Dict[str, Dict[str, str]]


class HabitAnalyzerInput(BaseModel):
    changes: List[Dict[str, Any]]


class HabitAnalyzerOutput(BaseModel):
    habits_description: str


class ReportIntegratorInput(BaseModel):
    agent_reports: List[Dict[str, Any]]


class ReportIntegratorOutput(BaseModel):
    report: str


class AgentInput(BaseModel):
    agent_type: str
    topic_text: str
    context_info: str
    user_context: str
    habit_description: str
    full_code: str
    diff: str


class AgentOutput(BaseModel):
    agent_type: str
    topic: str
    report_id: int
    report_content: str
