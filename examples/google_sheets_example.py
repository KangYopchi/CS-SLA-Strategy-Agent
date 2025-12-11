"""
Google Sheets 데이터를 JSON으로 변환하는 사용 예제
"""

import json
import os

# 프로젝트 루트에서 src 모듈 import
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.google_sheets_reader import GoogleSheetsReader

load_dotenv()


def example_basic_usage():
    """기본 사용 예제"""
    # 서비스 계정 JSON 파일 경로
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if not spreadsheet_id:
        print("GOOGLE_SPREADSHEET_ID 환경 변수를 설정하세요.")
        return

    # Google Sheets Reader 초기화
    reader = GoogleSheetsReader(credentials_path=credentials_path)

    # 방법 1: 전체 시트 읽기 (첫 번째 행을 헤더로 사용)
    json_data = reader.get_sheet_data_as_json(
        spreadsheet_id=spreadsheet_id,
        sheet_name="Sheet1",
    )

    print("=== 전체 시트 데이터 (헤더 포함) ===")
    print(json.dumps(json_data, indent=2, ensure_ascii=False))
    print(f"\n총 {len(json_data)}개의 행이 있습니다.\n")

    # 방법 2: 특정 범위 읽기
    range_data = reader.get_sheet_data_as_json(
        spreadsheet_id=spreadsheet_id,
        range_name="Sheet1!A1:C5",  # A1부터 C5까지
    )

    print("=== 특정 범위 데이터 ===")
    print(json.dumps(range_data, indent=2, ensure_ascii=False))
    print()

    # 방법 3: JSON 파일로 저장
    output_path = Path("data") / "google_sheets_output.json"
    reader.export_sheet_to_json(
        spreadsheet_id=spreadsheet_id,
        output_path=output_path,
        sheet_name="Sheet1",
    )
    print(f"데이터가 {output_path}에 저장되었습니다.")


def example_custom_range():
    """커스텀 범위 읽기 예제"""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if not spreadsheet_id:
        print("GOOGLE_SPREADSHEET_ID 환경 변수를 설정하세요.")
        return

    reader = GoogleSheetsReader(credentials_path=credentials_path)

    # 특정 시트의 특정 범위만 읽기
    data = reader.get_sheet_data_as_json(
        spreadsheet_id=spreadsheet_id,
        range_name="Sheet1!B2:D10",  # B2부터 D10까지
    )

    print("=== 커스텀 범위 데이터 ===")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def example_multiple_sheets():
    """여러 시트 읽기 예제"""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if not spreadsheet_id:
        print("GOOGLE_SPREADSHEET_ID 환경 변수를 설정하세요.")
        return

    reader = GoogleSheetsReader(credentials_path=credentials_path)

    # 여러 시트 읽기
    sheets = ["Sheet1", "Sheet2", "Sheet3"]

    all_data = {}
    for sheet_name in sheets:
        try:
            data = reader.get_sheet_data_as_json(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
            )
            all_data[sheet_name] = data
            print(f"{sheet_name}: {len(data)}개 행")
        except Exception as e:
            print(f"{sheet_name} 읽기 실패: {e}")

    # 모든 시트 데이터를 하나의 JSON 파일로 저장
    output_path = Path("data") / "all_sheets.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"\n모든 시트 데이터가 {output_path}에 저장되었습니다.")


if __name__ == "__main__":
    print("=" * 60)
    print("Google Sheets to JSON 변환 예제")
    print("=" * 60)
    print()

    # 기본 사용 예제
    example_basic_usage()

    print("\n" + "=" * 60 + "\n")

    # 커스텀 범위 예제 (주석 해제하여 사용)
    # example_custom_range()

    # 여러 시트 읽기 예제 (주석 해제하여 사용)
    # example_multiple_sheets()
