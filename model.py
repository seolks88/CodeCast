# model.py
from pydantic import BaseModel
from typing import List, Dict, Any


class TopicSelectorInput(BaseModel):
    changes: List[Dict[str, Any]]
    recent_topics: List[Dict[str, Any]]


class TopicSelectorOutput(BaseModel):
    selected_topics: Dict[str, Dict[str, Any]]


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
    feedback: str = ""
    missing_points: List[str] = []
    current_report: str = ""


class AgentOutput(BaseModel):
    agent_type: str
    topic: str
    report_id: int
    report_content: str
