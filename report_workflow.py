from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Any, Dict, List
import asyncio

from model import (
    TopicSelectorInput,
    TopicSelectorOutput,
    ConceptHabitAnalyzerInput,
    ConceptHabitAnalyzerOutput,
    AgentInput,
    AgentOutput,
    ReportIntegratorInput,
    ReportIntegratorOutput,
)
from modules.topic_selector import TopicSelector
from modules.concept_habit_analyzer import ConceptHabitAnalyzer
from modules.bad_agent_node import BadAgentNode
from modules.good_agent_node import GoodAgentNode
from modules.new_agent_node import NewAgentNode
from modules.report_integrator import ReportIntegrator
from memory.memory_system import MemorySystem
from ai_analyzer.llm_client import LLMClient
from file_watcher.state_manager import DatabaseManager
from config.settings import Config


class MyState(TypedDict):
    changes: List[Dict[str, Any]]
    recent_topics: List[Dict[str, Any]]
    concepts: List[str]
    habits: List[str]
    selected_topics: Dict[str, Dict[str, str]]
    user_context: str
    agent_reports: List[Dict[str, Any]]
    fallback_mode: bool
    error: bool


db_manager = DatabaseManager(Config.DB_PATH)
memory = MemorySystem(db_path=Config.DB_PATH)
llm_client = LLMClient()

topic_selector = TopicSelector(llm_client, memory)
concept_analyzer = ConceptHabitAnalyzer(llm_client)
bad_agent = BadAgentNode(llm_client, memory)
good_agent = GoodAgentNode(llm_client, memory)
new_agent = NewAgentNode(llm_client, memory)
report_integrator = ReportIntegrator()


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


async def analyze_concepts_habits(state: MyState) -> MyState:
    try:
        ch_input = ConceptHabitAnalyzerInput(changes=state["changes"])
        ch_output: ConceptHabitAnalyzerOutput = await concept_analyzer.run(ch_input)
        state["concepts"] = ch_output.concepts
        state["habits"] = ch_output.habits
        concept_str = (
            ", ".join([f"'{c}' 개념" for c in ch_output.concepts]) if ch_output.concepts else "특별한 개념 없음"
        )
        habit_str = ", ".join([f"'{h}' 습관" for h in ch_output.habits]) if ch_output.habits else "특별한 습관 없음"
        state["user_context"] = f"사용자 상태: 개념들: {concept_str}, 습관들: {habit_str}."
    except Exception as e:
        print(f"Error in analyze_concepts_habits: {e}")
        state["error"] = True
    return state


async def run_agents_in_parallel(state: MyState) -> MyState:
    if state["error"] or state["fallback_mode"]:
        # 이미 이전 단계에서 fallback이나 error면 그냥 반환
        return state

    try:
        agent_types = ["나쁜놈", "착한놈", "새로운놈"]
        tasks = []
        for agent_type in agent_types:
            inp = AgentInput(
                agent_type=agent_type,
                topic_text=state["selected_topics"][agent_type]["topic"],
                relevant_code=state["selected_topics"][agent_type]["relevant_code"],
                context_info=state["selected_topics"][agent_type]["context"],
                user_context=state["user_context"],
                concepts=state["concepts"],
                habits=state["habits"],
            )
            if agent_type == "나쁜놈":
                tasks.append(bad_agent.run(inp))
            elif agent_type == "착한놈":
                tasks.append(good_agent.run(inp))
            elif agent_type == "새로운놈":
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
    final_report = ri_output.report
    print("Final integrated daily report:")
    print(final_report)
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
graph.add_node("analyze_concepts_habits", analyze_concepts_habits)
graph.add_node("run_agents_in_parallel", run_agents_in_parallel)
graph.add_node("integrate_reports", integrate_reports)
graph.add_node("fallback_node", fallback_node)
graph.add_node("error_node", error_node)

# 첫 번째 분기: select_topics 후 상태에 따라 분기
graph.add_edge(START, "select_topics")
graph.add_conditional_edges(
    "select_topics",
    check_topics,
    {"normal": "analyze_concepts_habits", "fallback": "fallback_node", "error": "error_node"},
)

# 두 번째 분기: analyze_concepts_habits 후 에러/폴백 체크
graph.add_conditional_edges(
    "analyze_concepts_habits",
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
graph.add_edge("integrate_reports", END)

app = graph.compile()

# 그래프를 이미지로 저장
graph_png = app.get_graph(xray=True).draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(graph_png)


async def run_graph():
    changes = db_manager.get_recent_changes()
    recent_topics = memory.get_recent_topics(days=3)

    initial_state: MyState = {
        "changes": changes,
        "recent_topics": recent_topics,
        "concepts": [],
        "habits": [],
        "selected_topics": {},
        "user_context": "",
        "agent_reports": [],
        "fallback_mode": False,
        "error": False,
    }

    result = await app.ainvoke(initial_state)
    print("Graph execution result:", result)


if __name__ == "__main__":
    asyncio.run(run_graph())
