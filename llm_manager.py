# llm_manager.py
import os
import time
import asyncio
from litellm import acompletion, completion
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai
import json

load_dotenv()


class LLMManager:
    MODEL_CONFIGS = {
        "gpt-4o-mini": {"api_key": os.getenv("OPENAI_API_KEY"), "provider": "openai"},
        "gpt-4o-2024-11-20": {"api_key": os.getenv("OPENAI_API_KEY"), "provider": "openai"},
        "gemini/gemini-1.5-flash": {"api_key": os.getenv("GOOGLE_API_KEY"), "provider": "gemini"},
        "gemini/gemini-1.5-pro": {"api_key": os.getenv("GOOGLE_API_KEY"), "provider": "gemini"},
        "gemini/gemini-2.0-flash-exp": {"api_key": os.getenv("GOOGLE_API_KEY"), "provider": "gemini"},  # 추가
    }

    def __init__(self, model: str = "gemini/gemini-1.5-pro"):
        if model not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {model}")
        self.model = model
        self.config = self.MODEL_CONFIGS[model]
        self.is_gemini = self.config["provider"] == "gemini"

        if self.is_gemini:
            genai.configure(api_key=self.config["api_key"])

    async def _gemini_parse_json(
        self,
        messages: list,
        json_schema: dict,
        temperature: float,
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Gemini 전용 JSON 파싱"""
        try:
            schema_desc = json.dumps(json_schema, indent=2)
            prompt = f"""Please respond with a JSON object that follows this schema:

{schema_desc}

Ensure your response is a valid JSON object and nothing else.
Do not include any explanations or markdown formatting.
"""
            input_content = "\n".join([prompt, *[f"{msg['role']}: {msg['content']}" for msg in messages]])

            model = genai.GenerativeModel(
                model_name=self.model.replace("gemini/", ""),
                generation_config={"temperature": temperature, "top_p": 0.95, "top_k": 40},
            )

            response = await model.generate_content_async(input_content)

            try:
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]

                parsed_response = json.loads(text.strip())
                return parsed_response, None

            except json.JSONDecodeError as e:
                return None, f"Invalid JSON response: {text[:200]}..."

        except Exception as e:
            return None, str(e)

    async def aparse_json(
        self,
        messages: list,
        json_schema: dict,
        temperature: float = 0.7,
        max_retries: int = 5,
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """비동기 JSON 파싱"""
        if self.is_gemini:
            return await self._gemini_parse_json(messages, json_schema, temperature)

        # OpenAI 및 기타 모델
        for retry in range(max_retries):
            try:
                response = await acompletion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_schema", "schema": json_schema, "strict": True},
                )

                return response.choices[0].message.content, None

            except Exception as e:
                print(f"Error in attempt {retry + 1}/{max_retries}: {str(e)}")
                if retry == max_retries - 1:
                    return None, str(e)
                await asyncio.sleep(2**retry)

        return None, "Max retries exceeded"

    def parse_json(
        self,
        messages: list,
        json_schema: dict,
        temperature: float = 0.7,
        max_retries: int = 5,
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """동기 JSON 파싱"""
        if self.is_gemini:
            return asyncio.run(self._gemini_parse_json(messages, json_schema, temperature))

        for retry in range(max_retries):
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_schema", "schema": json_schema, "strict": True},
                )

                return response.choices[0].message.content, None

            except Exception as e:
                print(f"Error in attempt {retry + 1}/{max_retries}: {str(e)}")
                if retry == max_retries - 1:
                    return None, str(e)
                time.sleep(2**retry)

        return None, "Max retries exceeded"
