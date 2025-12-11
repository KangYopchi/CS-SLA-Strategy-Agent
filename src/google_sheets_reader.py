"""
Google Sheets 데이터를 JSON 형태로 변환하는 모듈
"""

import json
from pathlib import Path
from typing import Any

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    raise ImportError(
        "Google API 클라이언트가 설치되지 않았습니다. "
        "다음 명령어로 설치하세요: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        "또는: uv add google-api-python-client google-auth-httplib2 google-auth-oauthlib"
    )


class GoogleSheetsReader:
    """Google Sheets에서 데이터를 읽어 JSON으로 변환하는 클래스"""

    def __init__(
        self,
        credentials_path: str | Path | None = None,
        token_path: str | Path | None = None,
        scopes: list[str] | None = None,
    ):
        """
        Args:
            credentials_path: 서비스 계정 JSON 파일 경로 (서비스 계정 사용 시)
            token_path: OAuth 토큰 파일 경로 (OAuth 사용 시)
            scopes: Google API 스코프 (기본값: ['https://www.googleapis.com/auth/spreadsheets.readonly'])

        Note:
            - **서비스 계정 사용 시**: 권한은 다음 세 가지가 모두 필요합니다:
              * IAM 역할: Google Cloud 프로젝트 레벨 권한 (Google Cloud Console에서 설정)
              * OAuth Scopes: API 접근 수준 정의 (예: readonly는 읽기만, spreadsheets는 읽기/쓰기)
              * 스프레드시트 공유 설정: 특정 파일에 대한 접근 권한 (스프레드시트에 서비스 계정 이메일 공유)
                기본값(readonly)은 읽기 전용 작업에 적합합니다. 쓰기가 필요하면 'spreadsheets' scope를 사용하세요.
              * 구글 시트의 공유 설정 & 코드의 Scope 설정이 모두 충족되어야 권한을 얻을 수 있다.

            - **OAuth 사용 시**: scopes는 사용자가 부여할 권한 범위를 결정하므로 중요합니다.
        """
        if scopes is None:
            scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        self.scopes = scopes
        self.service = None

        if credentials_path:
            # 서비스 계정 사용
            # 참고: 서비스 계정의 권한은 IAM 역할, OAuth scopes, 스프레드시트 공유 설정이 모두 필요합니다.
            # scopes는 API 접근 수준을 정의하므로 중요합니다 (readonly는 읽기만, spreadsheets는 읽기/쓰기).
            self._init_service_account(credentials_path)
        elif token_path:
            # OAuth 토큰 사용
            # 참고: OAuth의 경우 scopes가 사용자가 부여할 권한 범위를 결정하므로 중요합니다.
            self._init_oauth(token_path)
        else:
            raise ValueError(
                "credentials_path 또는 token_path 중 하나를 제공해야 합니다."
            )

    def _init_service_account(self, credentials_path: str | Path) -> None:
        """
        서비스 계정으로 인증 초기화

        참고: 서비스 계정의 권한은 다음 세 가지가 모두 필요합니다:
        1. IAM 역할: Google Cloud Console에서 프로젝트 레벨 권한 설정
        2. OAuth Scopes: API 접근 수준 정의 (readonly는 읽기만, spreadsheets는 읽기/쓰기)
        3. 스프레드시트 공유: 특정 스프레드시트에 서비스 계정 이메일을 공유해야 접근 가능
        """
        creds = service_account.Credentials.from_service_account_file(
            str(credentials_path), scopes=self.scopes
        )
        self.service = build("sheets", "v4", credentials=creds)

    def _init_oauth(self, token_path: str | Path) -> None:
        """
        OAuth 토큰으로 인증 초기화

        참고: OAuth의 경우 scopes가 사용자가 부여할 권한 범위를 결정하므로 중요합니다.
        현재는 사용하고 있지 않습니다.
        """
        creds = Credentials.from_authorized_user_file(str(token_path), self.scopes)
        self.service = build("sheets", "v4", credentials=creds)

    def get_sheet_data(
        self,
        spreadsheet_id: str,
        range_name: str | None = None,
        sheet_name: str | None = None,
        value_render_option: str = "FORMATTED_VALUE",
    ) -> list[list[Any]]:
        """
        스프레드시트에서 데이터를 가져옵니다.

        Args:
            spreadsheet_id: Google Sheets 스프레드시트 ID
            range_name: 읽을 범위 (예: 'Sheet1!A1:D10' 또는 'A1:D10')
            sheet_name: 시트 이름 (range_name이 없을 경우 전체 시트 읽기)
            value_render_option: 값 렌더링 옵션 ('FORMATTED_VALUE', 'UNFORMATTED_VALUE', 'FORMULA')

        Returns:
            데이터 행들의 리스트
        """
        try:
            if range_name:
                # range_name이 명시적으로 제공된 경우
                if "!" not in range_name and sheet_name:
                    range_name = f"{sheet_name}!{range_name}"
            elif sheet_name:
                # sheet_name만 제공된 경우 전체 시트 읽기
                range_name = sheet_name
            else:
                # 둘 다 없으면 첫 번째 시트 전체 읽기
                range_name = None

            sheet = self.service.spreadsheets()  # type: ignore
            result = (
                sheet.values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueRenderOption=value_render_option,
                )
                .execute()
            )

            values = result.get("values", [])
            return values

        except HttpError as error:
            raise Exception(f"스프레드시트 데이터를 가져오는 중 오류 발생: {error}")

    def to_json(
        self,
        data: list[list[Any]],
        empty_cells_as_none: bool = True,
    ) -> list[dict[str, Any]]:
        """
        스프레드시트 데이터를 JSON 형태로 변환합니다.

        Args:
            data: 스프레드시트에서 가져온 데이터 (행들의 리스트)
            empty_cells_as_none: 빈 셀을 None으로 처리할지 여부

        Returns:
            헤더를 사용한 dict 리스트
        """
        if not data:
            return []

        # 첫 번째 행을 헤더로 사용
        headers = data[0]

        # 헤더 정리 (빈 문자열 제거 및 정규화)
        cleaned_headers = [
            str(h).strip() if h else f"column_{i + 1}" for i, h in enumerate(headers)
        ]

        # 데이터 행들 처리
        json_data = []
        for row in data[1:]:
            row_dict = {}
            for i, header in enumerate(cleaned_headers):
                value = row[i] if i < len(row) else None
                if empty_cells_as_none and (value == "" or value is None):
                    value = None
                row_dict[header] = value
            json_data.append(row_dict)

        return json_data

    def get_sheet_data_as_json(
        self,
        spreadsheet_id: str,
        range_name: str | None = None,
        sheet_name: str | None = None,
        empty_cells_as_none: bool = True,
        value_render_option: str = "FORMATTED_VALUE",
    ) -> list[dict[str, Any]]:
        """
        스프레드시트에서 데이터를 가져와 JSON 형태로 변환합니다.

        Args:
            spreadsheet_id: Google Sheets 스프레드시트 ID
            range_name: 읽을 범위 (예: 'Sheet1!A1:D10')
            sheet_name: 시트 이름
            empty_cells_as_none: 빈 셀을 None으로 처리할지 여부
            value_render_option: 값 렌더링 옵션

        Returns:
            JSON 형태의 데이터
        """
        data = self.get_sheet_data(
            spreadsheet_id=spreadsheet_id,
            range_name=range_name,
            sheet_name=sheet_name,
            value_render_option=value_render_option,
        )
        return self.to_json(
            data,
            empty_cells_as_none=empty_cells_as_none,
        )

    def save_to_json_file(
        self,
        data: list[dict[str, Any]] | list[list[Any]],
        output_path: str | Path,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> None:
        """
        JSON 데이터를 파일로 저장합니다.

        Args:
            data: 저장할 JSON 데이터
            output_path: 출력 파일 경로
            indent: JSON 들여쓰기 (None이면 한 줄로)
            ensure_ascii: ASCII만 사용할지 여부
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

    def export_sheet_to_json(
        self,
        spreadsheet_id: str,
        output_path: str | Path,
        range_name: str | None = None,
        sheet_name: str | None = None,
        empty_cells_as_none: bool = True,
        value_render_option: str = "FORMATTED_VALUE",
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> None:
        """
        스프레드시트 데이터를 가져와 JSON 파일로 저장합니다.

        Args:
            spreadsheet_id: Google Sheets 스프레드시트 ID
            output_path: 출력 JSON 파일 경로
            range_name: 읽을 범위
            sheet_name: 시트 이름
            empty_cells_as_none: 빈 셀을 None으로 처리할지 여부
            value_render_option: 값 렌더링 옵션
            indent: JSON 들여쓰기
            ensure_ascii: ASCII만 사용할지 여부
        """
        json_data = self.get_sheet_data_as_json(
            spreadsheet_id=spreadsheet_id,
            range_name=range_name,
            sheet_name=sheet_name,
            empty_cells_as_none=empty_cells_as_none,
            value_render_option=value_render_option,
        )
        self.save_to_json_file(
            json_data, output_path, indent=indent, ensure_ascii=ensure_ascii
        )


def main():
    """사용 예제"""
    import os

    from dotenv import load_dotenv

    from utils.env_utils import doublecheck_env

    load_dotenv()
    doublecheck_env(".env")

    # 환경 변수에서 설정 읽기
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if not credentials_path or not spreadsheet_id:
        print(
            "환경 변수를 설정하세요:\n"
            "  GOOGLE_CREDENTIALS_PATH: 서비스 계정 JSON 파일 경로\n"
            "  GOOGLE_SPREADSHEET_ID: 스프레드시트 ID\n"
            "\n사용 예제:\n"
            "  reader = GoogleSheetsReader(credentials_path='path/to/credentials.json')\n"
            "  json_data = reader.get_sheet_data_as_json(spreadsheet_id='your-spreadsheet-id')\n"
            "  print(json.dumps(json_data, indent=2, ensure_ascii=False))"
        )
        return

    # Google Sheets Reader 초기화
    reader = GoogleSheetsReader(credentials_path=credentials_path)

    # 데이터 가져오기 및 JSON 변환
    json_data = reader.get_sheet_data_as_json(
        spreadsheet_id=spreadsheet_id,
        sheet_name="202501",  # 또는 range_name='Sheet1!A1:D10'
    )

    # 결과 출력
    print(json.dumps(json_data, indent=2, ensure_ascii=False))

    # 파일로 저장
    reader.save_to_json_file(json_data, "output.json")


if __name__ == "__main__":
    main()
