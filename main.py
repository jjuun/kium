"""
주식자동매매프로그램 메인 파일
"""
import time
import schedule
import threading
import pandas as pd
from datetime import datetime, time as dt_time
from src.core.logger import logger
from src.core.config import Config
from src.core.data_collector import DataCollector
from src.trading.trading_strategy import TradingStrategy
from src.trading.risk_manager import RiskManager
from src.trading.trading_executor import TradingExecutor
import os
import sys
import signal

try:
    import psutil
except ImportError:
    print("psutil 모듈이 필요합니다. 설치 후 다시 실행하세요: pip install psutil")
    sys.exit(1)

def kill_existing_main_py():
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            pid = proc.info['pid']
            if (
                pid != current_pid and
                cmdline and
                'python' in cmdline[0] and
                'main.py' in ' '.join(cmdline)
            ):
                print(f"기존 main.py 프로세스 종료: PID={pid}")
                os.kill(pid, signal.SIGTERM)
        except Exception:
            continue

kill_existing_main_py()

class TradingBot:
    def __init__(self):
        self.data_collector = DataCollector()
        self.strategy = TradingStrategy()
        self.risk_manager = RiskManager()
        self.executor = TradingExecutor()
        self.is_running = False
        self.symbol = Config.SYMBOL
        
    def initialize(self):
        """
        봇 초기화
        """
        try:
            logger.info("=== 주식자동매매프로그램 시작 ===")
            logger.info(f"거래 심볼: {self.symbol}")
            logger.info(f"매매 전략: {Config.STRATEGY}")
            logger.info(f"최대 포지션 크기: {Config.MAX_POSITION_SIZE:,}원")
            logger.info(f"손절 비율: {Config.STOP_LOSS_PERCENT}%")
            logger.info(f"익절 비율: {Config.TAKE_PROFIT_PERCENT}%")
            
            # 초기 데이터 수집
            self.collect_initial_data()
            
            logger.info("초기화 완료")
            
        except Exception as e:
            logger.error(f"초기화 중 오류: {e}")
    
    def collect_initial_data(self):
        """
        초기 데이터 수집
        """
        try:
            logger.info("초기 데이터 수집 중...")
            
            # 과거 데이터 수집
            historical_data = self.data_collector.get_historical_data()
            if historical_data is not None:
                # 기술적 지표 계산
                data_with_indicators = self.data_collector.calculate_technical_indicators(historical_data)
                self.current_data = data_with_indicators
                logger.info(f"초기 데이터 수집 완료: {len(historical_data)}개 데이터")
            else:
                logger.error("초기 데이터 수집 실패")
                
        except Exception as e:
            logger.error(f"초기 데이터 수집 중 오류: {e}")
    
    def update_data(self):
        """
        실시간 데이터 업데이트
        """
        try:
            # 실시간 가격 정보 수집
            realtime_data = self.data_collector.get_realtime_price()
            if realtime_data is None:
                logger.warning("실시간 데이터 수집 실패")
                return False
            
            # 기존 데이터에 새로운 데이터 추가
            if hasattr(self, 'current_data') and self.current_data is not None:
                # 새로운 행 추가 (실제로는 더 정교한 구현 필요)
                new_row = pd.DataFrame([{
                    '시가': realtime_data['current_price'],
                    '고가': realtime_data['current_price'],
                    '저가': realtime_data['current_price'],
                    '종가': realtime_data['current_price'],
                    '거래량': 0  # 실시간 거래량은 별도 수집 필요
                }], index=[realtime_data['timestamp']])
                
                self.current_data = pd.concat([self.current_data, new_row])
                
                # 기술적 지표 재계산
                self.current_data = self.data_collector.calculate_technical_indicators(self.current_data)
                
                return True
            else:
                logger.warning("현재 데이터가 없습니다. 초기 데이터를 수집하세요.")
                return False
                
        except Exception as e:
            logger.error(f"데이터 업데이트 중 오류: {e}")
            return False
    
    def check_trading_time(self):
        """
        거래 시간 확인
        """
        try:
            now = datetime.now().time()
            start_time = datetime.strptime(Config.TRADING_START_TIME, "%H:%M").time()
            end_time = datetime.strptime(Config.TRADING_END_TIME, "%H:%M").time()
            
            return start_time <= now <= end_time
            
        except Exception as e:
            logger.error(f"거래 시간 확인 중 오류: {e}")
            return False
    
    def execute_trading_cycle(self):
        """
        매매 사이클 실행
        """
        try:
            if not self.is_running:
                return
            
            # 거래 시간 확인
            if not self.check_trading_time():
                logger.debug("거래 시간이 아닙니다.")
                return
            
            # 데이터 업데이트
            if not self.update_data():
                logger.warning("데이터 업데이트 실패")
                return
            
            # 현재 포지션 확인
            current_position = self.risk_manager.get_position_info(self.symbol)
            
            # 손절/익절 확인
            if current_position:
                current_price = self.current_data.iloc[-1]['종가']
                
                # 손절 확인
                stop_loss_triggered, stop_loss_info = self.risk_manager.check_stop_loss(self.symbol, current_price)
                if stop_loss_triggered:
                    self.execute_sell_order(stop_loss_info['quantity'], current_price, "손절")
                    return
                
                # 익절 확인
                take_profit_triggered, take_profit_info = self.risk_manager.check_take_profit(self.symbol, current_price)
                if take_profit_triggered:
                    self.execute_sell_order(take_profit_info['quantity'], current_price, "익절")
                    return
            
            # 매매 신호 생성
            signal = self.strategy.generate_signal(self.current_data)
            if signal is None or signal['action'] == 'HOLD':
                return
            
            # 매매 신호에 따른 거래 실행
            if signal['action'] == 'BUY' and not current_position:
                self.execute_buy_order(signal)
            elif signal['action'] == 'SELL' and current_position:
                self.execute_sell_order(current_position['quantity'], signal['price'], "매도 신호")
                
        except Exception as e:
            logger.error(f"매매 사이클 실행 중 오류: {e}")
    
    def execute_buy_order(self, signal):
        """
        매수 주문 실행
        """
        try:
            current_price = signal['price']
            
            # 계좌 잔고 확인
            balance = self.executor.get_account_balance()
            if balance is None:
                logger.error("계좌 잔고 조회 실패")
                return
            
            # 포지션 크기 계산
            quantity, position_size = self.risk_manager.calculate_position_size(current_price, balance['cash'])
            if quantity == 0:
                logger.warning("매수 가능한 수량이 없습니다.")
                return
            
            # 리스크 한도 확인
            risk_ok, risk_message = self.risk_manager.check_risk_limits(self.symbol, quantity, current_price)
            if not risk_ok:
                logger.warning(f"리스크 한도 초과: {risk_message}")
                return
            
            # 매수 주문 실행
            order_result = self.executor.place_buy_order(self.symbol, quantity, current_price)
            if order_result is None:
                logger.error("매수 주문 실패")
                return
            
            # 포지션 추가
            self.risk_manager.add_position(self.symbol, quantity, current_price)
            
            logger.info(f"매수 주문 성공: {quantity}주 @ {current_price:,}원")
            
        except Exception as e:
            logger.error(f"매수 주문 실행 중 오류: {e}")
    
    def execute_sell_order(self, quantity, price, reason=""):
        """
        매도 주문 실행
        """
        try:
            # 매도 주문 실행
            order_result = self.executor.place_sell_order(self.symbol, quantity, price)
            if order_result is None:
                logger.error("매도 주문 실패")
                return
            
            # 포지션 제거
            trade_record = self.risk_manager.remove_position(self.symbol, price)
            if trade_record:
                logger.info(f"매도 주문 성공: {quantity}주 @ {price:,}원 - {reason}")
            
        except Exception as e:
            logger.error(f"매도 주문 실행 중 오류: {e}")
    
    def print_portfolio_summary(self):
        """
        포트폴리오 요약 출력
        """
        try:
            summary = self.risk_manager.get_portfolio_summary()
            if summary:
                logger.info("=== 포트폴리오 요약 ===")
                logger.info(f"총 포지션 수: {summary['total_positions']}")
                logger.info(f"총 포지션 가치: {summary['total_value']:,}원")
                logger.info(f"총 수익/손실: {summary['total_pnl']:,}원 ({summary['total_pnl_percent']:+.2f}%)")
                logger.info(f"총 거래 수: {summary['total_trades']}")
                logger.info(f"수익 거래: {summary['winning_trades']}")
                logger.info(f"손실 거래: {summary['losing_trades']}")
                
                if summary['total_trades'] > 0:
                    win_rate = (summary['winning_trades'] / summary['total_trades']) * 100
                    logger.info(f"승률: {win_rate:.1f}%")
            
        except Exception as e:
            logger.error(f"포트폴리오 요약 출력 중 오류: {e}")
    
    def start(self):
        """
        봇 시작
        """
        try:
            self.initialize()
            self.is_running = True
            
            # 매 1분마다 매매 사이클 실행
            schedule.every(1).minutes.do(self.execute_trading_cycle)
            
            # 매 10분마다 포트폴리오 요약 출력
            schedule.every(10).minutes.do(self.print_portfolio_summary)
            
            logger.info("자동매매 봇이 시작되었습니다.")
            
            # 스케줄러 실행
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단되었습니다.")
            self.stop()
        except Exception as e:
            logger.error(f"봇 실행 중 오류: {e}")
            self.stop()
    
    def stop(self):
        """
        봇 중지
        """
        try:
            self.is_running = False
            logger.info("자동매매 봇이 중지되었습니다.")
            self.print_portfolio_summary()
            
        except Exception as e:
            logger.error(f"봇 중지 중 오류: {e}")

def main():
    """
    메인 함수
    """
    try:
        # 거래 봇 생성 및 시작
        bot = TradingBot()
        bot.start()
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류: {e}")

if __name__ == "__main__":
    main() 