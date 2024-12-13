# modules/habit_manager.py
import os
from pathlib import Path
from ai_analyzer.llm_manager import LLMManager


class HabitManager:
    def __init__(self, model) -> None:
        # 프로젝트 루트 디렉토리 기준으로 habits.txt 경로 설정
        project_root = Path(__file__).parent.parent
        self.habit_file_path = str(project_root / "habits.txt")
        self.llm = LLMManager(model=model)

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
현재의 habits.txt 내용입니다:
{original_habits_content}

오늘의 분석 보고서 내용입니다:
{final_report}

오늘 날짜: {today}

프로그래밍 습관 판단 기준:

1. 습관으로 볼 수 있는 경우:
   - 코드에서 일관된 패턴이나 접근 방식이 보이는 경우
   - 특정 문제 해결 방식이 여러 파일/위치에서 반복되는 경우
   - 이전 습관과 연관성이 있어 지속적으로 사용될 것이 명확한 경우

2. 습관이 아닌 경우:
   - 단순한 기능 구현이나 버그 수정
   - 프로젝트 특정 요구사항에 따른 일회성 변경
   - 아직 적용되지 않은 제안사항
   - 보고서 내용 중 발견 에이전트의 내용

3. last_updated 날짜 관리:
   - 오늘 보고서에서 해당 습관이 새롭게 언급된 경우 → {today}로 업데이트
   - 비슷한 습관을 통합하는 경우:
     * 오늘 보고서에서 관련 내용 언급 → {today}로 업데이트
     * 오늘 보고서에서 언급 없음 → 원래 날짜 유지
   - 기존 습관이 오늘 보고서에서 전혀 언급되지 않은 경우 → 원래 날짜 유지

4. 습관 통합 규칙:
   동일하거나 매우 유사한 습관 발견 시:
   - 오늘 보고서에서 언급된 경우:
     * 최신 컨텍스트로 내용 업데이트
     * last_updated를 {today}로 변경
   - 오늘 보고서에서 언급되지 않은 경우:
     * 기존 컨텍스트 유지
     * 기존 last_updated 유지

5. 작성 형식:
"사용자는 [구체적인 습관] 하는 습관이 있습니다. [보고서에서 언급된 최신 예시나 컨텍스트]. 주 사용 언어: [언어], 관련 도구: [도구들], 이 습관은 [보고서에서 언급된 긍정적 효과]에 기여합니다. last_updated: YYYY-MM-DD"

habits.txt 형식으로 결과만 반환해주세요.
"""

        response = await self.llm.agenerate(prompt, temperature=0)
        return response.strip()
