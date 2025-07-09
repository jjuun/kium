"""
백테스팅 시스템 테스트
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

def create_sample_data():
    """
    샘플 데이터 생성
    """
    try:
        # 1년간의 샘플 데이터 생성
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        dates = pd.date_range(start_date, end_date, freq='D')
        
        # 주말 제외
        dates = dates[dates.weekday < 5]
        
        # 가격 데이터 생성 (랜덤 워크)
        np.random.seed(42)  # 재현성을 위한 시드 설정
        
        initial_price = 50000
        returns = np.random.normal(0.001, 0.02, len(dates))  # 일간 수익률
        prices = [initial_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1000))  # 최소 가격 1000원
        
        # OHLCV 데이터 생성
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # OHLC 생성 (간단한 방식)
            open_price = price * (1 + np.random.normal(0, 0.005))
            high_price = max(open_price, price) * (1 + abs(np.random.normal(0, 0.01)))
            low_price = min(open_price, price) * (1 - abs(np.random.normal(0, 0.01)))
            close_price = price
            volume = np.random.randint(1000000, 10000000)
            
            data.append({
                '시가': open_price,
                '고가': high_price,
                '저가': low_price,
                '종가': close_price,
                '거래량': volume
            })
        
        df = pd.DataFrame(data, index=dates)
        logger.info(f"샘플 데이터 생성 완료: {len(df)}개 데이터")
        
        return df
        
    except Exception as e:
        logger.error(f"샘플 데이터 생성 중 오류: {e}")
        return pd.DataFrame()

def test_basic_backtest():
    """
    기본 백테스트 테스트
    """
    try:
        logger.info("=== 기본 백테스트 테스트 시작 ===")
        
        # 샘플 데이터 생성
        data = create_sample_data()
        if data.empty:
            logger.error("샘플 데이터 생성 실패")
            return False
        
        # 백테스트 엔진 생성
        engine = BacktestEngine(initial_capital=10000000)
        
        # 백테스트 실행
        result = engine.run_backtest(data, "TEST_STOCK")
        
        # 결과 확인
        logger.info(f"총 수익률: {result.total_return:.2f}%")
        logger.info(f"연간 수익률: {result.annualized_return:.2f}%")
        logger.info(f"샤프 비율: {result.sharpe_ratio:.3f}")
        logger.info(f"최대 낙폭: {result.max_drawdown:.2f}%")
        logger.info(f"총 거래 횟수: {result.total_trades}")
        logger.info(f"승률: {result.win_rate:.1f}%")
        
        # 분석기 생성 및 요약 보고서
        analyzer = BacktestAnalyzer(result)
        summary = analyzer.generate_summary_report()
        
        logger.info("=== 백테스트 요약 ===")
        for category, metrics in summary.items():
            logger.info(f"\n{category}:")
            for metric, value in metrics.items():
                logger.info(f"  {metric}: {value}")
        
        logger.info("=== 기본 백테스트 테스트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"기본 백테스트 테스트 중 오류: {e}")
        return False

def test_backtest_analyzer():
    """
    백테스트 분석기 테스트
    """
    try:
        logger.info("=== 백테스트 분석기 테스트 시작 ===")
        
        # 샘플 데이터로 백테스트 실행
        data = create_sample_data()
        if data.empty:
            logger.error("샘플 데이터 생성 실패")
            return False
        
        engine = BacktestEngine(initial_capital=10000000)
        result = engine.run_backtest(data, "TEST_STOCK")
        
        # 분석기 생성
        analyzer = BacktestAnalyzer(result)
        
        # 요약 보고서 생성
        summary = analyzer.generate_summary_report()
        logger.info("요약 보고서 생성 완료")
        
        # 차트 생성 (저장만, 표시하지 않음)
        try:
            analyzer.plot_equity_curve("test_equity_curve.png")
            analyzer.plot_drawdown("test_drawdown.png")
            analyzer.plot_monthly_returns("test_monthly_returns.png")
            analyzer.plot_trade_analysis("test_trade_analysis.png")
            logger.info("차트 생성 완료")
        except Exception as e:
            logger.warning(f"차트 생성 중 오류 (matplotlib 관련): {e}")
        
        # 결과 내보내기
        analyzer.export_results("test_backtest_results.csv")
        logger.info("결과 내보내기 완료")
        
        logger.info("=== 백테스트 분석기 테스트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"백테스트 분석기 테스트 중 오류: {e}")
        return False

def test_strategy_optimizer():
    """
    전략 최적화 테스트
    """
    try:
        logger.info("=== 전략 최적화 테스트 시작 ===")
        
        # 샘플 데이터 생성
        data = create_sample_data()
        if data.empty:
            logger.error("샘플 데이터 생성 실패")
            return False
        
        # 최적화기 생성
        optimizer = StrategyOptimizer(data, "TEST_STOCK")
        
        # SMA 교차 전략 최적화 (간단한 파라미터로)
        logger.info("SMA 교차 전략 최적화 시작...")
        sma_results = optimizer.optimize_sma_crossover(
            short_periods=[3, 5, 8],
            long_periods=[15, 20, 25],
            stop_loss_range=[2.0, 3.0],
            take_profit_range=[5.0, 7.0]
        )
        
        if not sma_results.empty:
            logger.info(f"SMA 최적화 완료: {len(sma_results)}개 결과")
            logger.info("상위 3개 결과:")
            print(sma_results.head(3).to_string(index=False))
        
        # 리스크 파라미터 최적화
        logger.info("리스크 파라미터 최적화 시작...")
        risk_results = optimizer.optimize_risk_parameters(
            position_size_range=[0.1, 0.15, 0.2],
            commission_range=[0.0001, 0.00015],
            slippage_range=[0.00005, 0.0001]
        )
        
        if not risk_results.empty:
            logger.info(f"리스크 최적화 완료: {len(risk_results)}개 결과")
            logger.info("상위 3개 결과:")
            print(risk_results.head(3).to_string(index=False))
        
        logger.info("=== 전략 최적화 테스트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"전략 최적화 테스트 중 오류: {e}")
        return False

def test_backtest_runner():
    """
    백테스트 실행기 테스트
    """
    try:
        logger.info("=== 백테스트 실행기 테스트 시작 ===")
        
        # 실행기 생성
        runner = BacktestRunner()
        
        # 샘플 데이터 생성 (실제로는 데이터 수집기에서 가져와야 함)
        data = create_sample_data()
        if data.empty:
            logger.error("샘플 데이터 생성 실패")
            return False
        
        # 데이터를 임시로 저장하여 실행기에서 사용
        data.to_csv("temp_test_data.csv")
        
        # 단일 백테스트 실행 (실제로는 데이터 수집기를 통해)
        logger.info("단일 백테스트 실행 테스트...")
        
        # 실행기에서 데이터 수집 부분을 우회하여 테스트
        engine = BacktestEngine(initial_capital=10000000)
        result = engine.run_backtest(data, "TEST_STOCK")
        
        # 보고서 생성
        runner.generate_report(result, "TEST_STOCK", "test_reports")
        
        logger.info("=== 백테스트 실행기 테스트 완료 ===")
        return True
        
    except Exception as e:
        logger.error(f"백테스트 실행기 테스트 중 오류: {e}")
        return False

def run_all_tests():
    """
    모든 테스트 실행
    """
    logger.info("=== 백테스팅 시스템 전체 테스트 시작 ===")
    
    tests = [
        ("기본 백테스트", test_basic_backtest),
        ("백테스트 분석기", test_backtest_analyzer),
        ("전략 최적화", test_strategy_optimizer),
        ("백테스트 실행기", test_backtest_runner)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"테스트: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = test_func()
            results[test_name] = "성공" if success else "실패"
        except Exception as e:
            logger.error(f"{test_name} 테스트 중 예외 발생: {e}")
            results[test_name] = "예외"
    
    # 테스트 결과 요약
    logger.info(f"\n{'='*50}")
    logger.info("테스트 결과 요약")
    logger.info(f"{'='*50}")
    
    for test_name, result in results.items():
        logger.info(f"{test_name}: {result}")
    
    success_count = sum(1 for result in results.values() if result == "성공")
    total_count = len(results)
    
    logger.info(f"\n전체 테스트: {success_count}/{total_count} 성공")
    
    if success_count == total_count:
        logger.info("모든 테스트가 성공적으로 완료되었습니다!")
        return True
    else:
        logger.warning("일부 테스트가 실패했습니다.")
        return False

if __name__ == "__main__":
    # 테스트 실행
    success = run_all_tests()
    
    if success:
        print("\n✅ 백테스팅 시스템 테스트 성공!")
        sys.exit(0)
    else:
        print("\n❌ 백테스팅 시스템 테스트 실패!")
        sys.exit(1) 