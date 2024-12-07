# models.py
from pydantic import BaseModel


class AgentTopic(BaseModel):
    topic: str
    relevant_code: str
    context: str


class TopicSelection(BaseModel):
    나쁜놈: AgentTopic
    착한놈: AgentTopic
    새로운놈: AgentTopic
