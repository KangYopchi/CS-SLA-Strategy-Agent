# Google Sheets API 설정 가이드

이 가이드는 Google Sheets API를 사용하기 위한 인증 설정 방법을 설명합니다.

## 1. Google Cloud Console에서 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 상단의 프로젝트 선택 드롭다운 클릭
3. "새 프로젝트" 클릭
4. 프로젝트 이름 입력 (예: "my-sheets-project")
5. "만들기" 클릭

## 2. Google Sheets API 활성화

1. Google Cloud Console에서 생성한 프로젝트 선택
2. 왼쪽 메뉴에서 "API 및 서비스" > "라이브러리" 클릭
3. 검색창에 "Google Sheets API" 입력
4. "Google Sheets API" 선택
5. "사용 설정" 버튼 클릭

## 3. 서비스 계정 생성

### 3-1. 사용자 인증 정보 페이지로 이동

1. 왼쪽 메뉴에서 **"API 및 서비스"** (API & Services) 클릭
2. 하위 메뉴에서 **"사용자 인증 정보"** (Credentials) 클릭

### 3-2. 서비스 계정 생성 시작

1. 페이지 상단의 **"+ 사용자 인증 정보 만들기"** (Create credentials) 버튼 클릭
2. 드롭다운 메뉴가 나타납니다. 다음 옵션들이 보일 수 있습니다:
   - API 키 (API key)
   - OAuth 클라이언트 ID (OAuth client ID)
   - **서비스 계정 (Service account)** ← **이것을 선택하세요!**
   - 사용자 인증 정보 만들기 (Create credentials) - 이 경우 하위 메뉴가 더 나타날 수 있습니다

3. **"서비스 계정"** 또는 **"Service account"** 클릭

### 3-3. 서비스 계정 정보 입력

서비스 계정 생성 페이지가 나타납니다:

1. **서비스 계정 이름** (Service account name) 입력
   - 예: `sheets-reader` 또는 `my-sheets-service`
   - 이 이름은 나중에 식별하기 위한 것입니다

2. **서비스 계정 ID** (Service account ID)
   - 자동으로 생성됩니다 (서비스 계정 이름 기반)
   - 필요시 수정 가능합니다

3. **설명** (Description) - 선택사항
   - 예: "Google Sheets 데이터 읽기용 서비스 계정"

4. **"만들기 및 계속"** (Create and continue) 또는 **"만들기"** (Create) 버튼 클릭

### 3-4. 역할 선택 (선택사항)

역할 선택 화면이 나타날 수 있습니다:

- **옵션 1**: 역할을 선택하지 않고 건너뛰기
  - "역할 없이 계속" (Continue without role) 또는 "건너뛰기" (Skip) 클릭
  
- **옵션 2**: 역할 선택 (선택사항)
  - "역할 선택" (Select a role) 드롭다운에서 "편집자" (Editor) 선택
  - 또는 "역할 없이 계속" 클릭

- **"계속"** (Continue) 버튼 클릭

### 3-5. 사용자 액세스 권한 (선택사항)

사용자 액세스 권한 부여 화면이 나타날 수 있습니다:

- 이 단계는 **건너뛰어도 됩니다**
- "완료" (Done) 또는 "건너뛰기" (Skip) 클릭

### 3-6. 완료

서비스 계정이 생성되었습니다! 

**다음 단계**: 이제 생성된 서비스 계정에 키(JSON 파일)를 추가해야 합니다. 아래 4번 섹션으로 진행하세요.

## 4. 서비스 계정 키(JSON 파일) 다운로드

### 방법 1: 사용자 인증 정보 페이지에서 직접

1. "사용자 인증 정보" 페이지에서 방금 생성한 **서비스 계정**을 찾습니다
   - 서비스 계정 이름 옆에 이메일 주소가 표시됩니다 (예: `sheets-reader@프로젝트명.iam.gserviceaccount.com`)
2. 서비스 계정 이메일을 **클릭**합니다

### 방법 2: 서비스 계정 목록에서

1. 왼쪽 메뉴에서 **"IAM 및 관리자"** (IAM & Admin) > **"서비스 계정"** (Service accounts) 클릭
2. 생성한 서비스 계정을 찾아서 **클릭**합니다

### 키 생성 및 다운로드

서비스 계정 상세 페이지로 이동한 후:

1. 상단의 **"키"** (Keys) 탭 클릭
2. **"키 추가"** (Add key) 버튼 클릭
3. **"새 키 만들기"** (Create new key) 선택
4. 키 유형 선택 팝업이 나타납니다:
   - **"JSON"** 선택 (기본값일 수 있음)
   - **"만들기"** (Create) 버튼 클릭
5. **JSON 파일이 자동으로 다운로드됩니다** ⬇️
   - 브라우저의 다운로드 폴더를 확인하세요
   - 파일 이름은 보통 `프로젝트명-랜덤문자열.json` 형식입니다

**이 파일이 바로 `credentials.json` 파일입니다!**

## 5. 다운로드된 JSON 파일 위치

다운로드된 파일은 보통 다음과 같은 위치에 있습니다:

- **macOS**: `~/Downloads/프로젝트명-xxxxx.json`
- **Windows**: `C:\Users\사용자명\Downloads\프로젝트명-xxxxx.json`
- **Linux**: `~/Downloads/프로젝트명-xxxxx.json`

파일 이름은 보통 다음과 같은 형식입니다:
- `my-sheets-project-xxxxx-xxxxx.json` (프로젝트명-랜덤문자열.json)

## 6. JSON 파일을 프로젝트에 복사

다운로드한 JSON 파일을 프로젝트 디렉토리로 복사하거나 이동합니다:

```bash
# 예시: 다운로드 폴더에서 프로젝트로 복사
cp ~/Downloads/my-sheets-project-*.json /Users/kangyopchi/Firenodes/Projects/cs-agent-project/credentials.json

# 또는 원하는 이름으로 변경
mv ~/Downloads/my-sheets-project-*.json credentials.json
```

## 7. 스프레드시트에 서비스 계정 공유

**중요**: 서비스 계정 이메일을 스프레드시트에 공유해야 데이터를 읽을 수 있습니다!

1. 다운로드한 JSON 파일을 열어서 `client_email` 필드를 확인합니다
   ```json
   {
     "type": "service_account",
     "project_id": "...",
     "private_key_id": "...",
     "private_key": "...",
     "client_email": "sheets-reader@my-sheets-project.iam.gserviceaccount.com",  ← 이 이메일
     ...
   }
   ```

2. 읽고 싶은 Google 스프레드시트를 엽니다
3. 오른쪽 상단의 "공유" 버튼 클릭
4. 서비스 계정 이메일 주소를 입력 (위에서 확인한 `client_email`)
5. 권한은 "뷰어"로 설정 (읽기만 필요하므로)
6. "전송" 클릭

## 8. 스프레드시트 ID 확인

스프레드시트 URL에서 ID를 확인할 수 있습니다:

```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit#gid=0
                                    ↑ 이 부분이 스프레드시트 ID
```

예시:
- URL: `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit`
- 스프레드시트 ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`

## 9. 환경 변수 설정 (선택사항)

`.env` 파일을 프로젝트 루트에 생성하고 다음을 추가합니다:

```env
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_SPREADSHEET_ID=your-spreadsheet-id-here
```

## 10. 보안 주의사항

⚠️ **중요**: `credentials.json` 파일은 절대 공개 저장소에 커밋하지 마세요!

`.gitignore` 파일에 다음을 추가하세요:

```
credentials.json
*.json
!package.json  # 필요한 경우 예외 처리
```

또는 더 구체적으로:

```
credentials.json
*-credentials.json
*-key.json
```

## 사용 예제

설정이 완료되면 다음과 같이 사용할 수 있습니다:

```python
from src.google_sheets_reader import GoogleSheetsReader

# credentials.json 파일 경로 지정
reader = GoogleSheetsReader(credentials_path="credentials.json")

# 스프레드시트 데이터 가져오기
json_data = reader.get_sheet_data_as_json(
    spreadsheet_id="your-spreadsheet-id",
    sheet_name="Sheet1"
)

print(json_data)
```

## 문제 해결

### "Create credentials" 클릭 후 서비스 계정 옵션이 보이지 않는 경우

**해결 방법 1**: 직접 서비스 계정 페이지로 이동
1. 왼쪽 메뉴에서 **"IAM 및 관리자"** (IAM & Admin) 클릭
2. **"서비스 계정"** (Service accounts) 클릭
3. 상단의 **"+ 서비스 계정 만들기"** (Create service account) 버튼 클릭
4. 위의 3-3 단계부터 진행하세요

**해결 방법 2**: URL로 직접 접근
- `https://console.cloud.google.com/iam-admin/serviceaccounts?project=YOUR_PROJECT_ID`
- YOUR_PROJECT_ID를 실제 프로젝트 ID로 변경하세요

### "Permission denied" 오류
- 서비스 계정 이메일을 스프레드시트에 공유했는지 확인하세요
- 공유 권한이 "뷰어" 이상인지 확인하세요
- 서비스 계정 이메일 주소를 정확히 입력했는지 확인하세요

### "API not enabled" 오류
- Google Sheets API가 활성화되었는지 확인하세요
- 올바른 프로젝트를 선택했는지 확인하세요
- API 활성화 후 몇 분 정도 기다려보세요

### "File not found" 오류
- `credentials_path`가 올바른지 확인하세요
- 파일 경로가 절대 경로인지 상대 경로인지 확인하세요
- 파일 이름에 공백이나 특수문자가 있는지 확인하세요

### 서비스 계정을 찾을 수 없는 경우
- 프로젝트가 올바르게 선택되었는지 확인하세요
- 서비스 계정 목록 페이지에서 필터를 확인하세요
- 서비스 계정이 실제로 생성되었는지 확인하세요
