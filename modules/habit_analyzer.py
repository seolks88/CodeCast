# habit_analyzer.py
from typing import Dict, Any, Tuple, List, Optional
import json
from ai_analyzer.llm_client import LLMClient
from model import HabitAnalyzerInput, HabitAnalyzerOutput


class HabitAnalyzer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def run(self, input: HabitAnalyzerInput) -> HabitAnalyzerOutput:
        changes_text = self._format_changes_for_habit_extraction(input.changes)
        prompt = self._get_habits_prompt(changes_text)
        # JSON 파싱 없이 바로 분석
        response = await self.llm_client.analyze_text(prompt)
        return HabitAnalyzerOutput(habits_description=response)

    def _get_habits_prompt(self, changes_text: str) -> str:
        return f"""
            다음은 코드 변경사항입니다:

            {changes_text}

            위 코드 변경사항을 통해 추정할 수 있는 개발자의 습관에 대해 자연스럽고 구체적인 문장으로 설명해 주세요.
            사용자가 어떤 습관을 가지고 있으며, 그 습관이 어떤 특징을 갖고 있고 왜 문제인지, 
            그리고 이를 어떻게 개선할 수 있는지에 대해 단락 형태로 서술하세요.
            
            JSON 형식이나 추가적인 설명 없이, 오직 서술형 문장으로만 답변해주세요.
        """.strip()

    def _format_changes_for_habit_extraction(self, changes: List[Dict[str, Any]]) -> str:
        return "\n".join(
            f"변경사항 {i}:\n파일: {ch['file_path']}\n변경사항:\n{ch['diff']}" for i, ch in enumerate(changes, start=1)
        )
