# 코드 리뷰: agent_spike.py

## 🔍 단계별 문제점 및 개선사항

### 1단계: State 정의 및 타입 안정성

#### ❌ 문제점
1. **Pydantic BaseModel 사용 시 LangGraph 호환성**
   - `AgentState`가 `BaseModel`을 상속하지만, LangGraph의 `StateGraph`는 주로 `TypedDict`를 기대합니다
   - `Annotated[list, add_messages]`는 LangGraph의 메시지 타입인데, Pydantic과 함께 사용할 때 검증 이슈가 발생할 수 있습니다

2. **타입 힌트 불일치**
   - `sla_result: str | None`로 정의했지만, 초기값이 `None`이고 실제로는 항상 문자열이 할당됩니다
   - `message` 필드가 `Annotated[list, add_messages]`인데 기본값이 없어서 초기화 시 필수입니다

3. **필드 설명 부족**
   - `Field`의 `description`이 있지만, 실제 사용 맥락에서 어떤 값이 들어와야 하는지 명확하지 않습니다

#### ✅ 개선 방안
```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict, total=False):
    """Agent 상태를 관리하는 TypedDict"""
    income_call: int
    answer_call: int
    sla_goal: str
    sla_result: str
    report: str | None
    simulation: str | None
    messages: Annotated[list, add_messages]
```

또는 Pydantic을 계속 사용한다면:
```python
class AgentState(BaseModel):
    income_call: int = 0
    answer_call: int = 0
    sla_goal: str = "S"
    sla_result: str | None = None
    report: str | None = None
    simulation: str | None = None
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
```

---

### 2단계: 데이터 로딩 및 계산 로직

#### ❌ 문제점
1. **하드코딩된 경로**
   ```python
   csv_path = "data/yesterday_calls.csv"  # 하드코딩
   ```
   - 테스트나 다른 데이터셋 사용이 어렵습니다
   - State에 `csv_path`가 없어서 재사용성이 떨어집니다

2. **계산 로직 오류**
   ```python
   result = round(answer_call / income_call, 2) * 100
   ```
   - `round()`를 곱하기 전에 적용하면 정밀도가 손실됩니다
   - 올바른 순서: `(answer_call / income_call) * 100` 후 `round()`

3. **0으로 나누기 예외 처리 부재**
   - `income_call`이 0이면 `ZeroDivisionError` 발생
   - 예외 처리가 있지만 계산 전에 검증하지 않습니다

4. **SLA 등급 기준 불일치**
   - 원본(`call_sla_agent.py`)은 90-94%가 A등급인데, 여기서는 85-89%가 B등급
   - 기준이 일관되지 않습니다

5. **에러 처리 후 상태 불일치**
   ```python
   except Exception as e:
       print(f"Data Load error: {e}")
   # sla_result가 설정되지 않으면 None 상태로 남음
   ```

#### ✅ 개선 방안
```python
def load_data(state: AgentState) -> AgentState:
    csv_path = state.get("csv_path", "data/yesterday_calls.csv")
    
    try:
        df = pd.read_csv(csv_path)
        
        # 데이터 검증
        if df.empty:
            raise ValueError("CSV 파일이 비어있습니다")
        
        required_columns = ["인입콜", "응답콜"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
        
        income_call = int(df["인입콜"].sum())
        answer_call = int(df["응답콜"].sum())
        
        # 0으로 나누기 방지
        if income_call == 0:
            raise ValueError("인입콜이 0입니다. 계산할 수 없습니다.")
        
        # 정확한 계산 순서
        response_rate = (answer_call / income_call) * 100
        result = round(response_rate, 2)
        
        # SLA 등급 계산 (함수로 분리)
        sla_result = calculate_sla_grade(result)
        
        state["income_call"] = income_call
        state["answer_call"] = answer_call
        state["sla_result"] = sla_result
        
        print(f"✅ 데이터 로드 완료: 인입콜={income_call}, 응답콜={answer_call}, SLA={sla_result}")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        state["sla_result"] = "ERROR"
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        state["sla_result"] = "ERROR"
    
    return state

def calculate_sla_grade(response_rate: float) -> str:
    """SLA 등급 계산 (일관된 기준 적용)"""
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
```

---

### 3단계: 리포트 생성 로직

#### ❌ 문제점
1. **프롬프트 미사용**
   ```python
   prompt = f"""..."""  # 정의만 하고 사용 안 함
   report = f"""..."""  # 하드코딩된 리포트
   ```
   - 프롬프트를 작성했지만 실제로 LLM을 호출하지 않습니다
   - 리포트가 단순 문자열 포맷팅으로만 구성됩니다

2. **날짜 정보 하드코딩**
   ```python
   안녕하세요. [어제 일자] 의 SLA 결과를 보고드립니다.
   ```
   - 실제 날짜가 아닌 플레이스홀더

3. **시뮬레이션 정보 미반영**
   - `state.simulation`을 프롬프트에 포함했지만 실제 리포트에는 반영되지 않습니다

4. **데이터 포맷팅 부족**
   - 숫자에 천 단위 구분자나 포맷팅이 없습니다
   - 리포트 구조가 일관되지 않습니다

#### ✅ 개선 방안
```python
from datetime import datetime, timedelta

def generate_report(state: AgentState) -> AgentState:
    """리포트 생성 (LLM 사용 또는 구조화된 템플릿)"""
    
    # 날짜 정보 추가
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y년 %m월 %d일")
    
    # 데이터 검증
    if state.get("sla_result") is None or state.get("sla_result") == "ERROR":
        state["report"] = "❌ 데이터 로드 실패로 리포트를 생성할 수 없습니다."
        return state
    
    # 응답률 계산
    income_call = state.get("income_call", 0)
    answer_call = state.get("answer_call", 0)
    response_rate = round((answer_call / income_call * 100), 2) if income_call > 0 else 0
    
    # 리포트 생성
    report = f"""
# 📊 콜센터 SLA 분석 리포트

## 📅 분석 일자
{yesterday}

## 📈 전체 통계
- **전체 인입콜**: {income_call:,}건
- **전체 응답콜**: {answer_call:,}건
- **전체 응답률**: {response_rate:.2f}%
- **현재 SLA 등급**: {state.get('sla_result', 'N/A')}
- **목표 SLA 등급**: {state.get('sla_goal', 'N/A')}
"""
    
    # 시뮬레이션 정보가 있으면 추가
    if state.get("simulation"):
        report += f"""
## 🎯 시뮬레이션 시나리오
{state.get('simulation')}
"""
    
    # 목표 달성 여부
    goal_achieved = _is_goal_achieved(state.get("sla_result"), state.get("sla_goal"))
    report += f"""
## ✅ 목표 달성 여부
{'✅ 목표를 달성했습니다!' if goal_achieved else '⚠️ 목표를 달성하지 못했습니다.'}
"""
    
    state["report"] = report
    return state

def _is_goal_achieved(current: str, goal: str) -> bool:
    """목표 달성 여부 판단"""
    grade_order = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "DD": 0}
    return grade_order.get(current, 0) >= grade_order.get(goal, 0)
```

---

### 4단계: Graph 구성 및 실행

#### ❌ 문제점
1. **하드코딩된 초기 상태**
   ```python
   initState = AgentState(
       sla_goal="A",
       simulation="오늘 점심부터 눈이 올 예정이며...",
       ...
   )
   ```
   - 실행 함수에 하드코딩되어 재사용성이 떨어집니다

2. **반환값 처리 부족**
   ```python
   result = app.invoke(initState)
   print(result)  # 전체 state를 출력
   ```
   - 리포트만 반환하거나 구조화된 결과를 반환해야 합니다

3. **에러 핸들링 부재**
   - Graph 실행 중 발생할 수 있는 예외를 처리하지 않습니다

4. **로깅/모니터링 부재**
   - 원본 코드처럼 Langfuse 같은 모니터링이 없습니다

#### ✅ 개선 방안
```python
def run_agent(
    csv_path: str = "data/yesterday_calls.csv",
    sla_goal: str = "S",
    simulation: str | None = None
) -> dict:
    """Agent 실행 함수"""
    app = create_graph()
    
    initial_state: AgentState = {
        "csv_path": csv_path,
        "income_call": 0,
        "answer_call": 0,
        "sla_goal": sla_goal,
        "sla_result": None,
        "report": None,
        "simulation": simulation,
        "messages": [],
    }
    
    try:
        result = app.invoke(initial_state)
        return {
            "success": True,
            "report": result.get("report"),
            "sla_result": result.get("sla_result"),
            "income_call": result.get("income_call"),
            "answer_call": result.get("answer_call"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "report": None,
        }
```

---

### 5단계: 코드 구조 및 모범 사례

#### ❌ 문제점
1. **함수 분리 부족**
   - SLA 등급 계산 로직이 `load_data` 안에 섞여 있습니다
   - 재사용 가능한 유틸리티 함수로 분리해야 합니다

2. **상수 정의 부재**
   - SLA 등급 기준값이 하드코딩되어 있습니다
   - 설정 파일이나 상수로 관리해야 합니다

3. **문서화 부족**
   - 함수 docstring이 없거나 부족합니다
   - 타입 힌트가 일부 누락되었습니다

4. **테스트 가능성**
   - 하드코딩과 긴밀한 결합으로 단위 테스트가 어렵습니다

#### ✅ 개선 방안
```python
# 상수 정의
SLA_GRADE_THRESHOLDS = {
    "S": 95.0,
    "A": 90.0,
    "B": 80.0,
    "C": 70.0,
    "D": 0.0,
}

def calculate_sla_grade(response_rate: float) -> str:
    """
    응답률을 기반으로 SLA 등급을 계산합니다.
    
    Args:
        response_rate: 응답률 (0-100 사이의 값)
    
    Returns:
        SLA 등급 (S, A, B, C, D 중 하나)
    
    Examples:
        >>> calculate_sla_grade(95.5)
        'S'
        >>> calculate_sla_grade(87.3)
        'B'
    """
    if response_rate >= SLA_GRADE_THRESHOLDS["S"]:
        return "S"
    elif response_rate >= SLA_GRADE_THRESHOLDS["A"]:
        return "A"
    elif response_rate >= SLA_GRADE_THRESHOLDS["B"]:
        return "B"
    elif response_rate >= SLA_GRADE_THRESHOLDS["C"]:
        return "C"
    else:
        return "D"
```

---

## 📋 종합 개선 체크리스트

- [ ] State 정의를 TypedDict로 변경하거나 Pydantic 설정 개선
- [ ] 하드코딩된 경로를 State 파라미터로 변경
- [ ] 계산 로직 순서 수정 (round 후 곱하기 → 곱하기 후 round)
- [ ] 0으로 나누기 예외 처리 추가
- [ ] SLA 등급 기준을 상수로 분리하고 일관성 유지
- [ ] 에러 발생 시 상태를 명확히 설정
- [ ] 리포트 생성 시 실제 날짜 사용
- [ ] 시뮬레이션 정보를 리포트에 반영
- [ ] 함수를 작은 단위로 분리 (단일 책임 원칙)
- [ ] 타입 힌트 및 docstring 추가
- [ ] 실행 함수에 파라미터 추가로 재사용성 향상
- [ ] 반환값 구조화
- [ ] 예외 처리 강화
- [ ] 테스트 코드 작성
