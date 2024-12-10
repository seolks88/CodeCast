# report_workflow.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Any, Dict, List
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
from ai_analyzer.llm_client import LLMClient
from file_watcher.state_manager import DatabaseManager
from config.settings import Config


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
    precheck_result: str  # 추가: precheck 결과 저장


db_manager = DatabaseManager(Config.DB_PATH)

rdb_repo = RDBRepository(Config.DB_PATH)
embedding_service = EmbeddingService()
vector_client = VectorDBClient(persist_directory=".chroma_db")

memory = MemoryOrchestrator(
    rdb_repository=rdb_repo, embedding_service=embedding_service, vector_db_client=vector_client
)

llm_client = LLMClient()

topic_selector = TopicSelector(llm_client, memory)
bad_agent = BadAgentNode(llm_client, memory)
good_agent = GoodAgentNode(llm_client, memory)
new_agent = NewAgentNode(llm_client, memory)
report_integrator = ReportIntegrator()
habit_manager = HabitManager(llm_client)


# 추가된 precheck_node
async def precheck_node(state: MyState) -> MyState:
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
    # 기존 로직 그대로
    if state["error"] or state["fallback_mode"]:
        return state

    try:
        combined_full_code = "\n\n".join(ch["full_content"] for ch in state["changes"] if ch["full_content"])
        combined_diff = "\n\n".join(ch["diff"] for ch in state["changes"] if ch["diff"])

        agent_types = ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"]
        tasks = []
        for agent_type in agent_types:
            inp = AgentInput(
                agent_type=agent_type,
                topic_text=state["selected_topics"][agent_type]["topic"],
                context_info=state["selected_topics"][agent_type]["context"],
                user_context=state["user_context"],
                habit_description=state.get("habits_description", ""),
                full_code=combined_full_code,
                diff=combined_diff,
            )
            if agent_type == "개선 에이전트":
                tasks.append(bad_agent.run(inp))
            elif agent_type == "칭찬 에이전트":
                tasks.append(good_agent.run(inp))
            elif agent_type == "발견 에이전트":
                tasks.append(new_agent.run(inp))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                raise r
            else:
                state["agent_reports"].append(r.model_dump())
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
    print("Fallback mode activated. No meaningful topics to process.")

    if not state["final_report"]:
        state["final_report"] = (
            "사소한 변경이 감지되었거나 적절한 주제를 찾지 못했습니다.\n"
            "오늘은 분석을 생략하고 휴식을 취하거나, habits.txt를 점검해보는 것은 어떨까요?\n"
            "다음 변경 시 더 풍부한 분석을 제공하도록 하겠습니다!"
        )
    return state


def error_node(state: MyState) -> MyState:
    print(f"Error occurred at node: {state.get('error_node_name')}")
    state["fallback_mode"] = True
    if not state["final_report"]:
        state["final_report"] = (
            "분석 도중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.\n"
            "오류가 지속된다면 시스템 관리자에게 문의하세요."
        )
    return state


graph = StateGraph(MyState)

# 그래프 구성 변경점: START -> precheck_node -> generate_advice_node or select_topics
graph.add_node("precheck_node", precheck_node)
graph.add_node("generate_advice_node", generate_advice_node)
graph.add_node("select_topics", select_topics)
graph.add_node("analyze_habits", analyze_habits)
graph.add_node("run_agents_in_parallel", run_agents_in_parallel)
graph.add_node("integrate_reports", integrate_reports)
graph.add_node("update_habits_post_report", update_habits_post_report)
graph.add_node("fallback_node", fallback_node)
graph.add_node("error_node", error_node)

graph.add_edge(START, "precheck_node")
graph.add_conditional_edges(
    "precheck_node",
    precheck_decision,
    {"generate_advice_node": "generate_advice_node", "select_topics": "select_topics"},
)

# 사소한 변경이면 generate_advice_node 후 바로 끝
graph.add_edge("generate_advice_node", END)

# 의미 있는 변경이면 원래 흐름 진행
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
    {"normal": "integrate_reports", "fallback": "fallback_node", "error": "error_node"},
)

graph.add_edge("integrate_reports", "update_habits_post_report")
graph.add_edge("update_habits_post_report", END)

app = graph.compile()


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
    }

    result = await app.ainvoke(initial_state)
    print("Final Report:", result["final_report"])


if __name__ == "__main__":
    asyncio.run(run_graph())
