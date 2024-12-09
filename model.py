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


class ConceptHabitAnalyzerInput(BaseModel):
    changes: List[Dict[str, Any]]


class ConceptHabitAnalyzerOutput(BaseModel):
    concepts: List[str]
    habits: List[str]


class ReportIntegratorInput(BaseModel):
    agent_reports: List[Dict[str, Any]]


class ReportIntegratorOutput(BaseModel):
    report: str


# 에이전트 노드용 모델
class AgentInput(BaseModel):
    agent_type: str  # "개선 에이전트", "칭찬 에이전트", "발견 에이전트"
    topic_text: str
    context_info: str
    user_context: str
    concepts: List[str]
    habits: List[str]
    full_code: str
    diff: str


class AgentOutput(BaseModel):
    agent_type: str
    topic: str
    report_id: int
    report_content: str
