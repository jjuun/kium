# 백테스팅 시스템 가이드

## 📋 개요

A-ki 백테스팅 시스템은 주식 매매 전략의 성과를 과거 데이터로 검증하고 최적화할 수 있는 강력한 도구입니다.

## 🏗️ 시스템 구조

```
src/backtesting/
├── __init__.py
├── backtest_engine.py      # 백테스트 엔진 (핵심)
├── backtest_analyzer.py    # 결과 분석 및 시각화
├── strategy_optimizer.py   # 전략 최적화
└── backtest_runner.py      # 실행 관리
```

## 🚀 주요 기능

### 1. 백테스트 엔진 (BacktestEngine)
- **실시간 시뮬레이션**: 과거 데이터로 거래 시뮬레이션
- **리스크 관리**: 손절/익절, 포지션 크기 제한
- **수수료 모델링**: 거래 수수료 및 슬리피지 반영
- **다양한 전략 지원**: SMA, RSI, MACD 등

### 2. 결과 분석기 (BacktestAnalyzer)
- **성과 지표**: 수익률, 샤프 비율, 최대 낙폭 등
- **시각화**: 자본금 곡선, 낙폭 분석, 월별 수익률
- **리스크 분석**: VaR, CVaR, 변동성 분석
- **보고서 생성**: JSON, CSV 형태로 결과 내보내기

### 3. 전략 최적화기 (StrategyOptimizer)
- **그리드 서치**: 파라미터 조합 최적화
- **병렬 처리**: 다중 CPU 활용으로 빠른 최적화
- **다양한 최적화**: SMA, 리스크 파라미터 등
- **결과 시각화**: 최적화 과정 및 결과 분석

## 📊 성과 지표

### 기본 지표
- **총 수익률**: 전체 기간 수익률
- **연간 수익률**: 연율화된 수익률
- **샤프 비율**: 위험 대비 수익률
- **최대 낙폭**: 최대 손실 구간

### 거래 통계
- **총 거래 횟수**: 전체 거래 수
- **승률**: 수익 거래 비율
- **수익 팩터**: 총 수익 / 총 손실
- **평균 거래 수익률**: 거래당 평균 수익률

### 리스크 지표
- **변동성**: 수익률의 표준편차
- **VaR (95%)**: 95% 신뢰구간 손실 한도
- **CVaR (95%)**: VaR 초과 손실의 평균
- **칼마 비율**: 수익률 / 최대 낙폭

## 🛠️ 사용 방법

### 1. 기본 백테스트

```python
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_analyzer import BacktestAnalyzer

# 데이터 준비 (OHLCV DataFrame)
data = get_historical_data("A005930", "2023-01-01", "2023-12-31")

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

### 2. 전략 최적화

```python
from src.backtesting.strategy_optimizer import StrategyOptimizer

# 최적화기 생성
optimizer = StrategyOptimizer(data, "A005930")

# SMA 교차 전략 최적화
results = optimizer.optimize_sma_crossover(
    short_periods=[3, 5, 8, 10],
    long_periods=[15, 20, 25, 30],
    stop_loss_range=[2.0, 3.0, 5.0],
    take_profit_range=[5.0, 7.0, 10.0]
)

# 최적 파라미터 확인
best_params = results.iloc[0]
print(f"최적 파라미터: {best_params}")
```

### 3. 비교 백테스트

```python
from src.backtesting.backtest_runner import BacktestRunner

# 실행기 생성
runner = BacktestRunner()

# 다중 종목 비교
symbols = ["A005930", "A000660", "A035420"]
results = runner.run_comparison_backtest(
    symbols, "2023-01-01", "2023-12-31"
)

# 결과 비교
for symbol, result in results.items():
    print(f"{symbol}: {result.total_return:.2f}%")
```

## 📈 시각화 기능

### 1. 자본금 곡선
- 총 자본금, 현금, 포지션 가치 변화
- 수익률 곡선

### 2. 낙폭 분석
- 누적 낙폭 시각화
- 최대 낙폭 구간 표시

### 3. 월별 수익률 히트맵
- 월별/연도별 수익률 분포
- 색상으로 수익/손실 구분

### 4. 거래 분석
- 거래 시점별 가격
- 거래량/금액 분포
- 거래 시간대 분석

## ⚙️ 설정 옵션

### 백테스트 설정
```python
# 초기 자본금
initial_capital = 10000000

# 수수료 설정
commission_rate = 0.00015  # 0.015%
slippage_rate = 0.0001     # 0.01%

# 리스크 관리
stop_loss_percent = 2.0    # 2% 손절
take_profit_percent = 5.0  # 5% 익절
max_position_size = 1000000  # 최대 포지션 크기
```

### 전략 파라미터
```python
# SMA 교차 전략
short_period = 5    # 단기 이동평균
long_period = 20    # 장기 이동평균

# RSI 전략
rsi_period = 14     # RSI 계산 기간
rsi_oversold = 30   # 과매도 기준
rsi_overbought = 70 # 과매수 기준
```

## 🔧 고급 기능

### 1. 커스텀 전략
```python
class CustomStrategy:
    def generate_signal(self, data):
        # 커스텀 신호 생성 로직
        return signal
```

### 2. 포트폴리오 백테스트
```python
# 다중 종목 동시 거래
portfolio = ["A005930", "A000660", "A035420"]
results = run_portfolio_backtest(portfolio, data)
```

### 3. 실시간 백테스트
```python
# 실시간 데이터로 백테스트
real_time_engine = RealTimeBacktestEngine()
result = real_time_engine.run_live_backtest()
```

## 📊 결과 해석

### 좋은 전략의 특징
- **높은 샤프 비율**: 1.0 이상
- **낮은 최대 낙폭**: 20% 이하
- **높은 승률**: 50% 이상
- **안정적인 수익률**: 연간 10% 이상

### 주의사항
- **과적합 위험**: 과거 데이터에만 최적화
- **거래 비용**: 수수료, 슬리피지 고려
- **시장 변화**: 과거 패턴이 미래에도 유효하지 않을 수 있음
- **리스크 관리**: 적절한 포지션 크기와 손절 설정

## 🚀 실행 예제

### 명령줄 실행
```bash
# 기본 백테스트
python -m src.backtesting.backtest_runner --symbol A005930 --start_date 2023-01-01 --end_date 2023-12-31

# 최적화 실행
python -m src.backtesting.backtest_runner --symbol A005930 --mode optimization --optimization_type sma_crossover

# 보고서 생성
python -m src.backtesting.backtest_runner --symbol A005930 --generate_report
```

### Python 스크립트
```python
# examples/backtest_example.py 실행
python examples/backtest_example.py
```

## 📁 출력 파일

### 백테스트 결과
- `backtest_results/`: 최적화 결과 CSV
- `reports/`: 상세 보고서 JSON
- `reports/charts/`: 시각화 차트 PNG
- `reports/data/`: 백테스트 데이터 CSV

### 로그 파일
- `logs/backtest.log`: 백테스트 실행 로그
- `logs/optimization.log`: 최적화 과정 로그

## 🔍 문제 해결

### 일반적인 문제
1. **데이터 부족**: 충분한 과거 데이터 확보
2. **메모리 부족**: 대용량 데이터 처리 시 청크 단위 처리
3. **수렴 문제**: 최적화 파라미터 범위 조정
4. **과적합**: 교차 검증 및 아웃오브샘플 테스트

### 성능 최적화
1. **병렬 처리**: 다중 CPU 활용
2. **데이터 캐싱**: 중복 계산 방지
3. **벡터화**: NumPy/Pandas 활용
4. **메모리 관리**: 불필요한 데이터 제거

## 📚 추가 자료

- [전략 개발 가이드](STRATEGY_DEVELOPMENT.md)
- [리스크 관리 가이드](RISK_MANAGEMENT.md)
- [성과 분석 가이드](PERFORMANCE_ANALYSIS.md)
- [API 문서](API_REFERENCE.md) 