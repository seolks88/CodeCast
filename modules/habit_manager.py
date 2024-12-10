# modules/habit_manager.py
import os
from pathlib import Path
from typing import Any


class HabitManager:
    def __init__(self, llm_client: Any) -> None:
        # 프로젝트 루트 디렉토리 기준으로 habits.txt 경로 설정
        project_root = Path(__file__).parent.parent
        self.habit_file_path = str(project_root / "habits.txt")

        if llm_client is None:
            raise ValueError("llm_client는 습관 업데이트에 필수적입니다.")
        self.llm_client = llm_client

    def read_habits(self) -> str:
        """habits.txt 파일 내용을 반환. 파일 없으면 빈 문자열."""
        if not os.path.exists(self.habit_file_path):
            return ""
        with open(self.habit_file_path, "r", encoding="utf-8") as f:
            return f.read()

    def write_habits(self, content: str):
        """habits.txt 파일 내용을 content로 덮어쓰기."""
        with open(self.habit_file_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def update_habits(self, today: str, original_habits_content: str, final_report: str) -> str:
        prompt = f"""
아래는 현재 관리중인 습관 목록(habits.txt) 내용입니다:

---습관 목록 시작---
{original_habits_content}
---습관 목록 끝---

아래는 오늘의 종합 보고서(final_report)입니다:
---보고서 시작---
{final_report}
---보고서 끝---

[지시사항]

- 오늘 날짜: {today}

1. 습관(habit)의 정의:
   - 사용자가 앞으로도 지속적으로 유지하거나 반복할 가능성이 높은 개발 행동 패턴을 의미합니다.
   - 단발적 기능 구현이 아닌, 코드 작성/리뷰/테스트/배포 등 과정에서 반복적으로 나타나는 행동 경향을 습관으로 간주합니다.
   - 반복성을 명확히 알 수 없더라도, final_report에서 미래에도 지속될 것으로 추정할 수 있다면 습관으로 판단할 수 있습니다.

2. 기존 습관 처리:
   - 현재 habits.txt에 존재하는 습관을 모두 유지하세요.
   - final_report에서 해당 습관이 언급되거나 강화되었음을 추론할 수 있다면 last_updated를 {today}로 갱신하세요.
   - final_report에서 해당 습관과 관련된 프로그래밍 언어, 도구, 프레임워크, 라이브러리 등 추가 정보를 얻을 수 있다면 습관 문장에 반영하세요.
   - final_report에서 개선 또는 관련 정보가 전혀 언급되지 않으면 기존 내용 그대로 둡니다.

3. 새로운 습관 발굴:
   - final_report를 분석하여, 기존에 없던 새로운 지속적 행동 패턴을 발견하면 새로운 습관을 한 줄 추가하고 last_updated={today}로 설정하세요.
   - 새로운 습관 추가 시, 가능하다면 다음 정보를 문장에 반영하세요:
     - 습관과 가장 밀접한 프로그래밍 언어나 기술 스택  
     - 관련 도구나 라이브러리(예: 특정 린트 툴, 테스트 프레임워크, CI/CD 파이프라인 등)  
     - 이 습관이 야기할 수 있는 문제점(또는 장점)  
     - 이를 개선하거나 더욱 강화하기 위한 구체적인 프로세스나 아이디어
   - 무리하게 정보 추가하지 말고, final_report에 나타난 정보만 활용하세요.
   - final_report에서 발견 에이전트가 제안한 내용은 추가하지 않습니다.
   - "가짜" 습관은 만들지 마세요. final_report로부터 합리적으로 유추 가능한 행동 패턴만 추가하세요.

4. 최종 출력 형식:
   - 최종 habits.txt는 각 습관을 한 줄에 하나의 문장으로 표현합니다.
   - 문장 형식(예시):
     "사용자는 {{habit_detail}} 하는 습관이 있습니다. 주 사용 언어: {{language}}, 관련 도구/환경: {{tools}}, 이 습관은 {{문제점 또는 장점}}를 야기하거나, 개선을 통해 {{개선방향}}하는 데 기여합니다. last_updated: YYYY-MM-DD"
   
   - 필수 필드는 아니지만, 가능하다면 language나 tools와 같은 추가 정보도 포함하세요.
     예: "주 사용 언어: Python, 관련 도구: ESLint, Jest"
   - 문제점, 장점, 개선방향은 final_report에서 힌트를 얻어 자연스럽게 서술하세요.
   - 기존 습관이 language, tools 정보를 가지고 있지 않았다면 final_report를 통해 추론 가능한 경우에만 추가하세요.  
   - 완성된 habits.txt 형태의 문장들만 출력하고, 여는 문구나 추가 설명은 하지 마세요.
   - 습관이 전혀 없다면 빈 줄만 반환하세요.

위 지시사항에 따라 최종 habits.txt를 구성해 주세요.
"""

        response = await self.llm_client.analyze_text(prompt, temperature=0)
        return response.strip()
