"""
거래 실행 클래스
"""
import time
import requests
import json
from datetime import datetime
from src.core.logger import logger
from src.core.config import Config
from src.api.kiwoom_api import KiwoomAPI

class TradingExecutor:
    def __init__(self):
        self.api_key = Config.API_KEY
        self.api_secret = Config.API_SECRET
        self.api_url = Config.API_URL
        self.is_simulation = True  # 시뮬레이션 모드 (실제 거래는 False)
        
        # 키움증권 API 초기화
        self.kiwoom_api = KiwoomAPI()
        
    def place_buy_order(self, symbol, quantity, price=None):
        """
        매수 주문 실행
        """
        try:
            if self.is_simulation:
                # 시뮬레이션 모드
                order_result = {
                    'order_id': f"SIM_BUY_{int(time.time())}",
                    'symbol': symbol,
                    'action': 'BUY',
                    'quantity': quantity,
                    'price': price or 0,
                    'status': 'FILLED',
                    'timestamp': datetime.now(),
                    'commission': 0,
                    'total_amount': quantity * (price or 0)
                }
                
                logger.info(f"시뮬레이션 매수 주문: {symbol} - {quantity}주 @ {price:,}원")
                return order_result
            else:
                # 키움증권 API를 통한 실제 주문
                result = self.kiwoom_api.place_order(symbol, quantity, price, '00')  # 지정가 주문
                if result:
                    return {
                        'order_id': result.get('ODNO', f"KIWOOM_BUY_{int(time.time())}"),
                        'symbol': symbol,
                        'action': 'BUY',
                        'quantity': quantity,
                        'price': price or 0,
                        'status': 'PENDING',
                        'timestamp': datetime.now(),
                        'commission': 0,
                        'total_amount': quantity * (price or 0)
                    }
                return None
                
        except Exception as e:
            logger.error(f"매수 주문 실행 중 오류: {e}")
            return None
    
    def place_sell_order(self, symbol, quantity, price=None):
        """
        매도 주문 실행
        """
        try:
            if self.is_simulation:
                # 시뮬레이션 모드
                order_result = {
                    'order_id': f"SIM_SELL_{int(time.time())}",
                    'symbol': symbol,
                    'action': 'SELL',
                    'quantity': quantity,
                    'price': price or 0,
                    'status': 'FILLED',
                    'timestamp': datetime.now(),
                    'commission': 0,
                    'total_amount': quantity * (price or 0)
                }
                
                logger.info(f"시뮬레이션 매도 주문: {symbol} - {quantity}주 @ {price:,}원")
                return order_result
            else:
                # 키움증권 API를 통한 실제 주문
                result = self.kiwoom_api.place_order(symbol, quantity, price, '00')  # 지정가 주문
                if result:
                    return {
                        'order_id': result.get('ODNO', f"KIWOOM_SELL_{int(time.time())}"),
                        'symbol': symbol,
                        'action': 'SELL',
                        'quantity': quantity,
                        'price': price or 0,
                        'status': 'PENDING',
                        'timestamp': datetime.now(),
                        'commission': 0,
                        'total_amount': quantity * (price or 0)
                    }
                return None
                
        except Exception as e:
            logger.error(f"매도 주문 실행 중 오류: {e}")
            return None
    

    
    def get_order_status(self, order_id):
        """
        주문 상태 조회
        """
        try:
            if self.is_simulation:
                # 시뮬레이션에서는 항상 체결됨
                return {
                    'order_id': order_id,
                    'status': 'FILLED',
                    'filled_quantity': 0,
                    'remaining_quantity': 0,
                    'average_price': 0
                }
            else:
                # 키움증권 API를 통한 주문 상태 조회
                result = self.kiwoom_api.get_order_status(order_id)
                if result:
                    return {
                        'order_id': order_id,
                        'status': result.get('ORD_STAT_CD', 'UNKNOWN'),
                        'filled_quantity': result.get('EXEC_QTY', 0),
                        'remaining_quantity': result.get('ORD_QTY', 0) - result.get('EXEC_QTY', 0),
                        'average_price': result.get('EXEC_PRC', 0)
                    }
                return None
                
        except Exception as e:
            logger.error(f"주문 상태 조회 중 오류: {e}")
            return None
    

    
    def cancel_order(self, order_id):
        """
        주문 취소
        """
        try:
            if self.is_simulation:
                logger.info(f"시뮬레이션 주문 취소: {order_id}")
                return True
            else:
                # 키움증권 API를 통한 주문 취소
                # 주문 취소를 위해서는 원주문 정보가 필요하므로 실제 구현에서는 주문 정보를 저장해두어야 함
                result = self.kiwoom_api.cancel_order(order_id, "", 0)
                return result is not None
                
        except Exception as e:
            logger.error(f"주문 취소 중 오류: {e}")
            return False
    

    
    def get_account_balance(self):
        """
        계좌 잔고 조회
        """
        try:
            if self.is_simulation:
                # 시뮬레이션 계좌 잔고
                return {
                    'cash': 10000000,  # 1천만원
                    'total_value': 10000000,
                    'buying_power': 10000000,
                    'timestamp': datetime.now()
                }
            else:
                # 키움증권 API를 통한 잔고 조회
                result = self.kiwoom_api.get_balance()
                if result:
                    # 키움증권 API 응답을 파싱하여 잔고 정보 추출
                    balance_data = result.get('output1', {})
                    return {
                        'cash': int(balance_data.get('prvs_rcdl_excc_amt', 0)),  # 예수금
                        'total_value': int(balance_data.get('tot_evlu_amt', 0)),  # 총평가금액
                        'buying_power': int(balance_data.get('ord_psbl_cash', 0)),  # 주문가능현금
                        'timestamp': datetime.now()
                    }
                return None
                
        except Exception as e:
            logger.error(f"계좌 잔고 조회 중 오류: {e}")
            return None
    

    
    def get_positions(self):
        """
        현재 포지션 조회
        """
        try:
            if self.is_simulation:
                # 시뮬레이션 포지션
                return []
            else:
                # 실제 거래소 API 호출
                return self._get_real_positions()
                
        except Exception as e:
            logger.error(f"포지션 조회 중 오류: {e}")
            return []
    

    
    def set_simulation_mode(self, is_simulation=True):
        """
        시뮬레이션 모드 설정
        """
        self.is_simulation = is_simulation
        mode = "시뮬레이션" if is_simulation else "실제 거래"
        logger.info(f"거래 모드 변경: {mode}")
    
    def calculate_commission(self, order_value):
        """
        수수료 계산 (한국 주식 기준)
        """
        try:
            # 한국 주식 수수료 (예시)
            # 매수/매도 수수료: 0.015%
            # 증권거래세: 매도시 0.23%
            
            commission_rate = 0.00015  # 0.015%
            tax_rate = 0.0023  # 0.23%
            
            commission = order_value * commission_rate
            tax = order_value * tax_rate
            
            return commission, tax
            
        except Exception as e:
            logger.error(f"수수료 계산 중 오류: {e}")
            return 0, 0 