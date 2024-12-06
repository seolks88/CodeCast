# agents_controller.py
import asyncio
from datetime import datetime
from typing import List, Dict
import json

from config.settings import Config
from file_watcher.state_manager import DatabaseManager
from memory.memory_system import MemorySystem
from ai_analyzer.llm_client import LLMClient


class AgentsController:
    def __init__(self, db_path: str):
        self.db_manager = DatabaseManager(db_path)
        self.memory = MemorySystem(db_path=db_path)
        self.llm_client = LLMClient()  # 기존 llm_client 사용
        # 나쁜놈, 착한놈, 새로운놈 각각의 프롬프트 템플릿(앞서 정의한 프롬프트 구조 이용)
        self.prompts = {
            "나쁜놈": self._get_bad_agent_prompt,
            "착한놈": self._get_good_agent_prompt,
            "새로운놈": self._get_new_agent_prompt,
        }

    async def initialize(self):
        await self.db_manager.initialize()

    def _get_bad_agent_prompt(self, topic_text: str, relevant_code: str, context_info: str, user_context: str) -> str:
        # 나쁜놈 에이전트용 프롬프트 (개선점 식별)
        prompt = f"""### Context (맥락)
당신은 주니어 개발자의 성장을 진심으로 돕는 10년차 시니어 개발자입니다.

{user_context}  # 여기서 사용자 난이도/습관 관련 정보 삽입

오늘 다룰 주제: "{topic_text}"

아래는 이 주제와 관련된 코드 스니펫과 맥락입니다:

[관련 코드]
```python
{relevant_code}

[맥락 (context)]
{context_info}

이 에이전트에서는 "{topic_text}"와 관련하여 가장 시급히 개선해야 할 문제점을 선정하세요.
이미 여러 번 지적된 습관이나 개념이라면 좀 더 심층적인 개선안을 제안해주세요.

### Strategy (전략)
- 한 가지 핵심 문제점을 명확히 식별합니다.
- 문제되는 부분의 코드 스니펫을 최소한으로 발췌(``` 코드블록 ``` 사용).
- 구체적이며 실용적인 개선 방향을 제안합니다.
- 친근하고 따뜻하지만, 기술적으로 명료한 톤을 유지합니다.
- 단계별 지시에 따라 명확히 답변을 구성합니다.

### Instructions (지시문)
아래 순서대로 피드백을 작성해주세요:

1. 🤝 문제점 발견  
- 문제의 핵심을 친근한 톤으로 소개  
- 문제가 되는 코드 부분을 ```...```로 짧게 발췌  
- 해당 문제의 기술적 영향과 위험성, 흔히 발생하는 상황 설명

2. ✨ 개선 방안  
- 발췌한 코드를 개선한 예시를 ```...```로 제시  
- 개선점의 기술적 장점과 구현 시 주의사항 설명

3. 💝 실무 꿀팁  
- 실제 현업 상황에서 문제 해결 프로세스를 단계별로 제안  
- 비슷한 오류를 방지할 수 있는 전략, 도구, 테스트 방법 제안  
- 필요하다면 간단한 보조 코드 예시 추가

4. ✍️ 정리  
- 한 줄로 문제와 개선점을 요약  
- 개선으로 인한 구체적인 이점 제시  
- Before/After 핵심 변화 포인트 요약

마지막으로 주니어 개발자가 앞으로 성장할 수 있도록 따뜻하고 구체적인 응원 메시지를 전해주세요.  
"예: '앞으로는 이런 상황에서도 침착하게 개선할 수 있을 거예요! 계속 성장하는 모습을 기대합니다 😊'"
"""

        return prompt

    def _get_good_agent_prompt(self, topic_text: str, relevant_code: str, context_info: str, user_context: str) -> str:
        # 착한놈 에이전트용 프롬프트
        prompt = f"""### Context (맥락)
당신은 주니어 개발자의 성장을 응원하는 10년차 시니어 개발자입니다.

{user_context}

오늘 다룰 주제: "{topic_text}"

[관련 코드]

{relevant_code}

[맥락 (context)]
{context_info}

이 에이전트에서는 "{topic_text}"에 대해 잘한 부분을 강조하고 발전 방향을 제안하세요.

### Strategy (전략)
- 한 가지 훌륭한 패턴이나 접근 방식을 발췌하고, 그 장점을 기술적으로 설명합니다.
- 해당 코드를 발전시킬 수 있는 구체적인 방안을 제안합니다.
- 희망적이고 격려하는 톤을 유지합니다.
- 단계별 지시에 따라 명확히 답변을 구성합니다.

### Instructions (지시문)
아래 순서대로 피드백을 작성해주세요:

1. 🌟 잘한 부분 발견  
   - 긍정적 톤으로 해당 코드의 좋은 점 소개  
   - ```...```로 해당 부분 핵심 코드 라인 발췌  
   - 이 접근이 기술적으로 왜 유용한지, 어떤 상황에서 특히 강점이 있는지 설명

2. 💡 발전 방향 제안  
   - 현재 코드보다 개선된 예시를 ```...```로 제시  
   - 이 개선으로 얻을 수 있는 추가적인 장점(확장성, 유지보수성 등) 강조

3. 🎯 실무 인사이트  
   - 이 패턴이 실제 프로젝트나 다양한 시나리오에서 어떻게 빛을 발하는지 설명  
   - 다른 상황에서 응용할 수 있는 아이디어(코드 예시 포함 가능)  
   - 관련 라이브러리나 도구 소개로 실무 적용성 강화

4. ✍️ 정리  
   - 한 줄로 잘한 점과 발전 방향 요약  
   - 제안 구현 시 추가적으로 얻을 수 있는 이점 명확히 제시  
   - Current/Advanced 상태 비교 간략 정리

마지막으로 주니어 개발자를 응원하는 따뜻한 메시지를 전해주세요.  
"예: '이렇게 조금씩 개선하면서 성장하는 모습이 기대됩니다. 화이팅! 😊'"
"""
        return prompt

    def _get_new_agent_prompt(self, topic_text: str, relevant_code: str, context_info: str, user_context: str) -> str:
        # 새로운놈 에이전트용 프롬프트
        prompt = f"""### Context (맥락)

당신은 최신 트렌드와 실무 경험이 풍부한 10년차 시니어 개발자입니다.

{user_context}

오늘 다룰 주제: "{topic_text}"

[관련 코드]

{relevant_code}

[맥락 (context)]
{context_info}

이 에이전트에서는 "{topic_text}"와 관련된 새로운 기술적 인사이트를 제안하세요.

### Strategy (전략)
- 코드나 프로젝트 맥락에 관련된 유용한 최신 트렌드나 베스트 프랙티스 중 하나를 선정합니다.
- 실제 적용 가능하고 명확한 코드 예시로 제안합니다.
- 실무 노하우와 주의사항을 알기 쉽게 전달합니다.
- 단계별 지시에 따라 명확히 답변을 구성합니다.

### Instructions (지시문)
아래 순서대로 인사이트를 작성해주세요:

1. 💫 오늘의 인사이트 소개  
   - 흥미로운 톤으로 새로운 인사이트 주제 소개  
   - 필요하다면 ```...```로 관련 코드 일부 발췌  
   - 이 인사이트가 왜 중요한지 기술적, 실무적 가치 설명

2. ⚡ 실제 적용 방법  
   - 인사이트 적용 예시 코드 ```...```로 제시  
   - 적용 시 얻는 장점(성능 개선, 유지보수성 증가, 생산성 향상 등) 강조  
   - 적용 시 주의할 점이나 고려사항 안내

3. 🎨 활용 시나리오  
   - "이런 상황에서는 특히 유용하다"는 구체적 사례 제시  
   - 다양한 활용 방법, 추가적인 코드 예시 가능  
   - 함께 사용하면 좋은 도구, 패턴, 라이브러리 소개

4. ✍️ 정리  
   - 한 줄로 오늘의 인사이트 핵심 요약  
   - 이 인사이트를 적용했을 때 얻을 수 있는 구체적 이점 명시  
   - Before/After 스타일로 접근 변화 간략히 정리

마지막으로 이 인사이트를 통해 개발자가 실무 역량을 키워나갈 수 있도록 격려하는 메시지를 전해주세요.  
"예: '이런 접근을 통해 더 효율적이고 스마트한 코드를 작성할 수 있을 거예요! 앞으로도 계속 성장해 나가길 응원합니다 😊'"
"""
        return prompt

    def _format_changes(self, changes: List[Dict]) -> str:
        formatted = []
        for i, ch in enumerate(changes, start=1):
            formatted.append(f"변경사항 {i}:\n파일: {ch['file_path']}\n변경사항:\n{ch['diff']}")
        return "\n".join(formatted)

    async def generate_daily_report(self):
        changes = self.db_manager.get_recent_changes()
        if not changes:
            print("No recent changes to analyze.")
            return None

        recent_topics = self.memory.get_recent_topics(days=3)
        recent_topic_texts = [t["raw_topic_text"] for t in recent_topics]

        new_topics = await self._select_new_topics(changes, recent_topic_texts)

        concepts, habits = await self._extract_concepts_and_habits(changes)
        user_context = self._build_user_context(concepts, habits)

        agent_types = ["나쁜놈", "착한놈", "새로운놈"]
        agent_reports = []

        for agent_type in agent_types:
            topic_text = new_topics[agent_type]["topic"]
            relevant_code = new_topics[agent_type]["relevant_code"]
            context_info = new_topics[agent_type]["context"]

            prompt = self.prompts[agent_type](topic_text, relevant_code, context_info, user_context)

            response = await self.llm_client.analyze_text(prompt)
            topic_id = self.memory.add_topic(datetime.now().isoformat(), topic_text)

            report_id = self.memory.add_agent_report(
                date=datetime.now().isoformat(),
                agent_type=agent_type,
                topic_id=topic_id,
                report_content=response,
                summary=f"{topic_text} 관련 {agent_type} 제안",
                code_refs=[],
                raw_topic_text=topic_text,
            )

            agent_reports.append(
                {"agent_type": agent_type, "topic": topic_text, "report_id": report_id, "report_content": response}
            )

            for c in concepts:
                if c in response:
                    current_diff = self.memory.get_concept_difficulty(c) or "basic"
                    new_diff = "intermediate" if current_diff == "basic" else "advanced"
                    self.memory.update_concept_difficulty(c, new_diff)

            for h in habits:
                if h in response:
                    self.memory.record_habit_occurrence(h)

        final_report = self._integrate_reports(agent_reports)
        return final_report

    def _clean_json_response(self, response: str) -> str:
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return cleaned

    async def _select_new_topics(self, changes, recent_topic_texts, max_retries=3):
        changes_summary = []
        for ch in changes:
            file_path = ch["file_path"]
            diff_excerpt = ch["diff"]
            if len(diff_excerpt) > 150:
                diff_excerpt = diff_excerpt[:150] + "..."
            changes_summary.append(f"파일: {file_path}\n변경사항:\n{diff_excerpt}")
        changes_text = "\n\n".join(changes_summary)

        recent_topics_text = ", ".join(recent_topic_texts) if recent_topic_texts else "없음"

        prompt = f"""
당신은 코드 리뷰 전문가입니다.
아래는 최근 3일간 다룬 주제와 오늘 변경된 코드 내용입니다.

최근 3일 주제: {recent_topics_text}
오늘의 변경사항 요약:
{changes_text}

아래 3명의 에이전트(나쁜놈, 착한놈, 새로운놈)에게 각각 다른 주제를 할당:
- 나쁜놈: 시급히 개선할 문제점(나쁜습관)
- 착한놈: 이미 잘한 부분(좋은습관)
- 새로운놈: 새로운 기능/구조/접근방식(신규 인사이트)

최근에 다룬 주제와 텍스트/의미적으로 유사한 주제도 피해주세요.
새로운 주제를 3개 제안하고, JSON만 반환:
{{
    "나쁜놈": {{
        "topic": "...",
        "relevant_code": "...",
        "context": "..."
    }},
    "착한놈": {{
        "topic": "...",
        "relevant_code": "...",
        "context": "..."
    }},
    "새로운놈": {{
        "topic": "...",
        "relevant_code": "...",
        "context": "..."
    }}
}}
"""

        for attempt in range(max_retries):
            response = await self.llm_client.analyze_text(prompt)
            json_str = self._clean_json_response(response)
            try:
                data = json.loads(json_str)

                if not all(k in data for k in ["나쁜놈", "착한놈", "새로운놈"]):
                    raise ValueError("응답 JSON에 필요한 키가 없습니다.")

                all_topics = [data["나쁜놈"]["topic"], data["착한놈"]["topic"], data["새로운놈"]["topic"]]

                # 텍스트 기반 비교
                if any(t in recent_topic_texts for t in all_topics):
                    raise ValueError("텍스트 기반으로 겹치는 주제 발견")

                # 의미적 유사도 검사
                for t in all_topics:
                    similar = self.memory.find_similar_topics(t, top_k=1)
                    if similar and similar[0]["score"] < 0.8:
                        raise ValueError("의미적으로 유사한 기존 주제와 겹치는 주제 발견")

                # 문제 없이 통과하면 주제 반환
                return data

            except Exception as e:
                print(f"토픽 선정 시도 {attempt+1}/{max_retries} 실패: {str(e)}")
                # 계속 재시도

        # 여기까지 왔다면 max_retries 모두 실패
        print("최대 재시도 횟수 도달. 새로운 주제 선정이 어렵습니다. 복습 모드로 전환합니다.")
        return self._recover_with_review_mode(recent_topic_texts)

    def _recover_with_review_mode(self, recent_topic_texts):
        # 이미 다뤘던 주제 중 하나를 골라 복습/심화 주제로 선정
        # 최근 주제 중 하나를 선택
        fallback_topic = recent_topic_texts[0] if recent_topic_texts else "이전에 다룬 주제"
        dummy_code = "# 기존 코드 일부"
        dummy_context = f"이전에도 '{fallback_topic}'를 다룬 바 있습니다. 이번에는 해당 주제를 복습하면서 더 심화된 관점(테스트 전략, 성능 최적화, 보안 강화 등)에서 제안합니다."

        # 복습 모드에서는 기존 주제를 약간 변형
        return {
            "나쁜놈": {
                "topic": fallback_topic + " 심화 개선점",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
            "착한놈": {
                "topic": fallback_topic + " 접근 강화",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
            "새로운놈": {
                "topic": fallback_topic + " 확장 아이디어",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
        }

    def _build_context_from_similar_reports(self, similar_reports):
        context_summaries = []
        for rep in similar_reports:
            meta = rep["metadata"]
            summary = meta.get("summary", "")
            context_summaries.append(summary)
        return "\n".join(context_summaries)

    def _integrate_reports(self, agent_reports):
        integrated = []
        for rep in agent_reports:
            integrated.append(f"### {rep['agent_type']} - {rep['topic']}\n{rep['report_content']}\n")
        return "\n".join(integrated)

    async def _extract_concepts_and_habits(self, changes: List[Dict]):
        changes_text = self._format_changes(changes)
        prompt = f"""
        다음은 코드 변경사항입니다:

        {changes_text}

        위 코드 변경사항에서 개발자가 고려해야 할 주요 개념(기술, 패턴) 또는 주로 등장하는 습관(좋거나 나쁜 습관) 키워드만 추출해 주세요.
        출력 형식은 JSON으로:
        {{
        "concepts": ["개념1", "개념2", …],
        "habits": ["습관1", "습관2", …]
        }}
        불필요한 설명 없이 JSON만 반환하세요.
        """
        response = await self.llm_client.analyze_text(prompt)
        json_str = self._clean_json_response(response)
        data = json.loads(json_str)

        return data.get("concepts", []), data.get("habits", [])

    def _build_user_context(self, concepts: List[str], habits: List[str]) -> str:
        concept_info = []
        for c in concepts:
            diff = self.memory.get_concept_difficulty(c)
            if not diff:
                self.memory.update_concept_difficulty(c, "basic")
                diff = "basic"
            concept_info.append(f"'{c}' 개념({diff})")

        habit_info = []
        for h in habits:
            occ = self.memory.get_habit_occurrences(h)
            if occ is None:
                occ = 0
            habit_info.append(f"'{h}' 습관({occ}회 지적)")

        concept_str = ", ".join(concept_info) if concept_info else "특별한 개념 없음"
        habit_str = ", ".join(habit_info) if habit_info else "특별한 습관 없음"

        return (
            f"사용자 상태: 개념들: {concept_str}, 습관들: {habit_str}. 이 정보를 참고하여 보고서를 더욱 맞춤화해주세요."
        )
