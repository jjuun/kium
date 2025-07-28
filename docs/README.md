# A-ki: 주식자동매매프로그램

키움증권 API를 활용한 Python 기반 자동매매 시스템입니다.

## 📁 프로젝트 구조

```
A-ki/
├── src/                    # 메인 소스 코드
│   ├── api/               # API 관련 모듈
│   │   ├── __init__.py
│   │   └── kiwoom_api.py  # 키움증권 API 연동
│   ├── auto_trading/      # 자동매매 모듈
│   │   ├── __init__.py
│   │   ├── auto_trader.py      # 자동매매 실행기
│   │   ├── watchlist_manager.py # 감시종목 관리
│   │   ├── condition_manager.py # 매매조건 관리
│   │   └── signal_monitor.py    # 신호 모니터링
│   ├── backtesting/       # 백테스팅 모듈
│   │   ├── __init__.py
│   │   ├── backtest_engine.py   # 백테스트 엔진
│   │   ├── backtest_analyzer.py # 백테스트 분석기
│   │   ├── backtest_runner.py   # 백테스트 실행기
│   │   └── strategy_optimizer.py # 전략 최적화
│   ├── core/              # 핵심 기능 모듈
│   │   ├── __init__.py
│   │   ├── config.py      # 설정 관리
│   │   ├── container.py   # 의존성 주입 컨테이너
│   │   ├── data_collector.py  # 데이터 수집
│   │   ├── interfaces.py  # 인터페이스 정의
│   │   └── logger.py      # 로깅 시스템
│   ├── trading/           # 거래 관련 모듈
│   │   ├── __init__.py
│   │   ├── trading_strategy.py  # 매매 전략
│   │   ├── risk_manager.py      # 리스크 관리
│   │   ├── trading_executor.py  # 거래 실행
│   │   └── order_executor.py    # 주문 실행
│   └── web/               # 웹 관련 모듈
│       ├── __init__.py
│       └── web_dashboard.py     # 웹 대시보드
├── tests/                 # 테스트 파일들
│   ├── __init__.py
│   ├── conftest.py        # pytest 설정
│   ├── utils/
│   │   └── test_helpers.py # 테스트 헬퍼
│   ├── unit/              # 단위 테스트
│   │   ├── test_auto_trader.py
│   │   ├── test_data_collector.py
│   │   ├── test_risk_manager.py
│   │   └── test_trading_strategy.py
│   ├── integration/       # 통합 테스트
│   │   ├── test_api_integration.py
│   │   └── test_database_integration.py
│   ├── e2e/               # E2E 테스트
│   │   ├── test_full_trading_workflow.py
│   │   └── test_web_dashboard_workflow.py
│   └── fixtures/          # 테스트 데이터
├── config/                # 설정 파일들
│   ├── 64339425_appkey.txt
│   └── 64339425_secretkey.txt
├── logs/                  # 로그 파일들
│   ├── server.log
│   ├── trading.log
│   └── monitor.log
├── static/                # 정적 파일들
│   ├── css/
│   │   └── dashboard.css
│   ├── js/
│   │   └── dashboard.js
│   └── favicon.svg
├── templates/             # 템플릿 파일들
│   └── dashboard.html
├── docs/                  # 문서 파일들
│   ├── README.md
│   ├── CURRENT_STATUS.md  # 현재 상태 요약
│   ├── BACKTESTING.md
│   ├── MONITORING.md
│   ├── TESTING.md
│   └── REFACTORING_PROGRESS.md
├── examples/              # 예제 파일들
│   ├── backtest_example.py
│   ├── simple_backtest_demo.py
│   └── advanced_backtest_demo.py
├── main.py                # 메인 실행 파일 (트레이딩 서버)
├── monitor_server.py      # 서버 모니터링 시스템
├── view_logs.py           # 로그 뷰어
├── aki_server_control.py  # 통합 서버 컨트롤 시스템
├── aki_control.sh         # 통합 서버 컨트롤 쉘 스크립트
├── web_server_control.py  # 웹 서버 전용 시작 스크립트
├── web_server_stop.py     # 웹 서버 전용 종료 스크립트
├── web_start.sh           # 웹 서버 시작 쉘 스크립트
├── web_stop.sh            # 웹 서버 종료 쉘 스크립트
├── server.sh              # 레거시 서버 관리 스크립트
├── aki-monitor.service    # Systemd 서비스 파일
├── requirements.txt       # 의존성 패키지
├── requirements-dev.txt   # 개발 의존성 패키지
├── pytest.ini            # pytest 설정
└── auto_trading.db        # SQLite 데이터베이스
```

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 의존성 패키지 설치
pip install -r requirements.txt

# 개발 의존성 설치 (테스트, 린팅 등)
pip install -r requirements-dev.txt
```

### 2. API 키 설정

`config/` 폴더에 키움증권 API 키 파일을 설정하거나 환경변수로 설정:

```bash
export KIWOOM_APPKEY="your_appkey_here"
export KIWOOM_SECRETKEY="your_secretkey_here"
```

### 3. 서버 실행 및 관리

#### 🚀 통합 서버 컨트롤 시스템 (권장)
웹 서버와 트레이딩 서버를 모두 관리하는 통합 컨트롤 시스템입니다.

```bash
# 모든 서버 시작 (웹 서버 + 트레이딩 서버)
./aki_control.sh start

# 모든 서버 중지
./aki_control.sh stop

# 모든 서버 재시작
./aki_control.sh restart

# 서버 상태 확인
./aki_control.sh status

# 강제 중지 (필요한 경우)
./aki_control.sh stop --force

# 도움말 표시
./aki_control.sh help
```

#### 🔍 서버 모니터링 시스템
서버 상태를 실시간으로 모니터링하고 자동 재시작하는 시스템입니다.

```bash
# 기본 모니터링 시작 (30초 간격, 3회 재시도)
python3 monitor_server.py

# 커스텀 설정으로 모니터링 시작
python3 monitor_server.py --interval 60 --retries 5 --delay 15

# 로그 확인
python3 view_logs.py

# 실시간 로그 추적
python3 view_logs.py --file server --follow

# 로그에서 키워드 검색
python3 view_logs.py --search "error"
```

#### 🌐 웹 서버 전용 관리 (선택적)
웹 서버만 별도로 관리하고 싶은 경우:

```bash
# 웹 서버 시작
./web_start.sh

# 웹 서버 종료
./web_stop.sh

# Python 스크립트 직접 실행
python3 web_server_control.py
python3 web_server_stop.py
```

#### 📋 통합 서버 컨트롤 기능
- **웹 서버 + 트레이딩 서버 통합 관리**: 두 서버를 동시에 시작/중지/재시작
- **자동 프로세스 감지**: 실행 중인 A-ki 관련 프로세스 자동 발견
- **안전한 종료**: 기존 프로세스를 안전하게 종료 후 새 서버 시작
- **포트 충돌 해결**: 포트 8000 사용 중인 프로세스 자동 정리
- **PID 파일 관리**: 웹 서버와 트레이딩 서버 PID 자동 관리
- **실시간 로그 모니터링**: 두 서버의 출력을 실시간으로 확인
- **강제 종료 옵션**: 응답하지 않는 프로세스 강제 종료

#### 🔧 기존 서버 관리 (레거시)
```bash
# 서버 시작
./server.sh start

# 서버 재시작
./server.sh restart

# 서버 중지
./server.sh stop

# 서버 상태 확인
./server.sh status
```

#### 📝 수동 서버 관리 (고급 사용자)
```bash
# 서버 시작
PYTHONPATH=$(pwd) uvicorn src.web.web_dashboard:app --host 0.0.0.0 --port 8000 --reload

# 서버 재시작 (실행 중인 서버가 있다면 종료 후 재시작)
pkill -f "uvicorn.*web_dashboard"
PYTHONPATH=$(pwd) uvicorn src.web.web_dashboard:app --host 0.0.0.0 --port 8000 --reload
```

웹 대시보드는 `http://localhost:8000`에서 접속할 수 있습니다.

## 📊 웹 대시보드 기능

### 주요 기능:

#### 📈 계좌 및 포트폴리오
- **계좌 잔고**: 실시간 계좌 현금 및 총 자산
- **포트폴리오**: 전체 포트폴리오 요약 및 평가손익
- **보유종목**: 현재 보유 중인 종목 목록 및 실시간 가격
- **실현손익**: 실현된 손익 내역

#### 📊 거래 관리
- **주문 실행**: 종목 검색 및 매수/매도 주문
- **미체결 주문**: 미체결 주문 조회 및 취소
- **체결 내역**: 상세한 체결 내역 조회
- **주식 차트**: 종목별 차트 데이터 조회

#### 🤖 자동매매 시스템
- **감시종목 관리**: 자동매매 대상 종목 추가/삭제/활성화
- **매매조건 관리**: 가격, RSI, 이동평균 등 다양한 조건 설정
- **자동매매 제어**: 자동매매 시작/중지 및 상태 모니터링
- **신호 모니터링**: 매매 신호 생성, 실행, 성공률 추적

#### 🔄 실시간 업데이트
- **자동 새로고침**: 30초마다 자동 데이터 갱신
- **연결 상태**: 서버 연결 상태 실시간 모니터링
- **실시간 가격**: 보유종목 실시간 가격 업데이트

## 🧪 테스트 시스템

### 테스트 구조
A-ki는 체계적인 테스트 시스템을 구축했습니다:

- **단위 테스트**: 개별 함수/클래스 테스트 (54개 테스트, 100% 통과)
- **통합 테스트**: 컴포넌트 간 상호작용 테스트
- **E2E 테스트**: 전체 시스템 워크플로우 테스트

### 테스트 실행

```bash
# 전체 테스트 실행
pytest tests/ -v

# 단위 테스트만 실행
pytest tests/unit/ -v

# 통합 테스트만 실행
pytest tests/integration/ -v

# E2E 테스트만 실행
pytest tests/e2e/ -v

# 커버리지와 함께 실행
pytest tests/ --cov=src --cov-report=html

# 특정 테스트 실행
pytest tests/unit/test_auto_trader.py -v
```

### 테스트 커버리지
- **단위 테스트**: 100% 통과 (54개 테스트)
- **전체 커버리지**: 80% 이상 목표
- **핵심 모듈**: 90% 이상 커버리지

## 📈 백테스팅 시스템

### 주요 기능
- **백테스트 엔진**: 과거 데이터로 거래 시뮬레이션
- **결과 분석**: 수익률, 샤프 비율, 최대 낙폭 등 성과 지표
- **전략 최적화**: 파라미터 최적화를 통한 전략 개선
- **시각화**: 자본금 곡선, 낙폭 분석, 월별 수익률 히트맵

### 사용 예제

```python
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_analyzer import BacktestAnalyzer

# 백테스트 실행
engine = BacktestEngine(initial_capital=10000000)
result = engine.run_backtest(data, "A005930")

# 결과 분석
analyzer = BacktestAnalyzer(result)
summary = analyzer.generate_summary_report()

# 시각화
analyzer.plot_equity_curve()
analyzer.plot_drawdown()
```

## 🔧 설정

### 자동매매 설정
- **감시종목**: 자동매매 대상 종목 설정
- **매매조건**: 가격 조건, 기술적 지표 조건 설정
- **리스크 관리**: 일일 주문 한도, 쿨다운 시간 설정

### 거래 설정
- **주문 수량**: 기본 주문 수량 설정
- **손절/익절**: 자동 손절매/익절매 비율 설정
- **거래 시간**: 거래 가능 시간 설정

## 📈 자동매매 시스템

### 감시종목 관리
- 종목코드 기반 감시종목 추가/삭제
- 종목별 활성화/비활성화 설정
- 감시종목 통계 정보 제공
- 테스트 데이터와 실제 데이터 구분 관리

### 매매조건 관리
- **가격 조건**: 현재가 기준 매수/매도 조건
- **RSI 조건**: RSI 지표 기반 매매 조건
- **이동평균 조건**: 이동평균선 기반 매매 조건
- **조건 조합**: 여러 조건을 조합한 복합 조건

### 자동매매 실행
- **실시간 모니터링**: 감시종목 실시간 가격 모니터링
- **조건 평가**: 설정된 조건에 따른 매매 신호 생성
- **주문 실행**: 신호에 따른 자동 주문 실행
- **리스크 관리**: 일일 주문 한도, 쿨다운 시간 관리

### 신호 모니터링
- **신호 기록**: 모든 매매 신호 자동 기록
- **상태 추적**: 신호 상태 (대기 → 실행 → 성공/실패) 추적
- **성공률 분석**: 종목별, 조건별 성공률 분석
- **수익/손실 계산**: 실현된 수익/손실 자동 계산

## 🛡️ 리스크 관리

- **일일 주문 한도**: 하루 최대 주문 횟수 제한
- **쿨다운 시간**: 연속 주문 간 최소 대기 시간
- **손절매**: 설정된 손실률 도달 시 자동 매도
- **익절매**: 설정된 수익률 도달 시 자동 매도
- **포지션 크기 제한**: 최대 포지션 크기 제한

## 📝 로깅

- **서버 로그**: `logs/server.log` - 웹 서버 및 API 로그
- **거래 로그**: `logs/trading.log` - 거래 관련 로그
- **모니터링 로그**: `logs/monitor.log` - 서버 모니터링 로그
- **자동매매 로그**: 실시간 자동매매 활동 로그

## ⚠️ 주의사항

- 이 프로그램은 교육 및 연구 목적으로 제작되었습니다.
- 실제 거래에 사용하기 전에 충분한 테스트가 필요합니다.
- 투자 손실에 대한 책임은 사용자에게 있습니다.
- 키움증권 API 사용 시 해당 증권사의 이용약관을 준수해야 합니다.

## 🔄 업데이트 내역

### v1.6.0 (현재)
- **서버 모니터링 시스템**: 실시간 서버 상태 모니터링 및 자동 재시작
- **로그 뷰어**: 실시간 로그 확인 및 검색 기능
- **Systemd 서비스**: 시스템 부팅 시 자동 시작
- **테스트 시스템 완성**: 단위/통합/E2E 테스트 체계 구축
- **백테스팅 시스템**: 전략 성과 검증 및 최적화 도구

### v1.5.0
- **자동매매 시스템 완성**: 감시종목, 매매조건, 자동매매 실행, 신호 모니터링
- **웹 대시보드 개선**: 자동매매 제어 UI, 실시간 상태 모니터링
- **신호 모니터링**: 매매 신호 추적, 성공률 분석, 수익/손실 계산
- **데이터베이스 연동**: SQLite 기반 영구 데이터 저장
- **단위 테스트**: 모든 핵심 기능에 대한 테스트 케이스

### v1.4.0
- **매매조건 관리**: 다양한 매매 조건 설정 및 관리
- **자동매매 로직**: 조건 기반 자동 매매 실행
- **리스크 관리**: 일일 주문 한도, 쿨다운 시간 관리

### v1.3.0
- **감시종목 관리**: 자동매매 대상 종목 관리 시스템
- **웹 UI 개선**: 감시종목 관리 인터페이스

### v1.2.0
- **자동 새로고침**: 30초마다 자동 데이터 갱신
- **연결 상태 모니터링**: 서버 연결 상태 실시간 확인
- **UI/UX 개선**: 사용자 인터페이스 개선

### v1.1.0
- **웹 대시보드**: FastAPI 기반 웹 인터페이스
- **실시간 데이터**: 계좌, 포트폴리오, 주문 실시간 조회
- **주문 실행**: 웹에서 직접 매수/매도 주문

### v1.0.0
- **키움증권 API 연동**: 기본 API 연동 및 인증
- **계좌 조회**: 잔고, 보유종목, 체결내역 조회
- **기본 주문**: 매수/매도 주문 실행

## 🚀 다음 단계 (개발 예정)

### 1. 알림 시스템
- **이메일 알림**: 매매 신호, 주문 체결, 수익/손실 알림
- **슬랙 알림**: 실시간 매매 상황 슬랙 채널 연동
- **푸시 알림**: 모바일 푸시 알림 기능
- **알림 설정**: 사용자별 알림 조건 및 채널 설정

### 2. 포트폴리오 분석
- **종목별 수익률 분석**: 개별 종목 성과 분석
- **포트폴리오 리밸런싱**: 자동 포트폴리오 재조정
- **분산 투자**: 위험 분산을 위한 자동 종목 분산
- **성과 리포트**: 월간/분기별 포트폴리오 성과 리포트

### 3. 위험 관리 강화
- **손절매 자동화**: 설정된 손실률 도달 시 자동 매도
- **익절매 자동화**: 설정된 수익률 도달 시 자동 매도
- **동적 리스크 조정**: 시장 상황에 따른 리스크 자동 조정
- **VaR 분석**: Value at Risk 기반 위험 측정

### 4. 차트 분석
- **기술적 지표 시각화**: RSI, MACD, 이동평균 등 지표 차트
- **실시간 차트**: 실시간 가격 차트 및 지표 표시
- **차트 패턴 인식**: 자동 패턴 인식 및 신호 생성
- **멀티 타임프레임**: 다양한 시간대 차트 분석

### 5. 코드 품질 개선
- **코드 포맷팅**: Black, Flake8, MyPy 적용
- **의존성 주입**: 인터페이스 기반 느슨한 결합
- **이벤트 기반 아키텍처**: 확장 가능한 이벤트 시스템
- **CI/CD 파이프라인**: 자동화된 테스트 및 배포

## 📚 추가 문서

- **[현재 상태 요약](docs/CURRENT_STATUS.md)**: 프로젝트 전체 진행 상황 및 성과
- **[백테스팅 가이드](docs/BACKTESTING.md)**: 백테스팅 시스템 상세 사용법
- **[모니터링 가이드](docs/MONITORING.md)**: 서버 모니터링 시스템 사용법
- **[테스트 가이드](docs/TESTING.md)**: 테스트 시스템 및 작성 가이드
- **[리팩토링 진행 상황](docs/REFACTORING_PROGRESS.md)**: 리팩토링 작업 진행 상황

## 📞 지원 및 문의

프로젝트 관련 문의사항이나 버그 리포트는 이슈를 통해 제출해주세요.

---

**A-ki 자동매매 시스템** - 더 스마트한 투자를 위한 선택 🚀
