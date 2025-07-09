"""
백테스팅 시스템 사용 예제
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.logger import logger
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_analyzer import BacktestAnalyzer
from src.backtesting.strategy_optimizer import StrategyOptimizer
from src.backtesting.backtest_runner import BacktestRunner

def create_realistic_sample_data():
    """
    현실적인 샘플 데이터 생성 (삼성전자 패턴 기반)
    """
    try:
        # 1년간의 데이터 생성
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        dates = pd.date_range(start_date, end_date, freq='D')
        
        # 주말 제외
        dates = dates[dates.weekday < 5]
        
        # 삼성전자와 유사한 패턴으로 가격 생성
        np.random.seed(42)
        
        initial_price = 70000  # 삼성전자 초기 가격
        prices = [initial_price]
        
        # 트렌드 + 노이즈로 가격 생성
        trend = np.linspace(0, 0.1, len(dates))  # 상승 트렌드
        noise = np.random.normal(0, 0.015, len(dates))  # 일간 변동성
        
        for i in range(1, len(dates)):
            # 트렌드 + 노이즈 + 주기적 변동
            daily_return = trend[i] + noise[i] + 0.001 * np.sin(i * 2 * np.pi / 252)
            new_price = prices[-1] * (1 + daily_return)
            prices.append(max(new_price, 50000))  # 최소 가격
        
        # OHLCV 데이터 생성
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # OHLC 생성 (현실적인 방식)
            volatility = 0.02  # 일간 변동성
            
            open_price = price * (1 + np.random.normal(0, volatility * 0.3))
            high_price = max(open_price, price) * (1 + abs(np.random.normal(0, volatility * 0.5)))
            low_price = min(open_price, price) * (1 - abs(np.random.normal(0, volatility * 0.5)))
            close_price = price
            volume = np.random.randint(5000000, 20000000)  # 거래량
            
            data.append({
                '시가': open_price,
                '고가': high_price,
                '저가': low_price,
                '종가': close_price,
                '거래량': volume
            })
        
        df = pd.DataFrame(data, index=dates)
        logger.info(f"현실적인 샘플 데이터 생성 완료: {len(df)}개 데이터")
        logger.info(f"가격 범위: {df['종가'].min():.0f} ~ {df['종가'].max():.0f}")
        
        return df
        
    except Exception as e:
        logger.error(f"현실적인 샘플 데이터 생성 중 오류: {e}")
        return pd.DataFrame()

def example_basic_backtest():
    """
    기본 백테스트 예제
    """
    print("\n" + "="*60)
    print("기본 백테스트 예제")
    print("="*60)
    
    try:
        # 데이터 생성
        data = create_realistic_sample_data()
        if data.empty:
            print("❌ 데이터 생성 실패")
            return
        
        # 백테스트 엔진 생성
        engine = BacktestEngine(initial_capital=10000000)  # 1천만원
        
        # 백테스트 실행
        print("백테스트 실행 중...")
        result = engine.run_backtest(data, "SAMPLE_STOCK")
        
        # 결과 출력
        print(f"\n📊 백테스트 결과:")
        print(f"총 수익률: {result.total_return:.2f}%")
        print(f"연간 수익률: {result.annualized_return:.2f}%")
        print(f"샤프 비율: {result.sharpe_ratio:.3f}")
        print(f"최대 낙폭: {result.max_drawdown:.2f}%")
        print(f"총 거래 횟수: {result.total_trades}")
        print(f"승률: {result.win_rate:.1f}%")
        print(f"수익 팩터: {result.profit_factor:.3f}")
        
        # 분석기로 상세 분석
        analyzer = BacktestAnalyzer(result)
        summary = analyzer.generate_summary_report()
        
        print(f"\n📈 상세 분석:")
        for category, metrics in summary.items():
            print(f"\n{category}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")
        
        print("\n✅ 기본 백테스트 완료!")
        
    except Exception as e:
        print(f"❌ 기본 백테스트 실패: {e}")

def example_strategy_optimization():
    """
    전략 최적화 예제
    """
    print("\n" + "="*60)
    print("전략 최적화 예제")
    print("="*60)
    
    try:
        # 데이터 생성
        data = create_realistic_sample_data()
        if data.empty:
            print("❌ 데이터 생성 실패")
            return
        
        # 최적화기 생성
        optimizer = StrategyOptimizer(data, "SAMPLE_STOCK")
        
        # SMA 교차 전략 최적화
        print("SMA 교차 전략 최적화 중...")
        sma_results = optimizer.optimize_sma_crossover(
            short_periods=[3, 5, 8, 10],
            long_periods=[15, 20, 25, 30],
            stop_loss_range=[2.0, 3.0, 5.0],
            take_profit_range=[5.0, 7.0, 10.0]
        )
        
        if not sma_results.empty:
            print(f"\n🏆 SMA 최적화 결과 (상위 5개):")
            print(sma_results.head().to_string(index=False))
            
            # 최적 파라미터
            best_params = sma_results.iloc[0]
            print(f"\n🎯 최적 파라미터:")
            print(f"단기 기간: {best_params['short_period']}")
            print(f"장기 기간: {best_params['long_period']}")
            print(f"손절 비율: {best_params['stop_loss']}%")
            print(f"익절 비율: {best_params['take_profit']}%")
            print(f"예상 수익률: {best_params['total_return']:.2f}%")
        
        # 리스크 파라미터 최적화
        print(f"\n🔧 리스크 파라미터 최적화 중...")
        risk_results = optimizer.optimize_risk_parameters(
            position_size_range=[0.05, 0.1, 0.15, 0.2],
            commission_range=[0.0001, 0.00015, 0.0002],
            slippage_range=[0.00005, 0.0001, 0.00015]
        )
        
        if not risk_results.empty:
            print(f"\n🏆 리스크 최적화 결과 (상위 5개):")
            print(risk_results.head().to_string(index=False))
        
        print("\n✅ 전략 최적화 완료!")
        
    except Exception as e:
        print(f"❌ 전략 최적화 실패: {e}")

def example_comparison_backtest():
    """
    비교 백테스트 예제
    """
    print("\n" + "="*60)
    print("비교 백테스트 예제")
    print("="*60)
    
    try:
        # 여러 종목의 데이터 생성 (다른 패턴)
        symbols = ["STOCK_A", "STOCK_B", "STOCK_C"]
        results = {}
        
        for i, symbol in enumerate(symbols):
            print(f"\n📈 {symbol} 백테스트 중...")
            
            # 각 종목별로 다른 패턴 생성
            np.random.seed(42 + i)  # 다른 시드로 다른 패턴
            
            data = create_realistic_sample_data()
            if data.empty:
                continue
            
            # 백테스트 실행
            engine = BacktestEngine(initial_capital=10000000)
            result = engine.run_backtest(data, symbol)
            results[symbol] = result
        
        # 결과 비교
        if results:
            print(f"\n📊 종목별 성과 비교:")
            print(f"{'종목':<10} {'수익률':<10} {'샤프비율':<10} {'최대낙폭':<10} {'거래횟수':<10}")
            print("-" * 60)
            
            for symbol, result in results.items():
                print(f"{symbol:<10} {result.total_return:>8.2f}% {result.sharpe_ratio:>8.3f} "
                      f"{result.max_drawdown:>8.2f}% {result.total_trades:>8d}")
            
            # 최고 성과 종목
            best_symbol = max(results.keys(), key=lambda x: results[x].total_return)
            best_result = results[best_symbol]
            
            print(f"\n🏆 최고 성과 종목: {best_symbol}")
            print(f"총 수익률: {best_result.total_return:.2f}%")
            print(f"샤프 비율: {best_result.sharpe_ratio:.3f}")
        
        print("\n✅ 비교 백테스트 완료!")
        
    except Exception as e:
        print(f"❌ 비교 백테스트 실패: {e}")

def example_risk_analysis():
    """
    리스크 분석 예제
    """
    print("\n" + "="*60)
    print("리스크 분석 예제")
    print("="*60)
    
    try:
        # 데이터 생성
        data = create_realistic_sample_data()
        if data.empty:
            print("❌ 데이터 생성 실패")
            return
        
        # 백테스트 실행
        engine = BacktestEngine(initial_capital=10000000)
        result = engine.run_backtest(data, "RISK_ANALYSIS")
        
        # 분석기 생성
        analyzer = BacktestAnalyzer(result)
        
        # 리스크 지표 계산
        summary = analyzer.generate_summary_report()
        risk_metrics = summary.get('리스크 지표', {})
        
        print(f"\n⚠️ 리스크 분석 결과:")
        for metric, value in risk_metrics.items():
            print(f"  {metric}: {value}")
        
        # 수익률 분포 분석
        if not result.equity_curve.empty:
            returns = result.equity_curve['total_equity'].pct_change().dropna()
            
            print(f"\n📊 수익률 분포:")
            print(f"평균 수익률: {returns.mean() * 100:.4f}%")
            print(f"수익률 표준편차: {returns.std() * 100:.4f}%")
            print(f"최대 수익률: {returns.max() * 100:.4f}%")
            print(f"최소 수익률: {returns.min() * 100:.4f}%")
            print(f"수익률 왜도: {returns.skew():.4f}")
            print(f"수익률 첨도: {returns.kurtosis():.4f}")
        
        print("\n✅ 리스크 분석 완료!")
        
    except Exception as e:
        print(f"❌ 리스크 분석 실패: {e}")

def main():
    """
    메인 실행 함수
    """
    print("🚀 백테스팅 시스템 예제 실행")
    print("="*60)
    
    examples = [
        ("기본 백테스트", example_basic_backtest),
        ("전략 최적화", example_strategy_optimization),
        ("비교 백테스트", example_comparison_backtest),
        ("리스크 분석", example_risk_analysis)
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n{i}. {name}")
    
    print(f"\n0. 모든 예제 실행")
    
    try:
        choice = input(f"\n실행할 예제를 선택하세요 (0-{len(examples)}): ").strip()
        
        if choice == "0":
            # 모든 예제 실행
            for name, func in examples:
                func()
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            # 선택된 예제 실행
            name, func = examples[int(choice) - 1]
            func()
        else:
            print("❌ 잘못된 선택입니다.")
            return
        
        print(f"\n🎉 백테스팅 시스템 예제 실행 완료!")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예제 실행 중 오류: {e}")

if __name__ == "__main__":
    main() 