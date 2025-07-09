#!/usr/bin/env python3
"""
간단한 백테스트 데모
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.logger import logger
from src.backtesting.backtest_engine import BacktestEngine, BacktestResult
from src.backtesting.backtest_analyzer import BacktestAnalyzer

def create_sample_data():
    """샘플 데이터 생성"""
    # 1년간의 데이터 생성
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    dates = pd.date_range(start_date, end_date, freq='D')
    
    # 주말 제외
    dates = dates[dates.weekday < 5]
    
    # 가격 데이터 생성 (랜덤 워크)
    np.random.seed(42)
    
    initial_price = 50000
    returns = np.random.normal(0.001, 0.02, len(dates))
    prices = [initial_price]
    
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(max(new_price, 1000))
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
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
    return df

def main():
    """메인 함수"""
    print("🚀 백테스팅 시스템 데모 시작")
    print("="*50)
    
    try:
        # 1. 샘플 데이터 생성
        print("📊 샘플 데이터 생성 중...")
        data = create_sample_data()
        print(f"데이터 생성 완료: {len(data)}개 데이터")
        
        # 2. 백테스트 엔진 생성
        print("\n⚙️ 백테스트 엔진 초기화...")
        engine = BacktestEngine(initial_capital=10000000)  # 1천만원
        
        # 3. 백테스트 실행
        print("🔄 백테스트 실행 중...")
        result = engine.run_backtest(data, "DEMO_STOCK")
        
        # 4. 결과 출력
        print("\n📈 백테스트 결과:")
        print(f"총 수익률: {result.total_return:.2f}%")
        print(f"연간 수익률: {result.annualized_return:.2f}%")
        print(f"샤프 비율: {result.sharpe_ratio:.3f}")
        print(f"최대 낙폭: {result.max_drawdown:.2f}%")
        print(f"총 거래 횟수: {result.total_trades}")
        print(f"승률: {result.win_rate:.1f}%")
        print(f"수익 팩터: {result.profit_factor:.3f}")
        
        # 5. 상세 분석
        print("\n📊 상세 분석:")
        analyzer = BacktestAnalyzer(result)
        summary = analyzer.generate_summary_report()
        
        for category, metrics in summary.items():
            print(f"\n{category}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")
        
        # 6. 거래 내역 요약
        if result.trades:
            print(f"\n💼 거래 내역 요약:")
            buy_trades = [t for t in result.trades if t.action == 'BUY']
            sell_trades = [t for t in result.trades if t.action == 'SELL']
            print(f"  매수 거래: {len(buy_trades)}회")
            print(f"  매도 거래: {len(sell_trades)}회")
            
            if sell_trades:
                avg_sell_price = sum(t.price for t in sell_trades) / len(sell_trades)
                print(f"  평균 매도가: {avg_sell_price:,.0f}원")
        
        print("\n✅ 백테스팅 시스템 데모 완료!")
        
    except Exception as e:
        print(f"\n❌ 데모 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 