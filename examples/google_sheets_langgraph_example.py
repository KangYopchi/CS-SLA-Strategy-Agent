"""
Google Sheets Reader를 LangGraph 노드로 사용하는 예제
"""

import asyncio
import operator
import os

# 프로젝트 루트에서 src 모듈 import
import sys
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.google_sheets_reader import GoogleSheetsReader

load_dotenv()


class SheetsAgentState(BaseModel):
    """Google Sheets 데이터를 처리하는 Agent의 State"""

    # 입력 파라미터
    spreadsheet_id: str | None = Field(
        default=None, description="Google Sheets 스프레드시트 ID"
    )
    sheet_name: str | None = Field(
        default=None, description="읽을 시트 이름 (예: 'Sheet1', '202501')"
    )
    range_name: str | None = Field(default=None, description="읽을 범위 (예: 'A1:D10')")

    # 출력 데이터
    sheets_data: list[list[Any]] | None = Field(
        default=None, description="스프레드시트 원본 데이터 (행들의 리스트)"
    )
    sheets_json: list[dict[str, Any]] | None = Field(
        default=None, description="JSON 형태로 변환된 스프레드시트 데이터"
    )

    # 메타데이터
    sheets_status: str = Field(
        default="pending", description="스프레드시트 읽기 상태: pending, success, error"
    )
    sheets_error: str | None = Field(
        default=None, description="에러 발생 시 에러 메시지"
    )

    # 로그/메시지
    messages: Annotated[list[str], operator.add] = Field(
        default_factory=list, description="처리 과정 로그"
    )


# 패턴 1: 노드 내부에서 Reader 생성
async def load_sheets_node_simple(state: SheetsAgentState) -> dict:
    """
    Google Sheets에서 데이터를 읽어오는 노드 (간단한 패턴)
    """
    spreadsheet_id = state.spreadsheet_id
    sheet_name = state.sheet_name
    range_name = state.range_name

    if not spreadsheet_id:
        return {
            "sheets_status": "error",
            "sheets_error": "spreadsheet_id가 제공되지 않았습니다",
            "messages": ["에러: spreadsheet_id가 필요합니다"],
        }

    try:
        # 환경 변수에서 credentials 경로 가져오기
        credentials_path = Path(
            os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        )

        # Reader 인스턴스 생성
        reader = GoogleSheetsReader(credentials_path=credentials_path)

        # 데이터 읽기 및 JSON 변환
        json_data = reader.get_sheet_data_as_json(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            range_name=range_name,
            empty_cells_as_none=True,
        )

        return {
            "sheets_json": json_data,
            "sheets_status": "success",
            "sheets_error": None,
            "messages": [
                f"스프레드시트 데이터를 성공적으로 읽었습니다: {len(json_data)}개 행"
            ],
        }

    except FileNotFoundError as e:
        error_msg = f"인증 파일을 찾을 수 없습니다: {str(e)}"
        return {
            "sheets_status": "error",
            "sheets_error": error_msg,
            "messages": [error_msg],
        }
    except Exception as e:
        error_msg = f"스프레드시트 읽기 실패: {str(e)}"
        return {
            "sheets_status": "error",
            "sheets_error": error_msg,
            "messages": [error_msg],
        }


# 패턴 2: Reader를 외부에서 주입 (권장)
def create_load_sheets_node(reader: GoogleSheetsReader):
    """
    Google Sheets Reader를 사용하는 노드 함수를 생성 (의존성 주입)

    Args:
        reader: GoogleSheetsReader 인스턴스

    Returns:
        노드 함수
    """

    async def load_sheets_node(state: SheetsAgentState) -> dict:
        """실제 노드 함수"""
        spreadsheet_id = state.spreadsheet_id
        sheet_name = state.sheet_name
        range_name = state.range_name

        if not spreadsheet_id:
            return {
                "sheets_status": "error",
                "sheets_error": "spreadsheet_id가 제공되지 않았습니다",
                "messages": ["에러: spreadsheet_id가 필요합니다"],
            }

        try:
            # Reader 인스턴스는 클로저로 캡처됨
            json_data = reader.get_sheet_data_as_json(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                range_name=range_name,
                empty_cells_as_none=True,
            )

            return {
                "sheets_json": json_data,
                "sheets_status": "success",
                "sheets_error": None,
                "messages": [
                    f"스프레드시트 데이터를 성공적으로 읽었습니다: {len(json_data)}개 행"
                ],
            }
        except Exception as e:
            error_msg = f"스프레드시트 읽기 실패: {str(e)}"
            return {
                "sheets_status": "error",
                "sheets_error": error_msg,
                "messages": [error_msg],
            }

    return load_sheets_node


# 분석 노드 예제
async def analyze_data_node(state: SheetsAgentState) -> dict:
    """로드된 데이터를 분석하는 노드"""
    if not state.sheets_json:
        return {
            "sheets_status": "error",
            "sheets_error": "분석할 데이터가 없습니다",
            "messages": ["에러: sheets_json이 없습니다"],
        }

    # 간단한 분석 예시
    data = state.sheets_json
    row_count = len(data)
    column_count = len(data[0]) if data else 0
    columns = list(data[0].keys()) if data else []

    analysis_info = (
        f"분석 완료: {row_count}행, {column_count}열, 컬럼: {', '.join(columns[:5])}"
    )

    return {
        "messages": [analysis_info],
    }


# 에러 처리 노드
async def handle_error_node(state: SheetsAgentState) -> dict:
    """에러를 처리하는 노드"""
    error_msg = state.sheets_error or "알 수 없는 에러"
    return {
        "sheets_status": "error_handled",  # 상태 명시적 업데이트
        "messages": [f"에러 처리 완료: {error_msg}"],
    }


# 조건부 라우팅 함수
def should_continue(state: SheetsAgentState) -> str:
    """에러 상태에 따라 다음 노드 결정"""
    if state.sheets_status == "error":
        return "handle_error"
    elif state.sheets_status == "success":
        return "analyze_data"
    else:
        return "end"


# 그래프 생성 함수들
def create_simple_graph():
    """간단한 그래프 생성 (패턴 1)"""
    workflow = StateGraph(SheetsAgentState)

    workflow.add_node("load_sheets", load_sheets_node_simple)
    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("handle_error", handle_error_node)

    workflow.add_edge(START, "load_sheets")
    workflow.add_conditional_edges(
        "load_sheets",
        should_continue,
        {
            "handle_error": "handle_error",
            "analyze_data": "analyze_data",
            "end": END,
        },
    )
    workflow.add_edge("analyze_data", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


def create_graph_with_reader():
    """Reader를 주입하는 그래프 생성 (패턴 2, 권장)"""
    # Reader 인스턴스 생성
    credentials_path = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json"))
    reader = GoogleSheetsReader(credentials_path=credentials_path)

    # 노드 생성
    load_sheets_node = create_load_sheets_node(reader)

    # 그래프 구성
    workflow = StateGraph(SheetsAgentState)

    workflow.add_node("load_sheets", load_sheets_node)
    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("handle_error", handle_error_node)

    workflow.add_edge(START, "load_sheets")
    workflow.add_conditional_edges(
        "load_sheets",
        should_continue,
        {
            "handle_error": "handle_error",
            "analyze_data": "analyze_data",
            "end": END,
        },
    )
    workflow.add_edge("analyze_data", END)
    workflow.add_edge("handle_error", END)

    return workflow.compile()


# 실행 함수
async def run_example():
    """예제 실행"""
    # 환경 변수 확인
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    if not spreadsheet_id:
        print(
            "환경 변수를 설정하세요:\n"
            "  GOOGLE_CREDENTIALS_PATH: 서비스 계정 JSON 파일 경로\n"
            "  GOOGLE_SPREADSHEET_ID: 스프레드시트 ID"
        )
        return

    # 그래프 생성 (패턴 2 사용)
    app = create_graph_with_reader()

    # 초기 상태 설정
    initial_state = SheetsAgentState(
        spreadsheet_id=spreadsheet_id,
        sheet_name="Sheet1",  # 또는 원하는 시트 이름
    )

    # 그래프 실행
    print("그래프 실행 시작...")
    result = await app.ainvoke(initial_state)

    # 결과 출력
    print("\n=== 실행 결과 ===")
    print(f"상태: {result.sheets_status}")
    print(f"메시지: {result.messages}")
    if result.sheets_json and len(result.sheets_json) > 0:
        print(f"데이터 행 수: {len(result.sheets_json)}")
        print(f"첫 번째 행 샘플: {result.sheets_json[0]}")
    if result.sheets_error:
        print(f"에러: {result.sheets_error}")


if __name__ == "__main__":
    asyncio.run(run_example())
