from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Any, Dict, List
import asyncio
import json

from model import (
    TopicSelectorInput,
    TopicSelectorOutput,
    HabitAnalyzerInput,
    HabitAnalyzerOutput,
    AgentInput,
    AgentOutput,
    ReportIntegratorInput,
    ReportIntegratorOutput,
)
from modules.topic_selector import TopicSelector
from modules.habit_analyzer import HabitAnalyzer
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
from ai_analyzer.prompt_manager import AgentPrompts
from datetime import datetime


class MyState(TypedDict):
    changes: List[Dict[str, Any]]
    recent_topics: List[Dict[str, Any]]
    habits: List[str]
    selected_topics: Dict[str, Dict[str, str]]
    user_context: str
    habits_description: str
    agent_reports: List[Dict[str, Any]]
    fallback_mode: bool
    error: bool
    final_report: str
    today: str
    original_habits_content: str


db_manager = DatabaseManager(Config.DB_PATH)

rdb_repo = RDBRepository(Config.DB_PATH)
embedding_service = EmbeddingService()
vector_client = VectorDBClient(persist_directory=".chroma_db")

memory = MemoryOrchestrator(
    rdb_repository=rdb_repo, embedding_service=embedding_service, vector_db_client=vector_client
)

llm_client = LLMClient()

topic_selector = TopicSelector(llm_client, memory)
habit_analyzer = HabitAnalyzer(llm_client)
bad_agent = BadAgentNode(llm_client, memory)
good_agent = GoodAgentNode(llm_client, memory)
new_agent = NewAgentNode(llm_client, memory)
report_integrator = ReportIntegrator()
habit_manager = HabitManager(llm_client)


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
    return state


def check_topics(state: MyState):
    if state["error"]:
        return "error"
    elif state["fallback_mode"]:
        return "fallback"
    else:
        return "normal"


async def analyze_habits(state: MyState) -> MyState:
    try:
        # habits.txt 파일에서 직접 읽기
        habits_content = habit_manager.read_habits()
        state["user_context"] = f"사용자 습관 정보:\n{habits_content}"
        state["habit_description"] = habits_content
    except Exception as e:
        print(f"Error in analyze_habits: {e}")
        state["error"] = True
    return state


async def run_agents_in_parallel(state: MyState) -> MyState:
    if state["error"] or state["fallback_mode"]:
        return state

    try:
        combined_full_code = "\n\n".join(ch["full_content"] for ch in state["changes"])
        combined_diff = "\n\n".join(ch["diff"] for ch in state["changes"])

        agent_types = ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"]
        tasks = []
        for agent_type in agent_types:
            inp = AgentInput(
                agent_type=agent_type,
                topic_text=state["selected_topics"][agent_type]["topic"],
                context_info=state["selected_topics"][agent_type]["context"],
                user_context=state["user_context"],
                habit_description=state.get("habit_description", ""),
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
    return state


def check_error_fallback(state: MyState):
    if state["error"]:
        return "error"
    elif state["fallback_mode"]:
        return "fallback"
    else:
        return "normal"


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
    messages, response_format = AgentPrompts.get_habit_update_prompt(
        today=state["today"],
        original_habits_content=state["original_habits_content"],
        final_report=state["final_report"],
    )

    parsed_data, refusal = await llm_client.parse_json(messages, response_format=response_format)

    if refusal:
        print(f"Habit update refused: {refusal}")
        state["error"] = True
        return state

    if isinstance(parsed_data, str):
        try:
            parsed_data = json.loads(parsed_data)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            state["error"] = True
            return state

    new_content = await habit_manager.update_habits(
        today=state["today"],
        original_habits_content=state["original_habits_content"],
        final_report=state["final_report"],
    )
    habit_manager.write_habits(new_content)
    return state


def fallback_node(state: MyState) -> MyState:
    # fallback 모드일 때 처리할 노드
    print("Fallback mode activated. No meaningful topics to process.")
    return state


def error_node(state: MyState) -> MyState:
    # 에러 발생 시 처리할 노드
    print("An error occurred. Please check logs.")
    return state


graph = StateGraph(MyState)

graph.add_node("select_topics", select_topics)
graph.add_node("analyze_habits", analyze_habits)
graph.add_node("run_agents_in_parallel", run_agents_in_parallel)
graph.add_node("integrate_reports", integrate_reports)
graph.add_node("update_habits_post_report", update_habits_post_report)
graph.add_node("fallback_node", fallback_node)
graph.add_node("error_node", error_node)

# 첫 번째 분기: select_topics 후 상태에 따라 분기
graph.add_edge(START, "select_topics")
graph.add_conditional_edges(
    "select_topics",
    check_topics,
    {"normal": "analyze_habits", "fallback": "fallback_node", "error": "error_node"},
)

# 두 번째 분기: analyze_habits 후 에러/폴백 체크
graph.add_conditional_edges(
    "analyze_habits",
    check_error_fallback,
    {"normal": "run_agents_in_parallel", "fallback": "fallback_node", "error": "error_node"},
)

# 세 번째 분기: run_agents_in_parallel 후 에러/폴백 체크
graph.add_conditional_edges(
    "run_agents_in_parallel",
    check_error_fallback,
    {"normal": "integrate_reports", "fallback": "fallback_node", "error": "error_node"},
)


# 마지막: integrate_reports 이후 특별한 조건 없이 END
graph.add_edge("integrate_reports", "update_habits_post_report")
graph.add_edge("update_habits_post_report", END)

app = graph.compile()

# 그래프 이미지로 저장
graph_png = app.get_graph(xray=True).draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(graph_png)


async def run_graph():
    changes = db_manager.get_recent_changes()
    recent_topics = memory.get_recent_topics(days=3)
    today = datetime.now().strftime("%Y-%m-%d")
    original_habits_content = habit_manager.read_habits()

    initial_state: MyState = {
        "changes": changes,
        "recent_topics": recent_topics,
        "habits": [],
        "selected_topics": {},
        "user_context": "",
        "habits_description": "",
        "agent_reports": [],
        "fallback_mode": False,
        "error": False,
        "final_report": "",
        "today": today,
        "original_habits_content": original_habits_content,
    }

    result = await app.ainvoke(initial_state)
    # print("Graph execution result:", result)


if __name__ == "__main__":
    asyncio.run(run_graph())
