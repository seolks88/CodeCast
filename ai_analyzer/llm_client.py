# ai_analyzer/llm_client.py
from openai import AsyncOpenAI
import os
from typing import Dict, Any, List
from .prompt_manager import PromptManager


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.prompt_manager = PromptManager()

    async def analyze_code_changes(self, changes: List[Dict]) -> Dict[str, Any]:
        """여러 파일의 코드 변경사항을 분석하여 개선점과 제안사항을 반환"""
        try:
            # 프롬프트 매니저를 사용하여 프롬프트 생성
            prompt = self.prompt_manager.get_multiple_changes_prompt(changes)

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 코드 리뷰 전문가입니다. Python, JavaScript 등 다양한 프로그래밍 언어에 대한 깊은 이해를 가지고 있으며, 코드 품질 향상을 위한 실용적인 제안을 제공합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            analysis = response.choices[0].message.content
            return {"analysis": analysis, "status": "success"}

        except Exception as e:
            return {"error": str(e), "status": "error"}
