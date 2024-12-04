# ai_analyzer/prompt_manager.py
from typing import Dict, List


class PromptManager:
    @staticmethod
    def get_multiple_changes_prompt(changes: List[Dict]) -> str:
        change_descriptions = []
        for idx, change in enumerate(changes, start=1):
            file_path = change["file_path"]
            diff_content = change["diff"]
            change_description = f"""변경사항 {idx}:
파일: {file_path}
변경사항:
{diff_content}"""
            change_descriptions.append(change_description)

        all_changes_text = "\n".join(change_descriptions)

        prompt = f"""오늘의 코드 개선 리포트입니다. 다음 코드 변경사항들을 분석하여 가장 중요한 3가지 개선점을 제시해주세요.

{all_changes_text}

각 개선점에 대해 다음 형식으로 상세히 설명해주세요:

1. 개선점 제목
현재 코드:
```python
# 현재 문제가 있는 코드 부분을 여기에 그대로 복사
async def get_file_info(self, file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None
    # ... 문제가 있는 코드 부분 ...
```

개선된 코드:
```python
# 개선된 코드를 여기에 작성
async def get_file_info(self, file_path):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
    # ... 개선된 코드 ...
```

개선 이유:
- 현재 코드의 문제점
- 개선 시 얻을 수 있는 이점
- 적용 시 주의사항

[이하 동일한 형식으로 2, 3번 개선점 설명]
"""

        return prompt
