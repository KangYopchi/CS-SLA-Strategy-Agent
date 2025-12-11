# Google Sheets Reader를 LangGraph 노드로 통합하는 가이드라인

이 가이드는 `GoogleSheetsReader`를 LangGraph의 노드로 통합하는 방법을 설명합니다.

## 목차

1. [기본 개념](#기본-개념)
2. [State 정의](#state-정의)
3. [노드 구현 패턴](#노드-구현-패턴)
4. [통합 예제](#통합-예제)
5. [에러 처리](#에러-처리)
6. [비동기 처리](#비동기-처리)
7. [모범 사례](#모범-사례)

---

## 기본 개념

### LangGraph 노드의 요구사항

1. **노드 함수 시그니처**: `async def node_name(state: StateClass) -> dict | StateClass`
2. **반환값**: 
   - **권장**: State의 부분 업데이트를 나타내는 `dict` (더 효율적)
   - **가능**: 전체 `StateClass` 객체 반환 (LangGraph가 자동으로 병합)
3. **State 클래스**: `pydantic.BaseModel`을 상속해야 함
4. **파라미터**: 노드 함수는 **오직 state만** 파라미터로 받을 수 있음 (추가 파라미터 불가)
5. **에러 처리**: 노드 내부에서 처리하고 state에 에러 정보 저장

**참고**: 프로젝트의 `agent_spike.py`에서는 `AgentState` 객체를 반환하지만, 가이드라인에서는 `dict` 반환을 권장합니다. 둘 다 작동하지만 `dict` 반환이 더 효율적입니다.

### Google Sheets Reader 통합 전략

- **옵션 1**: 노드 내부에서 `GoogleSheetsReader` 인스턴스 생성 (간단)
- **옵션 2**: 그래프 초기화 시 Reader 인스턴스 생성 후 노드에 전달 (권장)
- **옵션 3**: 의존성 주입 패턴 사용 (고급)

---

## State 정의

Google Sheets 데이터를 처리하는 State를 정의합니다:

```python
from typing import Annotated, Any
from pydantic import BaseModel, Field
import operator

class SheetsAgentState(BaseModel):
    """Google Sheets 데이터를 처리하는 Agent의 State"""
    
    # 입력 파라미터
    spreadsheet_id: str | None = Field(
        default=None, 
        description="Google Sheets 스프레드시트 ID"
    )
    sheet_name: str | None = Field(
        default=None, 
        description="읽을 시트 이름 (예: 'Sheet1', '202501')"
    )
    range_name: str | None = Field(
        default=None, 
        description="읽을 범위 (예: 'A1:D10')"
    )
    
    # 출력 데이터
    sheets_data: list[list[Any]] | None = Field(
        default=None,
        description="스프레드시트 원본 데이터 (행들의 리스트)"
    )
    sheets_json: list[dict[str, Any]] | None = Field(
        default=None,
        description="JSON 형태로 변환된 스프레드시트 데이터"
    )
    
    # 메타데이터
    sheets_status: str = Field(
        default="pending",
        description="스프레드시트 읽기 상태: pending, success, error"
    )
    sheets_error: str | None = Field(
        default=None,
        description="에러 발생 시 에러 메시지"
    )
    
    # 로그/메시지 (Annotated 사용)
    messages: Annotated[list[str], operator.add] = Field(
        default_factory=list,
        description="처리 과정 로그"
    )
```

---

## 노드 구현 패턴

### 패턴 1: 노드 내부에서 Reader 생성 (간단)

```python
from pathlib import Path
from src.google_sheets_reader import GoogleSheetsReader

async def load_sheets_data(state: SheetsAgentState) -> dict:
    """
    Google Sheets에서 데이터를 읽어오는 노드
    
    Args:
        state: SheetsAgentState 인스턴스
        
    Returns:
        State 업데이트를 위한 dict
    """
    # State에서 필요한 정보 추출
    spreadsheet_id = state.spreadsheet_id
    sheet_name = state.sheet_name
    range_name = state.range_name
    
    if not spreadsheet_id:
        return {
            "sheets_status": "error",
            "sheets_error": "spreadsheet_id가 제공되지 않았습니다",
            "messages": ["에러: spreadsheet_id가 필요합니다"]
        }
    
    try:
        # Reader 인스턴스 생성
        credentials_path = Path("credentials.json") 
        reader = GoogleSheetsReader(credentials_path=credentials_path)
        
        # 데이터 읽기
        data = reader.get_sheet_data(
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name,
            range_name=range_name
        )
        
        # JSON 변환
        json_data = reader.to_json(
            data,
            empty_cells_as_none=True
        )
        
        return {
            "sheets_data": data,
            "sheets_json": json_data,
            "sheets_status": "success",
            "sheets_error": None,
            "messages": [f"스프레드시트 데이터를 성공적으로 읽었습니다: {len(json_data)}개 행"]
        }
        
    except Exception as e:
        error_msg = f"스프레드시트 읽기 실패: {str(e)}"
        return {
            "sheets_status": "error",
            "sheets_error": error_msg,
            "messages": [error_msg]
        }
```

### 패턴 2: Reader를 미리 만들어 전달하는 “노드 팩토리” (LangGraph 공식 스타일)

**핵심**: LangGraph 노드는 `state` 하나만 인자로 받습니다. 공식 문서에서도 외부 리소스가 필요할 때는 “노드 팩토리”로 미리 준비한 뒤, state만 받는 함수를 반환하는 방식을 사용합니다.

> 12살 설명  
> - `reader`를 먼저 만든 다음,  
> - `reader`를 쥔 채로 `state`만 받는 함수를 “만들어 내보내는” 또 다른 함수를 만듭니다.  
> - 최종 노드 함수는 `state`만 받으니 LangGraph 규칙을 지키면서, 미리 들고 있던 `reader`를 그대로 씁니다.

```python
from src.google_sheets_reader import GoogleSheetsReader

def create_load_sheets_node(reader: GoogleSheetsReader):
    """
    미리 준비한 reader를 사용해, state만 받는 노드 함수를 만들어 반환합니다.
    (LangGraph 튜토리얼의 리소스 주입 패턴과 동일)
    """
    async def load_sheets_node(state: SheetsAgentState) -> dict:
        # LangGraph 표준 시그니처: state만 받음
        spreadsheet_id = state.spreadsheet_id
        if not spreadsheet_id:
            return {
                "sheets_status": "error",
                "sheets_error": "spreadsheet_id가 제공되지 않았습니다",
                "messages": ["에러: spreadsheet_id가 필요합니다"],
            }

        try:
            json_data = reader.get_sheet_data_as_json(
                spreadsheet_id=spreadsheet_id,
                sheet_name=state.sheet_name,
                range_name=state.range_name,
                empty_cells_as_none=True,
            )

            return {
                "sheets_json": json_data,
                "sheets_status": "success",
                "sheets_error": None,
                "messages": [f"성공: {len(json_data)}개 행 읽음"],
            }
        except Exception as e:
            return {
                "sheets_status": "error",
                "sheets_error": str(e),
                "messages": [f"에러: {str(e)}"],
            }

    return load_sheets_node

# 사용 예제:
# reader = GoogleSheetsReader(credentials_path="credentials.json")
# load_sheets_node = create_load_sheets_node(reader)
# workflow.add_node("load_sheets", load_sheets_node)
```

### 패턴 3: 래퍼 함수 사용 (의존성 주입)

```python
from functools import partial
from pathlib import Path
from src.google_sheets_reader import GoogleSheetsReader

def create_sheets_node(credentials_path: str | Path = "credentials.json"):
    """
    Google Sheets Reader를 사용하는 노드 함수를 생성
    
    Args:
        credentials_path: 서비스 계정 JSON 파일 경로
        
    Returns:
        노드 함수
    """
    reader = GoogleSheetsReader(credentials_path=credentials_path)
    
    async def load_sheets_data(state: SheetsAgentState) -> dict:
        """실제 노드 함수"""
        spreadsheet_id = state.spreadsheet_id
        if not spreadsheet_id:
            return {
                "sheets_status": "error",
                "sheets_error": "spreadsheet_id가 제공되지 않았습니다",
                "messages": ["에러: spreadsheet_id가 필요합니다"]
            }
        
        try:
            data = reader.get_sheet_data(
                spreadsheet_id=spreadsheet_id,
                sheet_name=state.sheet_name,
                range_name=state.range_name
            )
            
            json_data = reader.to_json(data)
            
            return {
                "sheets_data": data,
                "sheets_json": json_data,
                "sheets_status": "success",
                "sheets_error": None,
                "messages": [f"성공: {len(json_data)}개 행 읽음"]
            }
        except Exception as e:
            return {
                "sheets_status": "error",
                "sheets_error": str(e),
                "messages": [f"에러: {str(e)}"]
            }
    
    return load_sheets_data
```

---

## 통합 예제

### 완전한 예제: Google Sheets 데이터를 읽고 분석하는 Agent

```python
from typing import Annotated, Any
from pathlib import Path
import operator
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from src.google_sheets_reader import GoogleSheetsReader


class SheetsAnalysisState(BaseModel):
    """Google Sheets 데이터 분석 Agent의 State"""
    
    # 입력
    spreadsheet_id: str | None = None
    sheet_name: str | None = None
    
    # 데이터
    sheets_json: list[dict[str, Any]] | None = None
    
    # 분석 결과
    analysis_result: dict[str, Any] | None = None
    
    # 상태
    status: str = "pending"
    error: str | None = None
    messages: Annotated[list[str], operator.add] = Field(default_factory=list)


# 노드 1: Google Sheets 데이터 읽기
async def load_sheets_node(state: SheetsAnalysisState) -> dict:
    """스프레드시트 데이터를 읽어오는 노드"""
    if not state.spreadsheet_id:
        return {
            "status": "error",
            "error": "spreadsheet_id가 필요합니다",
            "messages": ["에러: spreadsheet_id가 제공되지 않았습니다"]
        }
    
    try:
        reader = GoogleSheetsReader(credentials_path="credentials.json")
        json_data = reader.get_sheet_data_as_json(
            spreadsheet_id=state.spreadsheet_id,
            sheet_name=state.sheet_name
        )
        
        return {
            "sheets_json": json_data,
            "status": "loaded",
            "messages": [f"스프레드시트 데이터 로드 완료: {len(json_data)}개 행"]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "messages": [f"데이터 로드 실패: {str(e)}"]
        }


# 노드 2: 데이터 분석 (예시)
async def analyze_data_node(state: SheetsAnalysisState) -> dict:
    """로드된 데이터를 분석하는 노드"""
    if not state.sheets_json:
        return {
            "status": "error",
            "error": "분석할 데이터가 없습니다",
            "messages": ["에러: sheets_json이 없습니다"]
        }
    
    # 간단한 분석 예시
    data = state.sheets_json
    row_count = len(data)
    column_count = len(data[0]) if data else 0
    
    analysis = {
        "row_count": row_count,
        "column_count": column_count,
        "columns": list(data[0].keys()) if data else []
    }
    
    return {
        "analysis_result": analysis,
        "status": "completed",
        "messages": [f"분석 완료: {row_count}행, {column_count}열"]
    }


# 그래프 생성
def create_sheets_analysis_graph():
    """Google Sheets 분석 그래프 생성"""
    workflow = StateGraph(SheetsAnalysisState)
    
    # 노드 추가
    workflow.add_node("load_sheets", load_sheets_node)
    workflow.add_node("analyze_data", analyze_data_node)
    
    # 엣지 추가
    workflow.add_edge(START, "load_sheets")
    workflow.add_edge("load_sheets", "analyze_data")
    workflow.add_edge("analyze_data", END)
    
    # 컴파일
    app = workflow.compile()
    return app


# 실행 예제
async def run_example():
    app = create_sheets_analysis_graph()
    
    initial_state = SheetsAnalysisState(
        spreadsheet_id="your-spreadsheet-id",
        sheet_name="Sheet1"
    )
    
    result = await app.ainvoke(initial_state)
    print(result.analysis_result)
```

---

## 에러 처리

### 권장 에러 처리 패턴

```python
async def load_sheets_node(state: SheetsAgentState) -> dict:
    """에러 처리가 포함된 노드"""
    # 1. 입력 검증
    if not state.spreadsheet_id:
        return {
            "sheets_status": "error",
            "sheets_error": "spreadsheet_id가 필요합니다",
            "messages": ["입력 검증 실패: spreadsheet_id 누락"]
        }
    
    try:
        # 2. Reader 생성
        reader = GoogleSheetsReader(credentials_path="credentials.json")
        
        # 3. 데이터 읽기
        json_data = reader.get_sheet_data_as_json(
            spreadsheet_id=state.spreadsheet_id,
            sheet_name=state.sheet_name
        )
        
        # 4. 성공 응답
        return {
            "sheets_json": json_data,
            "sheets_status": "success",
            "sheets_error": None,
            "messages": ["데이터 로드 성공"]
        }
        
    except FileNotFoundError as e:
        # 파일 관련 에러
        return {
            "sheets_status": "error",
            "sheets_error": f"인증 파일을 찾을 수 없습니다: {str(e)}",
            "messages": [f"인증 파일 오류: {str(e)}"]
        }
    
    except Exception as e:
        # 기타 에러
        return {
            "sheets_status": "error",
            "sheets_error": f"스프레드시트 읽기 실패: {str(e)}",
            "messages": [f"에러 발생: {str(e)}"]
        }
```

### 조건부 엣지로 에러 처리

```python
def should_continue(state: SheetsAgentState) -> str:
    """에러 상태에 따라 다음 노드 결정"""
    if state.sheets_status == "error":
        return "handle_error"
    elif state.sheets_status == "success":
        return "process_data"
    else:
        return "end"

# 그래프에 조건부 엣지 추가
workflow.add_conditional_edges(
    "load_sheets",
    should_continue,
    {
        "handle_error": "error_handler",
        "process_data": "analyze_data",
        "end": END
    }
)
```

---

## 비동기 처리

### Google Sheets Reader는 동기 함수

`GoogleSheetsReader`는 현재 동기 함수를 사용합니다. 비동기 노드에서 사용할 때는:

```python
import asyncio

async def load_sheets_node(state: SheetsAgentState) -> dict:
    """비동기 노드에서 동기 Reader 사용"""
    if not state.spreadsheet_id:
        return {"sheets_status": "error", "sheets_error": "spreadsheet_id 필요"}
    
    try:
        reader = GoogleSheetsReader(credentials_path="credentials.json")
        
        # 방법 1: asyncio.to_thread() 사용 (Python 3.9+, 권장)
        json_data = await asyncio.to_thread(
            reader.get_sheet_data_as_json,
            spreadsheet_id=state.spreadsheet_id,
            sheet_name=state.sheet_name
        )
        
        # 방법 2: run_in_executor 사용 (더 세밀한 제어가 필요한 경우)
        # loop = asyncio.get_running_loop()  # 현재 실행 중인 루프 가져오기
        # json_data = await loop.run_in_executor(
        #     None,  # 기본 스레드 풀 사용
        #     lambda: reader.get_sheet_data_as_json(
        #         spreadsheet_id=state.spreadsheet_id,
        #         sheet_name=state.sheet_name
        #     )
        # )
        
        return {
            "sheets_json": json_data,
            "sheets_status": "success",
            "messages": [f"로드 완료: {len(json_data)}개 행"]
        }
    except Exception as e:
        return {
            "sheets_status": "error",
            "sheets_error": str(e),
            "messages": [f"에러: {str(e)}"]
        }
```

**참고**: `asyncio.get_event_loop()`는 Python 3.10+에서 deprecated되었습니다. `asyncio.to_thread()` (Python 3.9+) 또는 `asyncio.get_running_loop()`를 사용하세요.

---

## 모범 사례

### 1. Reader 인스턴스 재사용

```python
# 그래프 생성 시 Reader 인스턴스 생성
def create_graph_with_reader(credentials_path: str | Path = "credentials.json"):
    reader = GoogleSheetsReader(credentials_path=credentials_path)
    
    # 래퍼 함수로 노드 생성
    async def load_sheets_node(state: SheetsAgentState) -> dict:
        # reader를 클로저로 캡처
        json_data = reader.get_sheet_data_as_json(...)
        return {"sheets_json": json_data}
    
    workflow = StateGraph(SheetsAgentState)
    workflow.add_node("load_sheets", load_sheets_node)
    return workflow.compile()
```

### 2. 환경 변수 사용

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

async def load_sheets_node(state: SheetsAgentState) -> dict:
    # 환경 변수에서 설정 읽기
    credentials_path = Path(
        os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    )
    
    reader = GoogleSheetsReader(credentials_path=credentials_path)
    # ...
```

### 3. State 검증

```python
from pydantic import field_validator

class SheetsAgentState(BaseModel):
    spreadsheet_id: str | None = None
    
    @field_validator("spreadsheet_id")
    @classmethod
    def validate_spreadsheet_id(cls, v):
        if v and not v.strip():
            raise ValueError("spreadsheet_id는 비어있을 수 없습니다")
        return v
```

### 4. 로깅 추가

```python
import logging

logger = logging.getLogger(__name__)

async def load_sheets_node(state: SheetsAgentState) -> dict:
    logger.info(f"스프레드시트 읽기 시작: {state.spreadsheet_id}")
    
    try:
        # ... 로직
        logger.info(f"성공: {len(json_data)}개 행 읽음")
        return {"sheets_json": json_data, "sheets_status": "success"}
    except Exception as e:
        logger.error(f"에러 발생: {str(e)}", exc_info=True)
        return {"sheets_status": "error", "sheets_error": str(e)}
```

---

## 체크리스트

노드를 구현할 때 다음을 확인하세요:

- [ ] State에 필요한 필드가 모두 정의되어 있는가?
- [ ] 노드 함수가 `async def`로 정의되어 있는가?
- [ ] 노드 함수가 **state만** 파라미터로 받는가? (추가 파라미터 불가)
- [ ] 반환값이 `dict` 형태인가? (부분 업데이트) 또는 `AgentState` 객체?
- [ ] 에러 처리가 포함되어 있는가?
- [ ] State에 에러 정보가 저장되는가?
- [ ] 로그/메시지가 적절히 기록되는가?
- [ ] Reader 인스턴스가 효율적으로 관리되는가?
- [ ] 비동기 함수에서 `asyncio.to_thread()` 또는 `asyncio.get_running_loop()` 사용?
- [ ] 의존성 주입이 필요한 경우 래퍼 함수 패턴 사용?
- [ ] 조건부 엣지의 반환값이 매핑에 포함되어 있는가?

---

## 추가 리소스

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [Pydantic v2 문서](https://docs.pydantic.dev/latest/)
- [Google Sheets API 문서](https://developers.google.com/sheets/api)
