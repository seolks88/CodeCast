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
                        "content": "당신은 코드 리뷰 전문가입니다. 분석 결과는 간단명료하게 작성하되, 불필요한 줄바꿈을 최소화하여 작성해 주세요. 각 항목 사이에는 한 줄의 공백만 넣어주세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )

            analysis = response.choices[0].message.content
            return {"analysis": analysis, "status": "success"}

        except Exception as e:
            return {"error": str(e), "status": "error"}

    async def analyze_text(self, user_prompt: str, temperature: float = 0.7) -> str:
        """일반 텍스트 분석을 위한 메서드"""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content
