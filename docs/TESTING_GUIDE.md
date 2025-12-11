# 테스트 코드 작성 가이드

## 📚 테스트 코드 구조

### 1. Fixtures (테스트 데이터 준비)

```python
@pytest.fixture
def sample_csv_data():
    """재사용 가능한 테스트 데이터"""
    return pd.DataFrame({...})

@pytest.fixture
def temp_csv_file(sample_csv_data):
    """임시 파일 생성 (테스트 후 자동 삭제)"""
    with tempfile.NamedTemporaryFile(...) as f:
        yield f.name
    Path(f.name).unlink()
```

**장점:**
- 테스트 간 데이터 일관성 유지
- 코드 중복 제거
- 자동 정리 (파일 삭제 등)

---

### 2. 단위 테스트 (Unit Tests)

각 함수를 독립적으로 테스트합니다.

```python
class TestCalculateSLAGrade:
    def test_grade_s(self):
        """S 등급 테스트"""
        assert calculate_sla_grade(95.0) == "S"
    
    def test_edge_cases(self):
        """경계값 테스트"""
        assert calculate_sla_grade(95.0) == "S"  # 정확히 95%
```

**테스트 케이스:**
- ✅ 정상 케이스 (Happy Path)
- ✅ 경계값 (Boundary Values)
- ✅ 예외 케이스 (Error Cases)
- ✅ 엣지 케이스 (Edge Cases)

---

### 3. 통합 테스트 (Integration Tests)

여러 함수가 함께 작동하는지 테스트합니다.

```python
class TestGraphFlow:
    def test_graph_execution_success(self, temp_csv_file):
        """전체 플로우 테스트"""
        result = run_agent(csv_path=temp_csv_file)
        assert result["success"] is True
```

---

### 4. 테스트 실행 방법

#### 기본 실행
```bash
# 전체 테스트 실행
pytest tests/test_agent_spike.py -v

# 특정 테스트 클래스만 실행
pytest tests/test_agent_spike.py::TestCalculateSLAGrade -v

# 특정 테스트만 실행
pytest tests/test_agent_spike.py::TestCalculateSLAGrade::test_grade_s -v

# 키워드로 필터링
pytest tests/test_agent_spike.py -k "grade" -v
```

#### 커버리지 포함
```bash
# 커버리지 리포트 생성
pytest tests/test_agent_spike.py --cov=src.agent_spike --cov-report=html

# HTML 리포트 확인
open htmlcov/index.html
```

#### 실패한 테스트만 재실행
```bash
pytest tests/test_agent_spike.py --lf  # last failed
```

---

## 🎯 테스트 작성 원칙

### 1. AAA 패턴 (Arrange-Act-Assert)

```python
def test_example():
    # Arrange: 테스트 데이터 준비
    state = initial_state.copy()
    state["csv_path"] = "test.csv"
    
    # Act: 테스트할 동작 실행
    result = load_data(state)
    
    # Assert: 결과 검증
    assert result["sla_result"] == "S"
```

### 2. 테스트는 독립적이어야 함

- 각 테스트는 다른 테스트에 의존하지 않아야 합니다
- 테스트 순서가 바뀌어도 결과가 같아야 합니다
- Fixture를 사용하여 격리된 환경 제공

### 3. 명확한 테스트 이름

```python
# ❌ 나쁜 예
def test1():
    ...

# ✅ 좋은 예
def test_load_data_success():
    """정상적인 데이터 로드 테스트"""
    ...

def test_load_data_file_not_found():
    """파일이 없을 때 테스트"""
    ...
```

### 4. 하나의 테스트는 하나의 것을 검증

```python
# ❌ 나쁜 예
def test_everything():
    assert load_data(...)
    assert calculate_sla(...)
    assert generate_report(...)

# ✅ 좋은 예
def test_load_data():
    assert load_data(...)

def test_calculate_sla():
    assert calculate_sla(...)
```

---

## 🔍 주요 테스트 시나리오

### 데이터 로드 테스트
- ✅ 정상적인 CSV 파일 로드
- ✅ 파일이 없는 경우
- ✅ 빈 파일
- ✅ 필수 컬럼 누락
- ✅ 0으로 나누기 (인입콜 = 0)
- ✅ 음수 값
- ✅ 응답콜 > 인입콜 (비정상 데이터)

### 계산 로직 테스트
- ✅ 정확한 등급 계산 (각 등급 경계값)
- ✅ 반올림 정확도
- ✅ 매우 큰 숫자 처리
- ✅ 소수점 처리

### 리포트 생성 테스트
- ✅ 정상적인 리포트 생성
- ✅ 시뮬레이션 정보 포함
- ✅ 에러 상태 리포트
- ✅ 데이터 포맷팅 (천 단위 구분자 등)

### Graph 플로우 테스트
- ✅ 전체 플로우 성공
- ✅ 중간 단계 실패 처리
- ✅ 다양한 목표 등급
- ✅ Graph 구조 검증

---

## 📊 테스트 커버리지 목표

- **라인 커버리지**: 80% 이상
- **브랜치 커버리지**: 75% 이상
- **함수 커버리지**: 90% 이상

---

## 🛠️ 디버깅 팁

### 실패한 테스트 디버깅

```python
# pytest의 -s 옵션으로 print 출력 확인
pytest tests/test_agent_spike.py -s

# 특정 테스트에서 중단점 설정
import pdb; pdb.set_trace()

# 상세한 출력
pytest tests/test_agent_spike.py -vv
```

### 테스트 데이터 확인

```python
# Fixture 데이터 출력
def test_debug(sample_csv_data):
    print(sample_csv_data)
    print(sample_csv_data.describe())
```

---

## 📝 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
