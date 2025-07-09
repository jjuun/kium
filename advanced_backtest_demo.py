#!/usr/bin/env python3
"""
고급 백테스팅 데모 - 여러 전략과 실용적인 조건들
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
from src.backtesting.strategy_optimizer import StrategyOptimizer

def create_realistic_sample_data():
    """실제 주식과 유사한 샘플 데이터 생성"""
    # 2년간의 데이터 생성
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2023, 12, 31)
    dates = pd.date_range(start_date, end_date, freq='D')
    
    # 주말 제외
    dates = dates[dates.weekday < 5]
    
    # 삼성전자와 유사한 가격 패턴 생성
    np.random.seed(42)
    
    initial_price = 70000  # 삼성전자 초기 가격
    prices = [initial_price]
    
    # 트렌드와 변동성 추가
    trend = 0.0001  # 약간의 상승 트렌드
    volatility = 0.02
    
    for i in range(1, len(dates)):
        # 기본 수익률
        base_return = trend + np.random.normal(0, volatility)
        
        # 계절성 추가 (월별 패턴)
        month = dates[i].month
        seasonal_factor = 0.001 * np.sin(2 * np.pi * month / 12)
        
        # 급등락 이벤트 (5% 확률)
        if np.random.random() < 0.05:
            base_return += np.random.normal(0, 0.05)
        
        # 가격 계산
        new_price = prices[-1] * (1 + base_return + seasonal_factor)
        prices.append(max(new_price, 1000))  # 최소 가격 보장
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, close_price) in enumerate(zip(dates, prices)):
        # 일일 변동성
        daily_volatility = 0.015
        
        # 시가 (전일 종가 기준)
        open_price = close_price * (1 + np.random.normal(0, daily_volatility * 0.5))
        
        # 고가/저가
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, daily_volatility * 0.3)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, daily_volatility * 0.3)))
        
        # 거래량 (가격 변동과 연관)
        price_change = abs(close_price - open_price) / open_price
        base_volume = np.random.randint(5000000, 20000000)
        volume = int(base_volume * (1 + price_change * 10))
        
        data.append({
            '시가': open_price,
            '고가': high_price,
            '저가': low_price,
            '종가': close_price,
            '거래량': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def create_simple_strategy():
    """간단한 매매 전략 클래스"""
    class SimpleStrategy:
        def __init__(self):
            self.name = "Simple Moving Average Crossover"
            
        def generate_signal(self, data):
            """매매 신호 생성"""
            if len(data) < 20:
                return None
                
            current = data.iloc[-1]
            previous = data.iloc[-2]
            
            # 단순 이동평균 계산
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
    
    return SimpleStrategy()

def run_multiple_strategies():
    """여러 전략으로 백테스트 실행"""
    print("🔄 여러 전략으로 백테스트 실행...")
    
    # 데이터 생성
    data = create_realistic_sample_data()
    
    # 전략들 정의
    strategies = {
        'SMA_Crossover': create_simple_strategy(),
        'Buy_and_Hold': None,  # 단순 매수 후 보유
        'Random': None  # 랜덤 매매
    }
    
    results = {}
    
    for strategy_name, strategy in strategies.items():
        print(f"\n📊 {strategy_name} 전략 실행 중...")
        
        # 백테스트 엔진 생성
        engine = BacktestEngine(initial_capital=10000000)
        
        # 전략 설정
        if strategy:
            engine.strategy = strategy
        
        # 백테스트 실행
        try:
            result = engine.run_backtest(data, "DEMO_STOCK")
            results[strategy_name] = result
            
            print(f"  총 수익률: {result.total_return:.2f}%")
            print(f"  연간 수익률: {result.annualized_return:.2f}%")
            print(f"  샤프 비율: {result.sharpe_ratio:.3f}")
            print(f"  최대 낙폭: {result.max_drawdown:.2f}%")
            print(f"  총 거래 횟수: {result.total_trades}")
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    
    return results

def optimize_strategy_parameters():
    """전략 파라미터 최적화"""
    print("\n🔧 전략 파라미터 최적화...")
    
    # 데이터 생성
    data = create_realistic_sample_data()
    
    # 최적화할 파라미터
    param_ranges = {
        'short_period': [3, 5, 7, 10],
        'long_period': [15, 20, 25, 30],
        'rsi_oversold': [20, 25, 30],
        'rsi_overbought': [70, 75, 80]
    }
    
    # 최적화 실행
    optimizer = StrategyOptimizer()
    best_params, best_result = optimizer.optimize_parameters(
        data, param_ranges, metric='sharpe_ratio'
    )
    
    print(f"최적 파라미터: {best_params}")
    print(f"최적 샤프 비율: {best_result:.3f}")
    
    return best_params, best_result

def main():
    """메인 함수"""
    print("🚀 고급 백테스팅 시스템 데모 시작")
    print("="*60)
    
    try:
        # 1. 기본 백테스트
        print("📊 기본 백테스트 실행...")
        data = create_realistic_sample_data()
        print(f"데이터 생성 완료: {len(data)}개 데이터")
        print(f"가격 범위: {data['종가'].min():,.0f}원 ~ {data['종가'].max():,.0f}원")
        
        engine = BacktestEngine(initial_capital=10000000)
        result = engine.run_backtest(data, "DEMO_STOCK")
        
        print(f"\n📈 기본 백테스트 결과:")
        print(f"총 수익률: {result.total_return:.2f}%")
        print(f"연간 수익률: {result.annualized_return:.2f}%")
        print(f"샤프 비율: {result.sharpe_ratio:.3f}")
        print(f"최대 낙폭: {result.max_drawdown:.2f}%")
        print(f"총 거래 횟수: {result.total_trades}")
        
        # 2. 여러 전략 비교
        print("\n" + "="*60)
        strategy_results = run_multiple_strategies()
        
        # 3. 전략 최적화
        print("\n" + "="*60)
        best_params, best_sharpe = optimize_strategy_parameters()
        
        # 4. 최적화된 파라미터로 재실행
        print("\n📊 최적화된 파라미터로 재실행...")
        # 여기서 최적화된 파라미터를 적용하여 재실행할 수 있습니다
        
        print("\n✅ 고급 백테스팅 시스템 데모 완료!")
        
        # 5. 다음 단계 제안
        print("\n🎯 다음 단계 제안:")
        print("1. 실제 주식 데이터로 백테스트 실행")
        print("2. 더 복잡한 전략 구현 (머신러닝 기반)")
        print("3. 포트폴리오 백테스트 (여러 종목)")
        print("4. 실시간 거래 시스템과 연동")
        print("5. 리스크 관리 시스템 강화")
        
    except Exception as e:
        print(f"\n❌ 데모 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 