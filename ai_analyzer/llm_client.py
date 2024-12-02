# ai_analyzer/llm_client.py
from openai import AsyncOpenAI
import os
from typing import Dict, Any, List


class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def analyze_code_changes(self, changes: List[Dict]) -> Dict[str, Any]:
        """여러 파일의 코드 변경사항을 분석하여 개선점과 제안사항을 반환"""
        try:
            # 모든 변경사항을 프롬프트에 포함
            change_descriptions = []
            for idx, change in enumerate(changes, start=1):
                file_path = change["file_path"]
                diff_content = change["diff"]
                change_description = f"""
변경사항 {idx}:
파일: {file_path}
변경사항:
{diff_content}
"""
                change_descriptions.append(change_description)

            all_changes_text = "\n".join(change_descriptions)

            prompt = f"""아래 여러 코드 변경사항을 분석하고 각 파일별로 다음 항목들을 평가해주세요:
1. 코드 품질 (가독성, 유지보수성)
2. 성능 영향
3. 잠재적 버그나 오류
4. 개선 제안

각 파일에 대해 별도로 분석해 주세요.

{all_changes_text}
"""

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
