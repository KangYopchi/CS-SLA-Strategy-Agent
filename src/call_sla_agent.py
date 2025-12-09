"""
Call SLA Analysis Agent
LangGraph를 사용한 콜센터 SLA 분석 시스템
"""

from typing import Annotated, TypedDict

import pandas as pd
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# State 정의
class CallSLAState(TypedDict):
    """콜센터 SLA 분석 Agent의 상태를 저장하는 클래스"""

    # 입력
    csv_path: str

    # 중간 결과
    raw_data: pd.DataFrame  # 로드된 원본 데이터
    sla_data: pd.DataFrame  # SLA 계산 결과

    # 출력
    report: str  # 최종 리포트
    messages: Annotated[list, add_messages]


# Node 1: 데이터 로드
def load_data(state: CallSLAState) -> CallSLAState:
    """
    CSV 파일을 읽어서 데이터프레임으로 로드
    """
    csv_path = state.get("csv_path", "data/yesterday_calls.csv")

    try:
        df = pd.read_csv(csv_path)
        state["raw_data"] = df
        print(f"✅ 데이터 로드 완료: {len(df)}개 행")
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        state["raw_data"] = pd.DataFrame()

    return state


# Node 2: SLA 계산
def calculate_sla(state: CallSLAState) -> CallSLAState:
    """
    응답률과 등급을 계산
    - 응답률 = (응답콜 / 인입콜) * 100
    - 등급: S(95% 이상), A(90-94%), B(80-89%), C(70-79%), D(70% 미만)
    """
    df = state.get("raw_data", pd.DataFrame())

    if df.empty:
        state["sla_data"] = pd.DataFrame()
        return state

    # 응답률 계산
    df = df.copy()
    df["응답률"] = (df["응답콜"] / df["인입콜"] * 100).round(2)

    # 등급 계산
    def get_grade(response_rate: float) -> str:
        if response_rate >= 95:
            return "S"
        elif response_rate >= 90:
            return "A"
        elif response_rate >= 80:
            return "B"
        elif response_rate >= 70:
            return "C"
        else:
            return "D"

    df["등급"] = df["응답률"].apply(get_grade)

    # 전체 통계 추가
    total_inbound = df["인입콜"].sum()
    total_answered = df["응답콜"].sum()
    overall_response_rate = (
        (total_answered / total_inbound * 100).round(2) if total_inbound > 0 else 0
    )
    overall_grade = get_grade(overall_response_rate)

    # 통계 정보를 별도 컬럼으로 추가 (각 행에 전체 통계 포함)
    df["전체_인입콜"] = total_inbound
    df["전체_응답콜"] = total_answered
    df["전체_응답률"] = overall_response_rate
    df["전체_등급"] = overall_grade

    state["sla_data"] = df
    print(
        f"✅ SLA 계산 완료: 전체 응답률 {overall_response_rate}% ({overall_grade}등급)"
    )

    return state


# Node 3: 리포트 생성
def generate_report(state: CallSLAState) -> CallSLAState:
    """
    계산된 SLA 데이터를 바탕으로 리포트 생성
    """
    df = state.get("sla_data", pd.DataFrame())

    if df.empty:
        state["report"] = "❌ 데이터가 없어 리포트를 생성할 수 없습니다."
        return state

    # 전체 통계 (첫 번째 행에서 가져오기)
    total_inbound = df["전체_인입콜"].iloc[0] if len(df) > 0 else 0
    total_answered = df["전체_응답콜"].iloc[0] if len(df) > 0 else 0
    overall_response_rate = df["전체_응답률"].iloc[0] if len(df) > 0 else 0
    overall_grade = df["전체_등급"].iloc[0] if len(df) > 0 else "N/A"

    # 시간대별 요약
    hourly_summary = df[["시간", "인입콜", "응답콜", "응답률", "등급"]].copy()

    # 등급별 통계
    grade_counts = df["등급"].value_counts().to_dict()

    # 리포트 생성
    report = f"""
# 📊 콜센터 SLA 분석 리포트

## 📈 전체 통계
- **전체 인입콜**: {total_inbound:,}건
- **전체 응답콜**: {total_answered:,}건
- **전체 응답률**: {overall_response_rate:.2f}%
- **전체 등급**: {overall_grade}등급

## 📊 등급별 분포
"""

    for grade in ["S", "A", "B", "C", "D"]:
        count = grade_counts.get(grade, 0)
        if count > 0:
            report += f"- **{grade}등급**: {count}시간대\n"

    report += """
## ⏰ 시간대별 상세 현황

| 시간 | 인입콜 | 응답콜 | 응답률 | 등급 |
|------|--------|--------|--------|------|
"""

    for _, row in hourly_summary.iterrows():
        report += f"| {int(row['시간'])}시 | {int(row['인입콜'])} | {int(row['응답콜'])} | {row['응답률']:.2f}% | {row['등급']} |\n"

    # 최고/최저 성과 시간대
    best_hour = hourly_summary.loc[hourly_summary["응답률"].idxmax()]
    worst_hour = hourly_summary.loc[hourly_summary["응답률"].idxmin()]

    report += f"""
## 🏆 주요 지표

### 최고 성과 시간대
- **시간**: {int(best_hour["시간"])}시
- **응답률**: {best_hour["응답률"]:.2f}% ({best_hour["등급"]}등급)
- **인입/응답**: {int(best_hour["인입콜"])}건 / {int(best_hour["응답콜"])}건

### 개선 필요 시간대
- **시간**: {int(worst_hour["시간"])}시
- **응답률**: {worst_hour["응답률"]:.2f}% ({worst_hour["등급"]}등급)
- **인입/응답**: {int(worst_hour["인입콜"])}건 / {int(worst_hour["응답콜"])}건

---
*리포트 생성 완료*
"""

    state["report"] = report
    print("✅ 리포트 생성 완료")

    return state


# Graph 구성
def create_graph():
    """LangGraph 생성"""
    workflow = StateGraph(CallSLAState)

    # Node 추가
    # pyrefly: ignore [no-matching-overload]
    workflow.add_node("load_data", load_data)
    # pyrefly: ignore [no-matching-overload]
    workflow.add_node("calculate_sla", calculate_sla)
    # pyrefly: ignore [no-matching-overload]
    workflow.add_node("generate_report", generate_report)

    # Edge 추가
    workflow.add_edge(START, "load_data")
    workflow.add_edge("load_data", "calculate_sla")
    workflow.add_edge("calculate_sla", "generate_report")
    workflow.add_edge("generate_report", END)

    # 컴파일
    app = workflow.compile()

    return app


# 실행 함수
def run_agent(csv_path: str = "data/yesterday_calls.csv"):
    """Agent 실행"""
    app = create_graph()

    initial_state = CallSLAState(
        {
            "csv_path": csv_path,
            "raw_data": pd.DataFrame(),
            "sla_data": pd.DataFrame(),
            "report": "",
            "messages": [],
        }
    )

    print("=" * 60)
    print("📊 콜센터 SLA 분석 Agent 시작")
    print("=" * 60)
    print("\n그래프 구조:")
    png_path = "graph/sla_graph.png"
    print(app.get_graph().draw_mermaid_png(output_file_path=png_path))
    print("\n" + "=" * 60 + "\n")

    langfuse_handler = CallbackHandler()

    result = app.invoke(initial_state, config={"callbacks": [langfuse_handler]})

    return result["report"]


# 테스트
if __name__ == "__main__":
    print("=== 콜센터 SLA 분석 Agent ===\n")

    # 리포트 생성
    report = run_agent("data/yesterday_calls.csv")
    print(report)
