# A-ki 테스트 가이드

## 📋 목차

1. [테스트 전략](#테스트-전략)
2. [테스트 구조](#테스트-구조)
3. [테스트 실행](#테스트-실행)
4. [테스트 커버리지](#테스트-커버리지)
5. [CI/CD 파이프라인](#cicd-파이프라인)
6. [테스트 작성 가이드](#테스트-작성-가이드)
7. [문제 해결](#문제-해결)

## 🎯 테스트 전략

### 테스트 피라미드

A-ki 프로젝트는 테스트 피라미드 원칙을 따릅니다:

```
    ┌─────────────┐
    │   E2E 테스트 │ ← 전체 시스템 통합 테스트
    └─────────────┘
         │
    ┌─────────────┐
    │ 통합 테스트  │ ← 컴포넌트 간 상호작용 테스트
    └─────────────┘
         │
    ┌─────────────┐
    │  단위 테스트 │ ← 개별 함수/클래스 테스트
    └─────────────┘
```

### 테스트 유형

#### 1. 단위 테스트 (Unit Tests)
- **목적**: 개별 함수, 클래스, 메서드의 동작 검증
- **위치**: `tests/unit/`
- **특징**: 
  - 빠른 실행 (1초 이내)
  - 외부 의존성 모킹
  - 격리된 테스트 환경

#### 2. 통합 테스트 (Integration Tests)
- **목적**: 컴포넌트 간 상호작용 및 API 엔드포인트 검증
- **위치**: `tests/integration/`
- **특징**:
  - 실제 데이터베이스 사용
  - API 엔드포인트 테스트
  - 컴포넌트 간 통합 검증

#### 3. E2E 테스트 (End-to-End Tests)
- **목적**: 전체 시스템 워크플로우 검증
- **위치**: `tests/e2e/`
- **특징**:
  - 실제 사용자 시나리오 시뮬레이션
  - 웹 인터페이스 테스트
  - 성능 및 부하 테스트

## 📁 테스트 구조

```
tests/
├── conftest.py                 # pytest 설정 및 공통 fixtures
├── utils/
│   └── test_helpers.py         # 테스트 헬퍼 함수들
├── unit/                       # 단위 테스트
│   ├── test_auto_trader.py
│   ├── test_data_collector.py
│   ├── test_risk_manager.py
│   └── test_trading_strategy.py
├── integration/                # 통합 테스트
│   ├── test_api_integration.py
│   └── test_database_integration.py
├── e2e/                        # E2E 테스트
│   ├── test_full_trading_workflow.py
│   └── test_web_dashboard_workflow.py
└── fixtures/                   # 테스트 데이터
    └── sample_data/
```

## 🚀 테스트 실행

### 1. 전체 테스트 실행

```bash
# 모든 테스트 실행
./scripts/run_tests.sh all

# 또는 직접 실행
pytest tests/ -v
```

### 2. 특정 테스트 유형 실행

```bash
# 단위 테스트만 실행
pytest tests/unit/ -v

# 통합 테스트만 실행
pytest tests/integration/ -v

# E2E 테스트만 실행
pytest tests/e2e/ -v
```

### 3. 마커를 사용한 테스트 실행

```bash
# 단위 테스트
pytest -m unit -v

# 통합 테스트
pytest -m integration -v

# E2E 테스트
pytest -m e2e -v

# 느린 테스트 제외
pytest -m "not slow" -v

# API 테스트만
pytest -m api -v

# 데이터베이스 테스트만
pytest -m database -v
```

### 4. 특정 파일 또는 함수 테스트

```bash
# 특정 파일 테스트
pytest tests/unit/test_auto_trader.py -v

# 특정 함수 테스트
pytest tests/unit/test_auto_trader.py::TestAutoTrader::test_auto_trader_initialization -v

# 패턴 매칭
pytest -k "initialization" -v
```

### 5. 커버리지와 함께 실행

```bash
# 커버리지 리포트 생성
pytest tests/ --cov=src --cov-report=html --cov-report=term

# 커버리지 임계값 설정
pytest tests/ --cov=src --cov-fail-under=80
```

## 📊 테스트 커버리지

### 커버리지 목표

- **전체 커버리지**: 80% 이상
- **핵심 모듈**: 90% 이상
- **API 엔드포인트**: 95% 이상

### 커버리지 확인

```bash
# HTML 리포트 생성
pytest tests/ --cov=src --cov-report=html

# 브라우저에서 확인
open htmlcov/index.html
```

### 커버리지 리포트 해석

- **Lines**: 코드 라인 커버리지
- **Functions**: 함수 호출 커버리지
- **Branches**: 조건문 분기 커버리지
- **Missing**: 커버되지 않은 코드

## 🔄 CI/CD 파이프라인

### GitHub Actions 워크플로우

`.github/workflows/test.yml`에서 다음 작업들이 자동 실행됩니다:

1. **테스트 작업**
   - Python 3.9-3.12 호환성 테스트
   - 코드 스타일 검사 (Black, Flake8)
   - 타입 검사 (MyPy)
   - 단위/통합/E2E 테스트
   - 커버리지 리포트 생성

2. **보안 검사**
   - Bandit (보안 취약점 검사)
   - Safety (의존성 보안 검사)

3. **성능 테스트**
   - 느린 테스트 실행
   - 성능 메트릭 수집

4. **빌드 및 배포**
   - 패키지 빌드
   - 배포 준비

### 로컬 CI/CD 실행

```bash
# 코드 스타일 검사
black --check src/ tests/
flake8 src/ tests/

# 타입 검사
mypy src/

# 보안 검사
bandit -r src/
safety check
```

## ✍️ 테스트 작성 가이드

### 1. 테스트 파일 명명 규칙

- 파일명: `test_*.py`
- 클래스명: `Test*`
- 함수명: `test_*`

### 2. 테스트 구조 (AAA 패턴)

```python
def test_function_name(self):
    """테스트 설명"""
    # Arrange (준비)
    input_data = "test"
    expected = "expected_result"
    
    # Act (실행)
    result = function_to_test(input_data)
    
    # Assert (검증)
    assert result == expected
```

### 3. Fixture 사용

```python
@pytest.fixture
def sample_data():
    """샘플 데이터 fixture"""
    return {"key": "value"}

def test_with_fixture(self, sample_data):
    """fixture를 사용한 테스트"""
    assert sample_data["key"] == "value"
```

### 4. 모킹 (Mocking)

```python
@patch('module.function_to_mock')
def test_with_mock(self, mock_function):
    """모킹을 사용한 테스트"""
    mock_function.return_value = "mocked_result"
    result = function_under_test()
    assert result == "mocked_result"
```

### 5. 비동기 테스트

```python
@pytest.mark.asyncio
async def test_async_function(self):
    """비동기 함수 테스트"""
    result = await async_function()
    assert result is not None
```

### 6. 데이터베이스 테스트

```python
def test_database_operation(self, temp_db_path):
    """데이터베이스 테스트"""
    auto_trader = AutoTrader(db_path=temp_db_path)
    # 테스트 로직...
```

## 🛠️ 문제 해결

### 일반적인 문제들

#### 1. ImportError: No module named 'src'

```bash
# 프로젝트 루트에서 실행
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

#### 2. 데이터베이스 연결 오류

```bash
# 임시 데이터베이스 사용
pytest tests/ --db-path=:memory:
```

#### 3. 의존성 문제

```bash
# 개발 의존성 재설치
pip install -r requirements-dev.txt --force-reinstall
```

#### 4. 테스트 타임아웃

```bash
# 타임아웃 증가
pytest tests/ --timeout=300
```

### 디버깅 팁

1. **상세한 출력**
   ```bash
   pytest tests/ -v -s --tb=long
   ```

2. **특정 테스트 디버깅**
   ```bash
   pytest tests/ -x --pdb
   ```

3. **커버리지 상세 분석**
   ```bash
   pytest tests/ --cov=src --cov-report=term-missing
   ```

### 성능 최적화

1. **병렬 실행**
   ```bash
   pytest tests/ -n auto
   ```

2. **캐시 사용**
   ```bash
   pytest tests/ --cache-clear
   ```

3. **느린 테스트 분리**
   ```bash
   pytest tests/ -m "not slow"
   ```

## 📈 테스트 메트릭

### 주요 지표

- **테스트 실행 시간**: < 5분 (전체)
- **단위 테스트**: < 30초
- **통합 테스트**: < 2분
- **E2E 테스트**: < 3분

### 품질 게이트

- **테스트 통과율**: 100%
- **코드 커버리지**: 80% 이상
- **보안 취약점**: 0개
- **성능 회귀**: 없음

## 🔗 관련 문서

- [pytest 공식 문서](https://docs.pytest.org/)
- [FastAPI 테스트 가이드](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python 테스트 모범 사례](https://realpython.com/python-testing/)

## 📞 지원

테스트 관련 문제가 있으면 다음을 확인하세요:

1. 이 문서의 문제 해결 섹션
2. GitHub Issues
3. 프로젝트 Wiki 