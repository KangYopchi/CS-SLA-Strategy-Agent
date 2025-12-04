import pandas as pd


def load_agent_data(file_path: str) -> pd.DataFrame:
    """상담사 실적 데이터를 로드한다."""
    return pd.read_csv(file_path)


def get_agent_names(df: pd.DataFrame) -> list:
    """상담사 이름 목록을 반환한다."""
    return df["agent_name"].unique().tolist()
