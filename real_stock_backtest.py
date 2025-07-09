#!/usr/bin/env python3
"""
실제 주식 데이터를 사용한 백테스팅 시스템
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
from src.core.data_collector import DataCollector

class SimpleTradingStrategy:
    """간단한 매매 전략"""
    
    def __init__(self):
        self.name = "Simple Moving Average Strategy"
        
    def generate_signal(self, data):
        """매매 신호 생성"""
        if len(data) < 20:
            return None
            
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        # 이동평균 계산
        sma_5 = data['종가'].rolling(window=5).mean().iloc[-1]
        sma_20 = data['종가'].rolling(window=20).mean().iloc[-1]
        sma_5_prev = data['종가'].rolling(window=5).mean().iloc[-2]
        sma_20_prev = data['종가'].rolling(window=20).mean().iloc[-2]
        
        signal = {
            'timestamp': datetime.now(),
            'price': current['종가'],
            'action': 'HOLD',
            'confidence': 0.0,
            'reason': []
        }
        
        # 매수 신호: 단기 이동평균이 장기 이동평균을 상향 돌파
        if (sma_5_prev <= sma_20_prev and sma_5 > sma_20):
            signal['action'] = 'BUY'
            signal['confidence'] = 0.7
            signal['reason'].append('SMA 상향 돌파')
            
        # 매도 신호: 단기 이동평균이 장기 이동평균을 하향 돌파
        elif (sma_5_prev >= sma_20_prev and sma_5 < sma_20):
            signal['action'] = 'SELL'
            signal['confidence'] = 0.7
            signal['reason'].append('SMA 하향 돌파')
        
        return signal

def run_backtest_with_real_data():
    """실제 주식 데이터로 백테스트 실행"""
    print("🚀 실제 주식 데이터 백테스트 시작")
    print("="*60)
    
    try:
        # 데이터 수집기 초기화
        data_collector = DataCollector()
        
        # 삼성전자 데이터 수집 (1년치)
        print("📊 삼성전자 데이터 수집 중...")
        data = data_collector.get_historical_data("005930", 365)
        
        if data is None or data.empty:
            print("❌ 데이터 수집 실패")
            return
        
        print(f"데이터 수집 완료: {len(data)}개 데이터")
        print(f"기간: {data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')}")
        print(f"가격 범위: {data['종가'].min():,.0f}원 ~ {data['종가'].max():,.0f}원")
        
        # 기술적 지표 계산
        print("\n📈 기술적 지표 계산 중...")
        data_with_indicators = data_collector.calculate_technical_indicators(data)
        
        # 백테스트 엔진 초기화
        print("\n⚙️ 백테스트 엔진 초기화...")
        engine = BacktestEngine(initial_capital=10000000)  # 1천만원
        
        # 간단한 전략 설정
        simple_strategy = SimpleTradingStrategy()
        engine.strategy = simple_strategy
        
        # 백테스트 실행
        print("🔄 백테스트 실행 중...")
        result = engine.run_backtest(data_with_indicators, "005930")
        
        # 결과 출력
        print("\n📈 백테스트 결과:")
        print(f"총 수익률: {result.total_return:.2f}%")
        print(f"연간 수익률: {result.annualized_return:.2f}%")
        print(f"샤프 비율: {result.sharpe_ratio:.3f}")
        print(f"최대 낙폭: {result.max_drawdown:.2f}%")
        print(f"총 거래 횟수: {result.total_trades}")
        print(f"승률: {result.win_rate:.1f}%")
        print(f"수익 팩터: {result.profit_factor:.3f}")
        
        # 상세 분석
        print("\n📊 상세 분석:")
        analyzer = BacktestAnalyzer(result)
        summary = analyzer.generate_summary_report()
        
        for category, metrics in summary.items():
            print(f"\n{category}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")
        
        # 거래 내역 요약
        if result.trades:
            print(f"\n💼 거래 내역 요약:")
            buy_trades = [t for t in result.trades if t.action == 'BUY']
            sell_trades = [t for t in result.trades if t.action == 'SELL']
            print(f"  매수 거래: {len(buy_trades)}회")
            print(f"  매도 거래: {len(sell_trades)}회")
            
            if sell_trades:
                avg_sell_price = sum(t.price for t in sell_trades) / len(sell_trades)
                print(f"  평균 매도가: {avg_sell_price:,.0f}원")
        
        print("\n✅ 실제 주식 데이터 백테스트 완료!")
        
    except Exception as e:
        print(f"\n❌ 백테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    print("🎯 실제 주식 데이터 백테스팅 시스템")
    print("="*60)
    
    # 실제 주식 데이터로 백테스트 실행
    run_backtest_with_real_data()
    
    print("\n🎯 다음 단계 제안:")
    print("1. 더 복잡한 전략 구현 (RSI, MACD 등)")
    print("2. 포트폴리오 백테스트 (여러 종목 동시 투자)")
    print("3. 전략 파라미터 최적화")
    print("4. 리스크 관리 시스템 강화")
    print("5. 실시간 거래 시스템과 연동")

if __name__ == "__main__":
    main() 