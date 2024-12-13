# report_workflow.py

from langgraph.graph import StateGraph, START, END
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
import asyncio
import random
from datetime import datetime

from model import (
    TopicSelectorInput,
    TopicSelectorOutput,
    AgentInput,
    ReportIntegratorInput,
    ReportIntegratorOutput,
)
from modules.topic_selector import TopicSelector
from modules.bad_agent_node import BadAgentNode
from modules.good_agent_node import GoodAgentNode
from modules.new_agent_node import NewAgentNode
from modules.report_integrator import ReportIntegrator
from modules.habit_manager import HabitManager
from memory.memory_orchestrator import MemoryOrchestrator
from memory.rdb_repository import RDBRepository
from memory.embedding_service import EmbeddingService
from memory.vector_db_client import VectorDBClient
from backup.llm_client import LLMClient
from file_watcher.state_manager import DatabaseManager
from config.settings import Config

from ai_analyzer.llm_manager import LLMManager
from modules.deep_explainer_agent_node import DeepExplainerAgentNode


class HabitsFeedback(TypedDict):
    agent_type: str
    improvement_suggestions: str
    missing_points: List[str]


class MyState(TypedDict):
    changes: List[Dict[str, Any]]
    recent_topics: List[Dict[str, Any]]
    selected_topics: Dict[str, Dict[str, str]]
    user_context: str
    habits_description: str
    agent_reports: List[Dict[str, Any]]
    fallback_mode: bool
    error: bool
    final_report: str
    today: str
    original_habits_content: str
    error_node_name: str
    precheck_result: str
    review_result: str
    feedback: str
    agents_to_improve: List[str]
    retry_count: int
    deep_explain_result: Optional[Dict[str, Any]]
    nodes_to_rerun: List[str]
    agent_feedbacks: List[HabitsFeedback]


db_manager = DatabaseManager(Config.DB_PATH)

rdb_repo = RDBRepository(Config.DB_PATH)
embedding_service = EmbeddingService()
vector_client = VectorDBClient(persist_directory=".chroma_db")

memory = MemoryOrchestrator(
    rdb_repository=rdb_repo, embedding_service=embedding_service, vector_db_client=vector_client
)

llm_client = LLMClient()
llm = LLMManager(model=Config.DEFAULT_LLM_MODEL)

topic_selector = TopicSelector(memory, model=Config.DEFAULT_LLM_MODEL)
bad_agent = BadAgentNode(memory, model=Config.DEFAULT_LLM_MODEL)
good_agent = GoodAgentNode(memory, model=Config.DEFAULT_LLM_MODEL)
new_agent = NewAgentNode(memory, model=Config.DEFAULT_LLM_MODEL)
report_integrator = ReportIntegrator()
habit_manager = HabitManager(model=Config.DEFAULT_LLM_MODEL)
deep_explainer_agent = DeepExplainerAgentNode(model=Config.DEFAULT_LLM_MODEL)


# 추가된 precheck_node
async def precheck_node(state: MyState) -> MyState:
    print("[INFO] precheck_node 시작")
    total_changed_lines = 0
    for ch in state["changes"]:
        diff_content = ch.get("diff", "")
        changed_lines = sum(1 for line in diff_content.split("\n") if line.startswith("+") or line.startswith("-"))
        total_changed_lines += changed_lines

    if total_changed_lines < 5:
        state["precheck_result"] = "minor_change"
    else:
        state["precheck_result"] = "major_change"
    return state


def precheck_decision(state: MyState):
    if state["precheck_result"] == "minor_change":
        return "generate_advice_node"
    else:
        return "select_topics"


# 추가된 generate_advice_node
async def generate_advice_node(state: MyState) -> MyState:
    print("[INFO] generate_advice_node 시작")
    # habits.txt 읽기
    habits_content = habit_manager.read_habits().strip()

    if habits_content:
        # 습관 정보 기반 조언
        advice = (
            f"사소한 변경이 감지되어 전체 분석을 생략합니다.\n\n"
            f"당신의 습관을 기반으로 한 프로그래밍 조언:\n\n{habits_content}\n\n"
            "이 습관을 더 발전시키기 위해, 매일 15분씩 리팩토링이나 코드 리뷰 연습을 시도해보세요!"
        )
    else:
        # 습관 정보 없음 -> 랜덤 주제
        random_topics = [
            "테스트 주도 개발(TDD)의 장점",
            "함수형 프로그래밍 기법",
            "효율적인 로그 관리 전략",
            "코드 리뷰 문화 개선 방법",
            "CI/CD 파이프라인 구축 기초",
        ]
        chosen_topic = random.choice(random_topics)
        advice = (
            f"사소한 변경이 감지되어 전체 분석을 생략합니다.\n\n"
            f"오늘의 랜덤 프로그래밍 주제: {chosen_topic}\n\n"
            "이 주제를 공부해보며 새로운 습관을 만들어보세요!"
        )

    state["final_report"] = advice
    return state


async def select_topics(state: MyState) -> MyState:
    print("[INFO] select_topics 시작")
    try:
        ts_input = TopicSelectorInput(changes=state["changes"], recent_topics=state["recent_topics"])
        output: TopicSelectorOutput = await topic_selector.run(ts_input)
        state["selected_topics"] = output.selected_topics
        if not output.selected_topics:
            state["fallback_mode"] = True
    except Exception as e:
        print(f"Error in select_topics: {e}")
        state["error"] = True
        state["error_node_name"] = "select_topics"
    return state


def check_topics(state: MyState):
    if state["error"]:
        return "error_node"
    elif state["fallback_mode"]:
        return "fallback_node"
    else:
        return "analyze_habits"


async def analyze_habits(state: MyState) -> MyState:
    print("[INFO] analyze_habits 시작")
    try:
        habits_content = habit_manager.read_habits()
        state["user_context"] = f"사용자 습관 정보:\n{habits_content}"
        state["habits_description"] = habits_content
    except Exception as e:
        print(f"Error in analyze_habits: {e}")
        state["error"] = True
        state["error_node_name"] = "analyze_habits"
    return state


async def run_agents_in_parallel(state: MyState) -> MyState:
    print("[INFO] run_agents_in_parallel 시작")
    # print(f"선택된 토픽: {state['selected_topics']}")
    print(f"에이전트 실행 목록: {state.get('agents_to_improve', [])}")

    if state["error"] or state["fallback_mode"]:
        return state

    try:
        # changes를 file_path 키로 하는 딕셔너리로 변환
        changes_dict = {ch["file_path"]: ch for ch in state["changes"]}

        agent_types = ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"]
        tasks = []

        agents_to_run = state.get("agents_to_improve", [])
        if not agents_to_run:
            agents_to_run = agent_types

        for agent_type in agents_to_run:
            agent_feedback = next((f for f in state.get("agent_feedbacks", []) if f["agent_type"] == agent_type), None)
            # 해당 에이전트와 관련된 파일들만 선택
            related_files = state["selected_topics"][agent_type]["related_files"]

            # 관련된 파일들의 코드와 diff만 결합
            agent_related_changes = {path: changes_dict[path] for path in related_files if path in changes_dict}

            combined_full_code = "\n\n".join(
                ch["full_content"] for ch in agent_related_changes.values() if ch["full_content"]
            )
            combined_diff = "\n\n".join(ch["diff"] for ch in agent_related_changes.values() if ch["diff"])

            inp = AgentInput(
                agent_type=agent_type,
                topic_text=state["selected_topics"][agent_type]["topic"],
                context_info=state["selected_topics"][agent_type]["context"],
                user_context=state["user_context"],
                habit_description=state.get("habits_description", ""),
                full_code=combined_full_code,
                diff=combined_diff,
                feedback=agent_feedback["improvement_suggestions"] if agent_feedback else "",
                missing_points=agent_feedback["missing_points"] if agent_feedback else [],
                current_report=state["final_report"],
            )

            if agent_type == "개선 에이전트":
                tasks.append(bad_agent.run(inp))
            elif agent_type == "칭찬 에이전트":
                tasks.append(good_agent.run(inp))
            elif agent_type == "발견 에이전트":
                tasks.append(new_agent.run(inp))

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    print(f"Agent execution error: {str(r)}")
                    continue
                state["agent_reports"].append(r.model_dump())
        except Exception as e:
            print(f"Critical error in run_agents_in_parallel: {e}")
            state["error"] = True
            state["error_node_name"] = "run_agents_in_parallel"
    except Exception as e:
        print(f"Error in run_agents_in_parallel: {e}")
        state["error"] = True
        state["error_node_name"] = "run_agents_in_parallel"
    return state


def check_error_fallback(state: MyState):
    if state["error"]:
        return "error"
    elif state["fallback_mode"]:
        return "fallback"
    else:
        return "normal"  # 정상 경우에 integrate_reports 대신 normal을 반환


def integrate_reports(state: MyState) -> MyState:
    print("[INFO] integrate_reports 시작")
    if state["error"]:
        print("An error occurred during the pipeline. Cannot produce final report.")
        return state

    if state["fallback_mode"]:
        print("Fallback mode: No topics found, no integrated report.")
        return state

    ri_input = ReportIntegratorInput(agent_reports=state["agent_reports"])
    ri_output: ReportIntegratorOutput = report_integrator.run(ri_input)
    state["final_report"] = ri_output.report

    db_manager.save_analysis_results({"status": "success", "analysis": state["final_report"]})
    return state


async def update_habits_post_report(state: MyState) -> MyState:
    print("[INFO] update_habits_post_report 시작")
    if state["error"] or state["fallback_mode"]:
        return state

    try:
        new_content = await habit_manager.update_habits(
            today=state["today"],
            original_habits_content=state["original_habits_content"],
            final_report=state["final_report"],
        )
        habit_manager.write_habits(new_content)
        return state
    except Exception as e:
        print(f"Error updating habits: {e}")
        state["error"] = True
        state["error_node_name"] = "update_habits_post_report"
        return state


def fallback_node(state: MyState) -> MyState:
    print("[INFO] fallback_node 시작")
    print("Fallback mode activated. No meaningful topics to process.")

    if not state["final_report"]:
        state["final_report"] = (
            "사소한 변경이 감지되었거나 적절한 주제를 찾지 못했습니다.\n"
            "오늘은 분석을 생략하고 휴식을 취하거나, habits.txt를 점검해보는 것은 어떨까요?\n"
            "다음 변경 시 더 풍부한 분석을 제공하겠습니다!"
        )
    return state


def error_node(state: MyState) -> MyState:
    print("[INFO] error_node 시작")
    print(f"Error occurred at node: {state.get('error_node_name')}")
    state["fallback_mode"] = True
    if not state["final_report"]:
        state["final_report"] = (
            "분석 도중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.\n"
            "오류가 지속된다면 시스템 관리자에게 문의하세요."
        )
    return state


async def review_report(state: MyState) -> MyState:
    print("[INFO] review_report 시작")

    # 1. habits 반영 여부 검토
    habits_review_schema = {
        "type": "object",
        "properties": {
            "is_reflected": {"type": "boolean"},
            "feedback": {"type": "string"},
            "agent_feedbacks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "agent_type": {"type": "string"},
                        "improvement_suggestions": {"type": "string"},
                        "missing_points": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["agent_type", "improvement_suggestions", "missing_points"],
                },
            },
            "agent_types": {
                "type": "array",
                "items": {"type": "string", "enum": ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"]},
            },
        },
        "required": ["is_reflected", "feedback", "agent_feedbacks", "agent_types"],
    }

    habits_prompt = f"""
    다음 habits.txt 내용과 최종 리포트를 비교 검토해주세요:
    
    [Habits 내용]
    {state['original_habits_content']}
    
    [최종 리포트]
    {state['final_report']}
    
    1. habits.txt의 내용이 리포트에 적절히 반영되었는지 판단해주세요.
    2. 만약 반영이 부족하다면, 어떤 에이전트(개선/칭찬/발견)의 분석이 부족한지 선택해주세요.
    3. 부족한 부분을 해결하려면 어떻게 접근해야하는지 구체적인 피드백을 제공해주세요.
    """

    habits_result, _ = await llm.aparse_json(
        messages=[
            {"role": "system", "content": "habits.txt 내용 반영 여부와 개선이 필요한 에이전트를 판단하세요."},
            {"role": "user", "content": habits_prompt},
        ],
        json_schema=habits_review_schema,
    )

    # 2. 심층 분석 품질 검토
    deep_explain_review = None
    if "심층 분석 에이전트" in [r["agent_type"] for r in state["agent_reports"]]:
        deep_review_schema = {
            "type": "object",
            "properties": {"has_issues": {"type": "boolean"}, "feedback": {"type": "string"}},
            "required": ["has_issues", "feedback"],
        }

        deep_explain_content = next(
            r["report_content"] for r in state["agent_reports"] if r["agent_type"] == "심층 분석 에이전트"
        )

        deep_explain_review, _ = await llm.aparse_json(
            messages=[
                {
                    "role": "system",
                    "content": "심층 분석에 심각한 문제가 있는지만 판단하세요. 일반적인 개선점은 무시하고, 명백한 문제가 있을 때만 지적해주세요.",
                },
                {
                    "role": "user",
                    "content": f"""다음 심층 분석에 심각한 문제가 있는지 확인해주세요:

{deep_explain_content}

- 분석이 완전히 잘못된 방향으로 갔는지
- 핵심을 완전히 놓쳤는지
- 내용이 너무 일반적이거나 의미 없는지

이런 심각한 문제가 있을 때만 피드백을 주세요.""",
                },
            ],
            json_schema=deep_review_schema,
        )

    # 3. 결과 통합 및 재실행 노드 결정
    nodes_to_rerun = []
    feedback_messages = []
    agents_to_improve = []

    if not habits_result["is_reflected"]:
        agents_to_improve.extend(habits_result["agent_types"])
        state["agent_feedbacks"] = [
            {"agent_type": agent_type, "improvement_suggestions": habits_result["feedback"], "missing_points": []}
            for agent_type in habits_result["agent_types"]
        ]
        feedback_messages.append("복습 관련 피드백이 각 에이전트에 전달됩니다.")

    if deep_explain_review and deep_explain_review["has_issues"]:
        nodes_to_rerun.append("deep_explainer_node")
        feedback_messages.append(f"심층 분석 피드백: {deep_explain_review['feedback']}")

    if agents_to_improve:
        nodes_to_rerun.append("run_agents_in_parallel")

    state.update(
        {
            "review_result": "fail" if nodes_to_rerun else "ok",
            "feedback": "\n".join(feedback_messages),
            "nodes_to_rerun": nodes_to_rerun,
            "agents_to_improve": agents_to_improve,
            "retry_count": state.get("retry_count", 0) + 1,
        }
    )

    return state


def review_decision(state: MyState):
    if state["review_result"] == "ok":
        return "update_habits_post_report"

    if state["retry_count"] > 2:
        return "fallback_node"

    nodes_to_rerun = state.get("nodes_to_rerun", [])

    # habits 관련 피드백이 있는 경우 run_agents_in_parallel로
    if "run_agents_in_parallel" in nodes_to_rerun:
        return "run_agents_in_parallel"
    # 심층 분석만 문제가 있는 경우
    elif "deep_explainer_node" in nodes_to_rerun:
        return "deep_explainer_node"

    return "fallback_node"


async def deep_explainer_node(state: MyState) -> MyState:
    print("[INFO] deep_explainer_node 시작")

    # 이미 결과가 있고 재실행이 필요없는 경우 스킵
    if state.get("deep_explain_result") and "deep_explainer_node" not in state.get("nodes_to_rerun", []):
        return state

    if state["error"] or state["fallback_mode"]:
        return state

    original_topic = state["agent_reports"][0]["topic"] if state["agent_reports"] else "주제 분석"
    detailed_explanation = await deep_explainer_agent.run(
        state["agent_reports"][0]["report_content"],
        feedback=state.get("feedback", ""),  # 피드백 전달
    )

    deep_explain_result = {
        "agent_type": "심층 분석 에이전트",
        "topic": f"{original_topic}의 심층 분석",
        "report_content": detailed_explanation,
    }

    state["deep_explain_result"] = deep_explain_result
    state["agent_reports"].append(deep_explain_result)

    return state


graph = StateGraph(MyState)

graph.add_node("precheck_node", precheck_node)
graph.add_node("generate_advice_node", generate_advice_node)
graph.add_node("select_topics", select_topics)
graph.add_node("analyze_habits", analyze_habits)
graph.add_node("run_agents_in_parallel", run_agents_in_parallel)
graph.add_node("deep_explainer_node", deep_explainer_node)
graph.add_node("integrate_reports", integrate_reports)
graph.add_node("update_habits_post_report", update_habits_post_report)
graph.add_node("fallback_node", fallback_node)
graph.add_node("error_node", error_node)
graph.add_node("review_report", review_report)

# 름 변경
graph.add_edge(START, "precheck_node")
graph.add_conditional_edges(
    "precheck_node",
    precheck_decision,
    {"generate_advice_node": "generate_advice_node", "select_topics": "select_topics"},
)
graph.add_edge("generate_advice_node", END)

graph.add_conditional_edges(
    "select_topics",
    check_topics,
    {"error": "error_node", "fallback": "fallback_node", "analyze_habits": "analyze_habits"},
)

graph.add_conditional_edges(
    "analyze_habits",
    check_error_fallback,
    {"normal": "run_agents_in_parallel", "fallback": "fallback_node", "error": "error_node"},
)

graph.add_conditional_edges(
    "run_agents_in_parallel",
    check_error_fallback,
    {"normal": "deep_explainer_node", "fallback": "fallback_node", "error": "error_node"},
)

# deep_explainer_node에서 심층 분석 리포트를 agent_reports에 추가한 드
graph.add_edge("deep_explainer_node", "integrate_reports")

graph.add_edge("integrate_reports", "review_report")

graph.add_conditional_edges(
    "review_report",
    review_decision,
    {
        "update_habits_post_report": "update_habits_post_report",
        "deep_explainer_node": "deep_explainer_node",
        "run_agents_in_parallel": "run_agents_in_parallel",
        "fallback_node": "fallback_node",
    },
)

graph.add_edge("update_habits_post_report", END)
graph.add_edge("fallback_node", END)
graph.add_edge("error_node", END)

app = graph.compile()
# 그래프를 이미지로 저장
graph_png = app.get_graph(xray=True).draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(graph_png)


# 만약 직접 테스트하려면 run_graph 호출
async def run_graph():
    changes = db_manager.get_recent_changes()
    recent_topics = memory.get_recent_topics(days=3)
    today = datetime.now().strftime("%Y-%m-%d")
    original_habits_content = habit_manager.read_habits()

    initial_state: MyState = {
        "changes": changes,
        "recent_topics": recent_topics,
        "selected_topics": {},
        "user_context": "",
        "habits_description": "",
        "agent_reports": [],
        "fallback_mode": False,
        "error": False,
        "final_report": "",
        "today": today,
        "original_habits_content": original_habits_content,
        "error_node_name": "",
        "precheck_result": "",
        "review_result": "",
        "feedback": "",
        "agents_to_improve": [],
        "retry_count": 0,
        "deep_explain_result": None,
        "nodes_to_rerun": [],
        "agent_feedbacks": [],
    }

    result = await app.ainvoke(
        initial_state,
        {"recursion_limit": 25},  # 최대 25번의 노드 실행으로 제한
    )

    with open(f"report_{today}.txt", "w", encoding="utf-8") as f:
        f.write(result["final_report"])


if __name__ == "__main__":
    asyncio.run(run_graph())
