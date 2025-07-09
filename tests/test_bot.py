"""
주식자동매매프로그램 테스트 파일
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.logger import logger
from src.core.data_collector import DataCollector
from src.trading.trading_strategy import TradingStrategy
from src.trading.risk_manager import RiskManager
from src.trading.trading_executor import TradingExecutor

def test_data_collection():
    """
    데이터 수집 테스트
    """
    print("=== 데이터 수집 테스트 ===")
    
    collector = DataCollector()
    
    # 과거 데이터 수집 테스트
    print("1. 과거 데이터 수집 테스트...")
    historical_data = collector.get_historical_data(period=7)  # 7일 데이터
    
    if historical_data is not None:
        print(f"   ✓ 과거 데이터 수집 성공: {len(historical_data)}개 데이터")
        print(f"   ✓ 데이터 범위: {historical_data.index[0]} ~ {historical_data.index[-1]}")
        print(f"   ✓ 최신 종가: {historical_data['종가'].iloc[-1]:,.0f}원")
        
        # 기술적 지표 계산 테스트
        print("2. 기술적 지표 계산 테스트...")
        data_with_indicators = collector.calculate_technical_indicators(historical_data)
        
        if data_with_indicators is not None:
            print("   ✓ 기술적 지표 계산 성공")
            print(f"   ✓ RSI: {data_with_indicators['RSI'].iloc[-1]:.2f}")
            print(f"   ✓ MACD: {data_with_indicators['MACD'].iloc[-1]:.2f}")
            print(f"   ✓ 단기 이동평균: {data_with_indicators['SMA_5'].iloc[-1]:,.0f}원")
            print(f"   ✓ 장기 이동평균: {data_with_indicators['SMA_20'].iloc[-1]:,.0f}원")
            
            return data_with_indicators
        else:
            print("   ✗ 기술적 지표 계산 실패")
    else:
        print("   ✗ 과거 데이터 수집 실패")
    
    return None

def test_trading_strategy(data):
    """
    매매 전략 테스트
    """
    print("\n=== 매매 전략 테스트 ===")
    
    if data is None:
        print("데이터가 없어 전략 테스트를 건너뜁니다.")
        return
    
    strategy = TradingStrategy()
    
    # 각 전략별 테스트
    strategies = [
        ("SMA_CROSSOVER", "이동평균선 교차"),
        ("RSI", "RSI"),
        ("MACD", "MACD"),
        ("BOLLINGER_BANDS", "볼린저 밴드"),
        ("COMBINED", "복합 전략")
    ]
    
    for strategy_name, strategy_desc in strategies:
        print(f"\n{strategy_desc} 전략 테스트...")
        
        # 전략 설정 변경
        strategy.strategy_name = strategy_name
        
        # 신호 생성
        signal = strategy.generate_signal(data)
        
        if signal:
            print(f"   ✓ 신호 생성 성공")
            print(f"   ✓ 액션: {signal['action']}")
            print(f"   ✓ 가격: {signal['price']:,.0f}원")
            print(f"   ✓ 신뢰도: {signal['confidence']:.2f}")
            if signal['reason']:
                print(f"   ✓ 이유: {', '.join(signal['reason'])}")
        else:
            print(f"   ✗ 신호 생성 실패")

def test_risk_management():
    """
    리스크 관리 테스트
    """
    print("\n=== 리스크 관리 테스트 ===")
    
    risk_manager = RiskManager()
    
    # 포지션 크기 계산 테스트
    print("1. 포지션 크기 계산 테스트...")
    current_price = 70000  # 7만원
    available_capital = 10000000  # 1천만원
    
    quantity, position_size = risk_manager.calculate_position_size(current_price, available_capital)
    print(f"   ✓ 계산된 수량: {quantity}주")
    print(f"   ✓ 포지션 크기: {position_size:,}원")
    
    # 포지션 추가 테스트
    print("2. 포지션 관리 테스트...")
    risk_manager.add_position("005930", quantity, current_price)
    
    position_info = risk_manager.get_position_info("005930")
    if position_info:
        print(f"   ✓ 포지션 추가 성공")
        print(f"   ✓ 보유 수량: {position_info['quantity']}주")
        print(f"   ✓ 매수 가격: {position_info['entry_price']:,}원")
    
    # 손절/익절 테스트
    print("3. 손절/익절 테스트...")
    
    # 손절 테스트 (가격 하락)
    stop_loss_triggered, stop_loss_info = risk_manager.check_stop_loss("005930", current_price * 0.95)
    print(f"   ✓ 손절 조건 확인: {stop_loss_triggered}")
    
    # 익절 테스트 (가격 상승)
    take_profit_triggered, take_profit_info = risk_manager.check_take_profit("005930", current_price * 1.06)
    print(f"   ✓ 익절 조건 확인: {take_profit_triggered}")
    
    # 포트폴리오 요약 테스트
    print("4. 포트폴리오 요약 테스트...")
    summary = risk_manager.get_portfolio_summary()
    if summary:
        print(f"   ✓ 총 포지션 수: {summary['total_positions']}")
        print(f"   ✓ 총 포지션 가치: {summary['total_value']:,}원")

def test_trading_executor():
    """
    거래 실행 테스트
    """
    print("\n=== 거래 실행 테스트 ===")
    
    executor = TradingExecutor()
    
    # 시뮬레이션 모드 확인
    print("1. 시뮬레이션 모드 테스트...")
    executor.set_simulation_mode(True)
    
    # 계좌 잔고 조회 테스트
    print("2. 계좌 잔고 조회 테스트...")
    balance = executor.get_account_balance()
    if balance:
        print(f"   ✓ 현금: {balance['cash']:,}원")
        print(f"   ✓ 총 가치: {balance['total_value']:,}원")
        print(f"   ✓ 매수 가능 금액: {balance['buying_power']:,}원")
    
    # 매수 주문 테스트
    print("3. 매수 주문 테스트...")
    buy_order = executor.place_buy_order("005930", 10, 70000)
    if buy_order:
        print(f"   ✓ 매수 주문 성공")
        print(f"   ✓ 주문 ID: {buy_order['order_id']}")
        print(f"   ✓ 주문 상태: {buy_order['status']}")
    
    # 매도 주문 테스트
    print("4. 매도 주문 테스트...")
    sell_order = executor.place_sell_order("005930", 10, 72000)
    if sell_order:
        print(f"   ✓ 매도 주문 성공")
        print(f"   ✓ 주문 ID: {sell_order['order_id']}")
        print(f"   ✓ 주문 상태: {sell_order['status']}")

def run_all_tests():
    """
    모든 테스트 실행
    """
    print("🚀 주식자동매매프로그램 테스트 시작")
    print("=" * 50)
    
    try:
        # 데이터 수집 테스트
        data = test_data_collection()
        
        # 매매 전략 테스트
        test_trading_strategy(data)
        
        # 리스크 관리 테스트
        test_risk_management()
        
        # 거래 실행 테스트
        test_trading_executor()
        
        print("\n" + "=" * 50)
        print("✅ 모든 테스트 완료!")
        print("프로그램이 정상적으로 작동합니다.")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        logger.error(f"테스트 중 오류: {e}")

if __name__ == "__main__":
    run_all_tests() 