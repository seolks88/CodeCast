from langgraph.graph import StateGraph, START, END
from typing import TypedDict


# 그래프의 상태를 정의하는 클래스
class MyState(TypedDict):
    counter: int


# StateGraph 인스턴스 생성
graph = StateGraph(MyState)


# 카운터를 증가시키는 노드 함수 정의
def increment(state: MyState):
    return {"counter": state["counter"] + 1}


def check_counter(state: MyState):
    if state["counter"] > 10:
        return "종료"
    else:
        return "증가"


# 'increment' 노드 추가
graph.add_node("increment", increment)


graph.add_edge(START, "increment")

# 'increment' 노드에서 END로 엣지 추가
graph.add_conditional_edges("increment", check_counter, {"종료": END, "증가": "increment"})
# graph.add_edge("increment", END)


# 그래프 컴파일
app = graph.compile()

# 그래프 실행
result = app.invoke({"counter": 0})
print(result)


# 그래프를 이미지로 저장
graph_png = app.get_graph(xray=True).draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(graph_png)
