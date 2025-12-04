import pandas as pd

from src.data_loader import get_agent_names, load_agent_data


def test_load_agetn_data_return_dataframe():
    """CSV 파일을 로드하면 DataFrame을 반환한다."""
    df = load_agent_data("data/sample_agents.csv")
    assert isinstance(df, pd.DataFrame)


def test_load_agent_data_has_data():
    """데이터가 비어 있지 않아야 한다."""
    df = load_agent_data("data/sample_agents.csv")
    assert len(df) > 0


def test_get_agent_names():
    """상담사 이름 목록을 반환한다."""
    df = load_agent_data("data/sample_agents.csv")
    names = get_agent_names(df)
    assert "김철수" in names
    assert "이영희" in names
