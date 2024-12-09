# ai_analyzer/llm_client.py
from openai import AsyncOpenAI
import os


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = AsyncOpenAI(api_key=self.api_key)

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

    async def parse_json(self, messages, response_format, temperature: float = 0.7):
        """Pydantic 모델을 통해 Structured Outputs를 파싱하는 메서드"""
        completion = await self.client.beta.chat.completions.parse(
            model="gpt-4o-mini", messages=messages, temperature=temperature, response_format=response_format
        )

        message = completion.choices[0].message
        if message.refusal:
            # 모델이 스키마를 만족하는 결과를 낼 수 없어서 거부한 경우
            return None, message.refusal

        if message.parsed is not None:
            # 모델이 스키마에 맞추어 정상 파싱된 결과
            return message.parsed, None

        # parsed가 None이지만 거부도 없으면 content를 반환 (JSON 문자열일 가능성)
        return message.content, None
