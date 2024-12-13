# CodeCast
### 코드의 성장을 이끄는 AI 멘토링 시스템

**CodeCast**는 사용자의 코드 변화를 감지하고, 멀티에이전트 시스템을 통해 심층적인 코드 분석을 제공하는 지능형 개발 파트너입니다.  
단순한 코드 리뷰를 넘어, 각기 다른 전문성을 가진 AI 에이전트들이 협업하여 균형 잡힌 피드백을 제공합니다:

여기엔 단순히 코드 스타일만 보는 리뷰어가 아니라, 개성 있는 세 명의 시니어 개발자 에이전트가 대기 중입니다:

1. **개선 에이전트 ('나쁜놈')** 😤:  
   - "이봐, 이건 좀 별로인데?"라고 문제점을 짚으며 실용적인 개선책을 제안합니다.
   - 개발자의 나쁜 코딩 습관을 날카롭게 지적하고 직설적으로 조언합니다.
   - 반복되는 실수나 비효율적인 패턴을 추적하여 뼈아픈 피드백을 제공합니다.
   
2. **칭찬 에이전트 ('좋은놈')** 😊:  
   - "오, 이 부분 정말 좋네요!"라며 코드의 장점을 구체적으로 집어냅니다.
   - 개발자의 좋은 코딩 습관을 발견하고 이를 더욱 강화하도록 격려합니다.
   - 발견된 좋은 패턴을 다른 코드에도 적용할 수 있도록 안내합니다.
   
3. **발견 에이전트 ('새로운놈')** 🤔:  
   - "이렇게 접근해보면 어떨까요?"라며 새로운 기술이나 패턴을 시도하도록 유도합니다.
   - 기존 코드에 적용 가능한 최신 개발 트렌드와 패턴을 제안합니다.
   - 실험적이고 창의적인 접근법으로 코드의 새로운 가능성을 제시합니다.

여기에 심층 분석 에이전트('쪽집게 선생님') 🧐가 합류하여, 앞선 리뷰들을 종합 분석한 후 3줄 요약, 핵심 통찰, 다각도 제안을 통해 더욱 깊이 있는 인사이트를 제공합니다.

## 💫 주요 특징
- **개인화된 코딩 여정:**
  > CodeCast는 단순한 코드 분석을 넘어, 개발자만의 고유한 프로그래밍 스토리를 기록합니다. 개발자의 코딩 습관과 스타일을 지속적으로 학습하고 기억하여, 마치 페어 프로그래밍 파트너처럼 맥락을 이해하는 피드백을 제공합니다. 이는 기존 RAG 시스템들과 차별화되는 CodeCast만의 개인화된 장기 메모리 시스템입니다.

- **실시간 파일 감시:**
  > Git commit이나 수동 저장을 기다리지 않고, 로컬 디렉토리의 모든 코드 변경을 감지합니다. 이는 개발자가 commit하지 않은 작업 중인 코드까지 포함하여 하루 동안의 모든 코딩 여정을 놓치지 않고 기록합니다. 이렇게 수집된 데이터는 다음날 아침의 더 풍부한 코드 리뷰와 인사이트 제공의 기반이 됩니다.

- **주요 토픽 자동 선정**: 
  > 당일 제안할 세 가지 관점의 토픽을 자동으로 선별합니다. 각 에이전트는 서로 다른 관점에서 겹치지 않는 토픽을 다루어 더욱 풍부하고 다각적인 피드백을 제공합니다.
  > 
  > 토픽 중복 검사는 키워드 매칭, 의미적 유사도 검사를 검증을 통해 이루어집니다. 이는 단순한 문자열 비교를 넘어 토픽의 실질적인 의미와 맥락을 고려하여, 반복적인 피드백을 방지하고, 매일 새롭고 유의미한 개선 포인트를 발견할 수 있습니다.

- **멀티 에이전트 협업 시스템**: 
  > LangGraph 기반의 멀티에이전트 시스템이 코드 분석의 모든 단계를 유기적으로 연결합니다. 각 전문 에이전트가 독자적인 관점에서 분석을 수행하고, 검토 에이전트가 생성된 피드백의 품질을 평가하여 기준 미달 시 해당 에이전트에게 구체적인 개선 지침과 함께 재작성을 요청합니다. 이러한 반복적인 품질 관리 과정을 거쳐 심층 분석 에이전트가 최종 인사이트를 도출합니다.
  > 
  > 예기치 못한 상황에서도 폴백 시스템이 안정적인 분석을 보장하고, 리포트 통합기가 각 에이전트의 분석 결과를 하나의 일관된 스토리로 엮어냅니다. 이러한 협업 체계는 단일 에이전트의 한계를 뛰어넘어 더욱 풍부하고 신뢰할 수 있는 코드 분석을 가능하게 합니다.

- **개발 습관 관리 시스템**: 
  > AI가 제안한 모든 리포트는 사용자의 '개발 습관'으로 축적되어 지속적으로 관리됩니다. 특정 패턴이나 개선점이 반복적으로 발견될 때, AI는 과거의 유사한 피드백을 자연스럽게 연결하여 맥락 있는 인사이트를 제공합니다. "지난번에도 비슷한 패턴이 발견되었네요"와 같은 친근한 방식으로 사용자에게 상기시켜, 개발자가 자신의 성장 과정을 되돌아보고 지속적인 개선에 집중할 수 있도록 돕습니다.
  > 
  > 이러한 '기억'을 통한 피드백은 단순한 코드 리뷰를 넘어, 개발자의 장기적인 성장 여정을 함께하는 개인화된 멘토링 경험을 제공합니다.

- **프라이버시 중심 설계**: 
  > 개발자의 코딩 습관과 히스토리는 매우 민감한 개인정보입니다. 이에 CodeCast는 철저한 프라이버시 보호를 위해 완전한 로컬 시스템으로 설계되었습니다. SQLite와 Chroma를 활용한 로컬 데이터베이스는 모든 데이터를 사용자의 컴퓨터에만 안전하게 저장하며, 현재는 LLM 추론을 위한 API 호출만이 유일한 외부 통신입니다.
  > 
  > 시스템의 모든 코드를 GitHub에 투명하게 공개하여 사용자가 데이터 처리 방식을 직접 검증할 수 있습니다. 이러한 투명성과 로컬 중심 설계는 개발자가 안심하고 자신의 코딩 여정을 기록하고 발전시킬 수 있는 환경을 제공합니다.


## 🚀 시작하기

### 설치

1. **저장소 클론 및 의존성 설치**
```bash
git clone https://github.com/yourusername/codecast.git
cd codecast
pip install -r requirements.txt
```

2. **환경 변수 설정**
```bash
cp .env.example .env
```
`.env` 파일에 필요한 API 키와 설정을 입력하세요.

3. **워치 디렉토리 준비**
```bash
mkdir watched_directory
```
분석하고자 하는 소스 파일을 이 디렉토리에 위치시킵니다.

### 실행

**기본 실행**
```bash
python main.py
```
파일 변경을 감지하고 자동으로 분석을 시작합니다.

**리포트 이메일 전송** (선택사항)
```bash
python send_report.py
```
SMTP 설정 후 이메일로 리포트를 받아볼 수 있습니다.

### 추가 기능

**개발 습관 관리**
```bash
touch habits.txt
```
시스템이 자동으로 이 파일을 관리하며 개발 습관을 추적합니다.

**커스터마이징**
- `ai_analyzer/prompt_manager.py`를 수정하여 에이전트의 성격과 분석 방식을 조정할 수 있습니다.

### 테스트
```bash
pytest
```
기본적인 안정성 테스트를 실행합니다.

## 🤝 기여하기
- 버그 리포트와 기능 제안은 GitHub 이슈를 이용해 주세요.
- PR 시 PEP8 스타일 가이드를 준수하고 테스트 코드를 포함해 주세요.

## 📜 라이선스
MIT License로 배포됩니다. 자유롭게 사용하고 수정할 수 있습니다.

---

CodeCast는 단순한 코드 분석 도구를 넘어, AI 기반의 지능형 개발 파트너입니다. 일상적인 코딩 패턴을 성찰하고 더 나은 방향을 제시하여, 함께 성장하는 개발 문화를 만들어갑니다.
