# ai_analyzer/code_analyzer.py
from .llm_client import LLMClient
from .prompt_manager import PromptManager
from typing import Dict, List, Any
import asyncio


class CodeAnalyzer:
    def __init__(self):
        self.llm_client = LLMClient()
        self.prompt_manager = PromptManager()

    async def analyze_changes(self, changes: List[Dict]) -> Dict[str, Any]:
        """변경된 파일들에 대한 분석 수행"""
        # 모든 변경사항을 한꺼번에 LLMClient로 전달
        analysis_result = await self.llm_client.analyze_code_changes(changes)
        return analysis_result
