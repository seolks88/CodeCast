# ai_analyzer/prompt_manager.py
from typing import Dict, List


class PromptManager:
    @staticmethod
    def get_code_review_prompt(diff_content: str, file_path: str, context: Dict = None) -> str:
        """코드 리뷰를 위한 프롬프트 생성"""
        base_prompt = f"""다음 코드 변경사항에 대한 상세한 리뷰를 제공해주세요:

파일: {file_path}

변경사항:
{diff_content}

다음 관점에서 분석해주세요:
1. 코드 품질
   - 가독성
   - 유지보수성
   - 코드 스타일
   
2. 성능
   - 시간 복잡도
   - 공간 복잡도
   - 리소스 사용
   
3. 안정성
   - 잠재적 버그
   - 예외 처리
   - 엣지 케이스
   
4. 보안
   - 취약점
   - 안전하지 않은 작업
   
5. 개선 제안
   - 구체적인 코드 개선 방안
   - 대체 구현 방식
   - 모범 사례
"""

        if context:
            # 프로젝트 특정 컨텍스트 추가
            base_prompt += f"\n\n추가 컨텍스트:\n{context}"

        return base_prompt

    @staticmethod
    def get_optimization_prompt(file_content: str, file_path: str) -> str:
        """성능 최적화를 위한 프롬프트 생성"""
        return f"""다음 코드의 성능 최적화 방안을 제시해주세요:

파일: {file_path}

코드:
{file_content}

분석 관점:
1. 알고리즘 최적화
2. 메모리 사용 개선
3. 실행 시간 단축
4. 리소스 사용 효율화"""

    @staticmethod
    def get_multiple_changes_prompt(changes: List[Dict]) -> str:
        """여러 파일의 변경사항에 대한 프롬프트 생성"""
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
        return prompt
