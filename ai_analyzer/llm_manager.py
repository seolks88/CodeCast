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
        "gemini/gemini-2.0-flash-exp": {"api_key": os.getenv("GOOGLE_API_KEY"), "provider": "gemini"},
        "claude-3-5-sonnet-20241022": {"api_key": os.getenv("ANTHROPIC_API_KEY"), "provider": "anthropic"},
    }

    def __init__(self, model: str = "gemini/gemini-1.5-flash"):
        if model not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {model}")
        self.model = model
        self.config = self.MODEL_CONFIGS[model]
        self.is_gemini = self.config["provider"] == "gemini"

        if self.is_gemini:
            genai.configure(api_key=self.config["api_key"])
            self.generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            self.safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ]

    def _create_messages(self, prompt: str, system_prompt: Optional[str] = None) -> list:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def _gemini_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> Optional[str]:
        try:
            async with asyncio.timeout(30):  # 30초 타임아웃 추가
                model = genai.GenerativeModel(
                    model_name=self.model.replace("gemini/", ""),
                    generation_config={**self.generation_config, "temperature": temperature},
                    system_instruction=system_prompt if system_prompt else None,
                )
                response = await model.generate_content_async(prompt)
                if response and response.text:
                    return response.text.strip()
                return None
        except asyncio.TimeoutError:
            print("[ERROR] Gemini API 호출 시간 초과")
            return None
        except Exception as e:
            print(f"[ERROR] Gemini API 오류: {str(e)}")
            return None

    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        max_retries: int = 5,
        temperature: float = 0.7,
        **kwargs,
    ) -> Optional[str]:
        if self.is_gemini:
            for retry in range(max_retries):
                try:
                    response = await self._gemini_generate(
                        prompt=prompt, system_prompt=system_prompt, temperature=temperature, **kwargs
                    )
                    if response:
                        return response
                except Exception as e:
                    print(f"Error in attempt {retry + 1}/{max_retries}: {str(e)}")
                    if retry == max_retries - 1:
                        print(f"Final error: {str(e)}")
                        return None
                    print(f"Retrying immediately (attempt {retry + 2}/{max_retries})...")
            return None

        messages = self._create_messages(prompt, system_prompt)

        for retry in range(max_retries):
            try:
                response = await acompletion(
                    model=self.model,
                    messages=messages,
                    stream=stream,
                    api_key=self.config["api_key"],
                    temperature=temperature,
                    **kwargs,
                )

                if stream:
                    full_response = ""
                    async for chunk in response:
                        if chunk.choices[0].delta.content:
                            chunk_content = chunk.choices[0].delta.content
                            print(chunk_content, end="", flush=True)
                            full_response += chunk_content
                    print()  # 줄바꿈
                    return full_response
                else:
                    return response.choices[0].message.content

            except Exception as e:
                print(f"Error in attempt {retry + 1}/{max_retries}: {str(e)}")
                if retry == max_retries - 1:
                    print(f"Final error: {str(e)}")
                    return None
                # 재시도 전 지연 시간 제거, 대신 재시도 메시지 출력
                print(f"Retrying immediately (attempt {retry + 2}/{max_retries})...")

        return None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        max_retries: int = 5,
        temperature: float = 0.7,
        **kwargs,
    ) -> Optional[str]:
        messages = self._create_messages(prompt, system_prompt)

        for retry in range(max_retries):
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    stream=stream,
                    api_key=self.config["api_key"],
                    temperature=temperature,
                    **kwargs,
                )

                if stream:
                    full_response = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                    return full_response
                else:
                    return response.choices[0].message.content

            except Exception as e:
                print(f"Error in attempt {retry + 1}/{max_retries}: {str(e)}")
                if retry == max_retries - 1:
                    print(f"Final error: {str(e)}")
                    return None
                # 재시도 전 지연 시간 제거, 대신 재시도 메시지 출력
                print(f"Retrying immediately (attempt {retry + 2}/{max_retries})...")

        return None

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

            response = model.generate_content(input_content)

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
        response_format: Optional[Dict] = None,
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """비동기 JSON 파싱"""
        if self.is_gemini:
            return await self._gemini_parse_json(messages, json_schema, temperature)

        # OpenAI 및 기타 모델
        for retry in range(max_retries):
            try:
                # JSON 스키마를 프롬프트에 포함시키기
                schema_desc = json.dumps(json_schema, indent=2)
                messages = [
                    *messages,
                    {
                        "role": "system",
                        "content": f"""Please respond with a JSON object that follows this schema:
{schema_desc}

Ensure your response is a valid JSON object and nothing else.
Do not include any explanations or markdown formatting.""",
                    },
                ]

                response = await acompletion(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    api_key=self.config["api_key"],
                    response_format={"type": "json_object"},
                )

                try:
                    content = response.choices[0].message.content
                    parsed_content = json.loads(content)
                    return parsed_content, None
                except json.JSONDecodeError as e:
                    return None, f"JSON 파싱 오류: {str(e)}"

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
                # 재시도 전 지연시간 제거
                print(f"Retrying immediately (attempt {retry + 2}/{max_retries})...")

        return None, "Max retries exceeded"
