"""
SLA Strategy Recommendation Agent (Spike)
LangGraph를 사용한 간단한 전략 추천 시스템
"""

import json
from typing import Annotated, TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# State 정의
class AgentState(TypedDict):
    """Agent의 상태를 저장하는 클래스"""

    # 입력
    user_input: str
    weather: str
    budget: int

    # 중간 결과
    all_data: str  # CSV 데이터 (문자열로 변환)
    filtered_strategies: str  # 필터링된 전략들

    # 출력
    recommendation: str
    messages: Annotated[list, add_messages]


# Node 1: 사용자 입력 파싱
def parse_input(state: AgentState) -> AgentState:
    """
    사용자 입력을 파싱하여 날씨와 예산 추출
    예: "폭설 예보, 예산 50만원" → weather="Snow", budget=500000
    """
    user_input = state["user_input"]

    # 간단한 파싱 (실제로는 LLM 사용 가능)
    weather_map = {"맑": "Sunny", "비": "Rain", "눈": "Snow", "폭설": "Snow"}

    weather = "Sunny"  # 기본값
    for key, value in weather_map.items():
        if key in user_input:
            weather = value
            break

    # 예산 추출 (숫자 찾기)
    budget = None
    if "만원" in user_input:
        # "50만원" → 500000
        import re

        numbers = re.findall(r"(\d+)만원", user_input)
        if numbers:
            budget = int(numbers[0]) * 10000

    state["weather"] = weather
    state["budget"] = budget if budget else 999999999  # 제한 없으면 무한대

    return state


# Node 2: 데이터 로드 및 필터링
def load_and_filter_data(state: AgentState) -> AgentState:
    """
    CSV 데이터를 로드하고 날씨와 예산에 맞게 필터링
    """
    # CSV 로드
    df = pd.read_csv("data/level1_clean.csv")

    # 전체 데이터 저장 (컨텍스트용)
    state["all_data"] = df.to_string(index=False)

    # 필터링
    weather = state["weather"]
    budget = state["budget"]

    filtered = df[(df["weather"] == weather) & (df["cost"] <= budget)].copy()

    # 순이익 기준 정렬
    filtered = filtered.sort_values("profit", ascending=False)

    # 상위 5개만 (너무 많으면 LLM 부담)
    filtered = filtered.head(5)

    state["filtered_strategies"] = filtered.to_string(index=False)

    return state


# Node 3: LLM 분석 및 추천
def llm_recommend(state: AgentState) -> AgentState:
    """
    LLM을 사용하여 최적 전략 추천 및 설명
    """
    # 프롬프트 구성
    prompt = f"""
당신은 CS센터 SLA 최적화 전문가입니다.

## 상황
- 날씨: {state["weather"]}
- 가용 예산: {state["budget"]:,}원

## 컬럼 설명
- weather: 날씨 (Sunny/Rain/Snow)
- staff_emergency: 휴무자 긴급 투입 인원 (1명당 4만원)
- staff_overtime: 초과근무/조기출근 인원 (1명당 5만원)
- staff_fasttrack: 간단한 콜만 처리하는 전담팀 (비용 0원, 품질 약간 하락)
- calls_inbound: 예상 인입 콜 수
- calls_answered: 예상 응답 콜 수
- response_rate: 응답률 (%)
- grade: SLA 등급 (S/A/B/C/D)
- cost: 전략 비용
- profit: 순이익 (최종 목표!)
- roi: 투자 수익률

## 가능한 전략들 (순이익 순)
{state["filtered_strategies"]}

## 질문
위 전략 중 어떤 것을 추천하시나요?

**추천 형식:**
1. 추천 전략: [구체적 인원 명시]
2. 예상 결과: [응답률, 등급, 순이익]
3. 선택 이유: [왜 이 전략이 최적인지 2-3문장]

간단명료하게 답변해주세요.
"""

    # 실제로는 여기서 Anthropic API 호출
    # 지금은 Spike라 간단하게 규칙 기반으로
    filtered_df = pd.read_csv("data/level1_clean.csv")
    filtered_df = filtered_df[
        (filtered_df["weather"] == state["weather"])
        & (filtered_df["cost"] <= state["budget"])
    ].sort_values("profit", ascending=False)

    if len(filtered_df) == 0:
        state["recommendation"] = "예산 내 가능한 전략이 없습니다."
        return state

    best = filtered_df.iloc[0]

    recommendation = f"""
## 추천 전략

**투입 인원:**
- 긴급 투입: {int(best["staff_emergency"])}명
- 초과 근무: {int(best["staff_overtime"])}명
- FastTrack: {int(best["staff_fasttrack"])}명

**예상 결과:**
- 응답률: {best["response_rate"]:.1f}%
- SLA 등급: {best["grade"]}등급
- 비용: {int(best["cost"]):,}원
- 순이익: {int(best["profit"]):,}원
- ROI: {best["roi"]:.1f}%

**선택 이유:**
이 전략은 예산 {state["budget"]:,}원 내에서 순이익을 최대화합니다.
{state["weather"]} 날씨에서 응답률 {best["response_rate"]:.0f}%를 달성하여
{best["grade"]}등급을 받을 수 있으며, 최종적으로 {int(best["profit"]):,}원의
순이익이 예상됩니다.
"""

    state["recommendation"] = recommendation

    return state


# Graph 구성
def create_graph():
    """LangGraph 생성"""
    workflow = StateGraph(AgentState)

    # Node 추가
    workflow.add_node("parse", parse_input)
    workflow.add_node("filter", load_and_filter_data)
    workflow.add_node("recommend", llm_recommend)

    # Edge 추가
    workflow.add_edge(START, "parse")
    workflow.add_edge("parse", "filter")
    workflow.add_edge("filter", "recommend")
    workflow.add_edge("recommend", END)

    # 컴파일
    app = workflow.compile()

    return app


# 실행 함수
def run_agent(user_input: str):
    """Agent 실행"""
    app = create_graph()

    initial_state = AgentState(
        {
            "user_input": user_input,
            "weather": "",
            "budget": 0,
            "all_data": "",
            "filtered_strategies": "",
            "recommendation": "",
            "messages": [],
        }
    )

    # initial_state = {
    #     "user_input": user_input,
    #     "weather": "",
    #     "budget": 0,
    #     "all_data": "",
    #     "filtered_strategies": "",
    #     "recommendation": "",
    #     "messages": [],
    # }

    result = app.invoke(initial_state)

    return result["recommendation"]


# 테스트
if __name__ == "__main__":
    print("=== SLA 전략 추천 Agent (Spike) ===\n")

    # 테스트 케이스
    test_cases = [
        "폭설 예보인데 예산 50만원 있어",
        "비가 올 것 같은데 예산은 무제한이야",
        "맑은 날씨야",
    ]

    for test in test_cases:
        print(f"📍 질문: {test}")
        print(run_agent(test))
        print("\n" + "=" * 60 + "\n")
