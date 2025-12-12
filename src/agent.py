from pathlib import Path
from typing import Annotated, Any, Literal, TypedDict, cast

import pandas as pd
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

SLA_GRADES: dict[str, int] = {"S": 95, "A": 90, "B": 85, "C": 80, "D": 75, "DD": 0}


class OverallState(TypedDict):
    messages: Annotated[list, add_messages]
    spreadsheet_id: str | None
    sheet_name: str | None
    range_name: str | None
    sheets_data: list[dict[str, Any]] | None
    report: (
        dict[
            Literal["summary", "urgency", "strategy"],
            str | Literal["low", "medium", "high", "critical"],
        ]
        | None
    )
    customer_request: str | None
    condition: dict[Literal["weather", "event", "attendance_rate"], str | int | float]
    yesterday_data: dict[Literal["income_call", "answer_call", "sla_result"], int | str]


class OverallStateVaildation(BaseModel):
    messages: Annotated[list, add_messages]
    spreadsheet_id: str | None = Field(
        default=None, description="Google Sheets 스프레드시트 ID"
    )
    sheet_name: str | None = Field(
        default=None, description="읽을 시트 이름 (예: 'Sheet1', '202501')"
    )
    range_name: str | None = Field(default=None, description="읽을 범위 (예: 'A1:D10')")
    sheets_data: list[dict[str, Any]] | None = Field(
        default=None, description="스프레드시트 데이터"
    )
    report: (
        dict[
            Literal["summary", "urgency", "strategy"],
            str | Literal["low", "medium", "high", "critical"],
        ]
        | None
    ) = Field(default=None, description="Report")
    customer_request: str | None = Field(default=None, description="Request")
    condition: dict[
        Literal["weather", "event", "attendance_rate"], str | int | float
    ] = Field(
        default={"weather": "unknown", "event": "unknown", "attendance_rate": 0},
        description="오늘의 상황",
    )
    yesterday_data: dict[
        Literal["income_call", "answer_call", "sla_result"], int | str
    ] = Field(
        default={"income_call": 0, "answer_call": 0, "sla_result": "DD"},
        description="어제의 데이터",
    )


class GoogleSheetsData(TypedDict):
    sheets_data: list[dict[str, Any]] | None


class AgentStrategy(BaseModel):
    summary: str
    urgency: Literal["low", "medium", "high", "critical"]
    strategy: str


def validate_input_state(state: OverallState) -> OverallStateVaildation:
    """입력 데이터 검증"""
    return OverallStateVaildation(**state)


def load_sheets_data(state: OverallStateVaildation) -> GoogleSheetsData:
    """
    Google Sheets에서 데이터를 읽어오는 노드

    Args:
        state: SheetsAgentState 인스턴스

    Returns:
        State 업데이트를 위한 최소한의 데이터 dict
    """
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.gs_reader import GoogleSheetsReader

    # State에서 필요한 정보 추출
    spreadsheet_id: str | None = state.spreadsheet_id
    sheet_name: str | None = state.sheet_name
    range_name: str | None = state.range_name

    if not spreadsheet_id:
        raise ValueError("spreadsheet_id가 제공되지 않았습니다")

    try:
        # Reader 인스턴스 생성
        credentials_path = Path("credentials.json")
        reader = GoogleSheetsReader(credentials_path=credentials_path)

        # 데이터 읽기
        data: list[list[Any]] = reader.get_sheet_data(
            spreadsheet_id=spreadsheet_id, sheet_name=sheet_name, range_name=range_name
        )

        # JSON 변환
        json_data: list[dict[str, Any]] = reader.to_json(data, empty_cells_as_none=True)

        return {
            "sheets_data": json_data,
        }

    except Exception as e:
        raise ValueError(f"스프레드시트 읽기 실패: {str(e)}")


def calculate_sla_grade(state: GoogleSheetsData) -> OverallState:
    """
    SLA 등급을 계산하는 함수

    Args:
        state: GoogleSheetsState 인스턴스

    Returns:
        OverallState 인스턴스
    """

    data: list[dict[str, Any]] | None = state["sheets_data"]
    df = pd.DataFrame(data)

    df["answer_call"] = df["answer_call"].astype(int)
    df["income_call"] = df["income_call"].astype(int)
    sla_rate = round((df["answer_call"].sum() / df["income_call"].sum()) * 100, 2)

    grade = "DD"

    for grade, threshold in SLA_GRADES.items():
        if sla_rate >= threshold:
            grade = grade
            break

    income_call = df["income_call"].sum()
    answer_call = df["answer_call"].sum()

    return {
        "yesterday_data": {
            "income_call": income_call,
            "answer_call": answer_call,
            "sla_result": grade,
        }
    }


def generate_report(state: OverallState) -> OverallState:
    """
    Report를 생성하는 함수

    Args:
        state: OverallState 인스턴스

    Returns:
        OverallState 인스턴스
    """

    prompt = f"""
    <persona>
    당신은 CS 센터의 운영자입니다. 아래의 데이터를 바탕으로 Report를 Rule에 맞춰 작성해주세요. 말투는 센터장님의 근엄한 말투로 실장들에게 전달해주세요.
    </persona>
    <rule>
    1. 고객사 요구사항을 우선적으로 충족시키도록 해주세요.
    2. 어제의 SLA 결과를 바탕으로 오늘의 상황을 고려하여 Report를 작성해주세요.
    3. 오늘의 날씨, 이벤트, 출근인원 비율의 상황을 고려하여 전략을 세워주세요.
    4. Report는 최대 500자 이내로 작성해주세요.
    </rule>
    <data>
    <yesterday_result>
    어제 콜 인입량: {state["yesterday_data"]["income_call"]}
    어제 콜 응답량: {state["yesterday_data"]["answer_call"]}
    어제 SLA: {state["yesterday_data"]["sla_result"]}
    </yesterday_result>
    <customer_request>
    오늘의 고객사 요구사항입니다: {state["customer_request"]}
    </customer_request>
    <condition>
    오늘의 날씨: {state["condition"]["weather"]}
    오늘의 이벤트: {state["condition"]["event"]}
    오늘의 출근인원 비율: {state["condition"]["attendance_rate"]}
    </condition>
    </data>

    <example>
    summary: 폭설로 인한 인원 추가 및 AUX 최소화 전략
    urgency: critical
    strategy:
    1. 오늘은 **폭설**이 예상됩니다. 고객사 요청사항입니다. 배달지연에 대해서는 "도착시간 확인불가"로 통일되게 대응해 ATT를 최대한 줄여주세요.
    2. 어제 폭설로 인해 10~14시 사이에 AHT가 급증했습니다. 해당 시간에는 AUX가 발생하지 않도록 이석 관리가 필요합니다. 식사시간을 최대한 조정해서 AUX를 최소화 해주세요.
    3. 또한 오늘은 출근인원 비율이 높지 않습니다. 따라서 휴무인 인원 중 일부를 추가 근무 가능한지 확인해주세요.
    4. 어제 SLA 점수가 낮습니다. 금일 응답콜 목표를 60% 달성할 경우 A 등급을 받기로 했습니다. 응답콜을 높이기 위해 배달지연, 단순확인 등의 콜은 일관된 답변을 제공해주세요.
    </example>
    """

    llm = ChatOpenAI(model="gpt-5-mini")
    structured_llm = llm.with_structured_output(AgentStrategy)

    # type hinting error 로 인해 cast 사용
    report_strategy = cast(AgentStrategy, structured_llm.invoke(prompt))

    return {
        "report": {
            "summary": report_strategy.summary,
            "urgency": report_strategy.urgency,
            "strategy": report_strategy.strategy,
        }
    }


def validate_report(state: OverallState) -> OverallState:
    """
    Report를 검증하는 함수

    Args:
        state: OverallState 인스턴스

    Returns:
        OverallState 인스턴스
    """

    return OverallState(**OverallStateVaildation(**state).model_dump())


def create_graph() -> CompiledStateGraph:
    workflow = StateGraph(OverallState)

    workflow.add_node("validate_input_state", validate_input_state)
    workflow.add_node("load_sheets_data", load_sheets_data)
    workflow.add_node("calculate_sla_grade", calculate_sla_grade)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("validate_report", validate_report)

    workflow.add_edge(START, "validate_input_state")
    workflow.add_edge("validate_input_state", "load_sheets_data")
    workflow.add_edge("load_sheets_data", "calculate_sla_grade")
    workflow.add_edge("calculate_sla_grade", "generate_report")
    # workflow.add_edge("generate_report", "validate_report")
    workflow.add_edge("generate_report", END)

    graph = workflow.compile()

    return graph
