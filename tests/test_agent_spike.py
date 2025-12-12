"""
sla_agent.py 각 함수에 대한 단위 테스트.
외부 의존성(LLM, Google Sheets)은 monkeypatch로 대체해 순수 함수 로직만 검증합니다.
"""

import pytest


# 기본 상태 데이터 -------------------------------------------------------------
@pytest.fixture
def base_state_dict():
    return {
        "messages": [],
        "spreadsheet_id": "spreadsheet-123",
        "sheet_name": "Sheet1",
        "range_name": "A1:B10",
        "sheets_data": None,
        "report": None,
        "customer_request": "고객 요청 사항",
        "condition": {"weather": "맑음", "event": "없음", "attendance_rate": 0.75},
        "yesterday_data": {
            "income_call": 100,
            "answer_call": 90,
            "sla_result": "A",
        },
    }


# vaildate_input_state --------------------------------------------------------
def test_vaildate_input_state_returns_pydantic_model(base_state_dict):
    result = sla_agent.vaildate_input_state(base_state_dict)

    assert isinstance(result, sla_agent.OverallStateVaildation)
    assert result.spreadsheet_id == "spreadsheet-123"
    assert result.condition["attendance_rate"] == 0.75


# load_sheets_data ------------------------------------------------------------
@pytest.mark.asyncio
async def test_load_sheets_data_success(monkeypatch, base_state_dict):
    sample_rows = [
        ["income_call", "answer_call"],
        [120, 100],
        [130, 110],
    ]

    class FakeReader:
        def __init__(self, credentials_path):
            self.credentials_path = credentials_path

        def get_sheet_data(self, spreadsheet_id, sheet_name=None, range_name=None):
            assert spreadsheet_id == base_state_dict["spreadsheet_id"]
            assert sheet_name == base_state_dict["sheet_name"]
            assert range_name == base_state_dict["range_name"]
            return sample_rows

        def to_json(self, data, empty_cells_as_none=True):
            assert data == sample_rows
            return [
                {"income_call": 120, "answer_call": 100},
                {"income_call": 130, "answer_call": 110},
            ]

    monkeypatch.setattr(sla_agent, "GoogleSheetsReader", FakeReader)
    state_model = sla_agent.OverallStateVaildation(**base_state_dict)

    result = await sla_agent.load_sheets_data(state_model)

    assert result["sheets_data"][0]["income_call"] == 120
    assert len(result["sheets_data"]) == 2


@pytest.mark.asyncio
async def test_load_sheets_data_without_spreadsheet_id_raises(
    monkeypatch, base_state_dict
):
    base_state_dict["spreadsheet_id"] = None
    state_model = sla_agent.OverallStateVaildation(**base_state_dict)

    with pytest.raises(ValueError):
        await sla_agent.load_sheets_data(state_model)


# calculate_sla_grade ---------------------------------------------------------
def test_calculate_sla_grade_summarizes_totals():
    state = {
        "sheets_data": [
            {"income_call": 100, "answer_call": 95},
            {"income_call": 100, "answer_call": 95},
        ]
    }

    result = sla_agent.calculate_sla_grade(state)
    yesterday = result["yesterday_data"]

    assert yesterday["income_call"] == 200
    assert yesterday["answer_call"] == 190
    assert yesterday["sla_result"] == "S"  # 95% 달성 시 S 등급


# generate_report -------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_report_uses_structured_llm(monkeypatch, base_state_dict):
    class FakeStructuredLLM:
        def __init__(self, response):
            self.response = response
            self.prompts = []

        def invoke(self, prompt):
            self.prompts.append(prompt)
            return self.response

    class FakeChatOpenAI:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def with_structured_output(self, model):
            return FakeStructuredLLM(
                sla_agent.AgentStrategy(
                    summary="테스트 요약",
                    urgency="high",
                    strategy="테스트 전략",
                )
            )

    monkeypatch.setattr(sla_agent, "ChatOpenAI", FakeChatOpenAI)

    base_state_dict["yesterday_data"] = {
        "income_call": 150,
        "answer_call": 140,
        "sla_result": "A",
    }
    base_state_dict["condition"] = {
        "weather": "비",
        "event": "이벤트 없음",
        "attendance_rate": 0.9,
    }
    base_state_dict["customer_request"] = "고객 요청"

    result = await sla_agent.generate_report(base_state_dict)

    assert result["summary"] == "테스트 요약"
    assert result["urgency"] == "high"
    assert "전략" in result["strategy"]


# validate_report -------------------------------------------------------------
def test_validate_report_returns_typed_dict(base_state_dict):
    validated = sla_agent.validate_report(base_state_dict)

    assert isinstance(validated, dict)
    assert validated["yesterday_data"]["income_call"] == 100
    assert validated["condition"]["weather"] == "맑음"


# create_graph ----------------------------------------------------------------
def test_create_graph_contains_all_nodes():
    app = sla_agent.create_graph()
    graph = app.get_graph()

    nodes = set(graph.nodes)
    assert {
        "vaildate_input_state",
        "load_sheets_data",
        "calculate_sla_grade",
        "generate_report",
        "validate_report",
    }.issubset(nodes)

    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert ("__start__", "vaildate_input_state") in edges
    assert ("validate_report", "__end__") in edges


# main ------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_main_executes_with_stubbed_graph(monkeypatch, capsys):
    captured_payload: dict = {}

    class FakeGraph:
        async def ainvoke(self, payload):
            captured_payload.update(payload)
            return {"done": True}

    fake_graph = FakeGraph()

    def fake_create_graph():
        return fake_graph

    monkeypatch.setattr(sla_agent, "create_graph", fake_create_graph)
    monkeypatch.setattr(sla_agent, "load_dotenv", lambda: None)
    monkeypatch.setattr(
        sla_agent.os,
        "getenv",
        lambda key: "spreadsheet-id" if key == "GOOGLE_SPREADSHEET_ID" else None,
    )

    await sla_agent.main()
    out = capsys.readouterr().out

    assert "done" in out
    assert captured_payload["spreadsheet_id"] == "spreadsheet-id"
    assert captured_payload["sheet_name"] == "202501"
