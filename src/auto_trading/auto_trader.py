"""
자동매매 메인 엔진
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from src.core.logger import logger
from src.auto_trading.watchlist_manager import WatchlistManager
from src.auto_trading.condition_manager import ConditionManager
from src.auto_trading.signal_monitor import SignalMonitor
from src.trading.order_executor import OrderExecutor
from src.api.kiwoom_api import KiwoomAPI

@dataclass
class TradingSignal:
    """매매 신호"""
    symbol: str
    signal_type: str  # 'buy' or 'sell'
    condition_id: int
    condition_value: str
    current_price: float
    timestamp: datetime
    executed: bool = False

class AutoTrader:
    """자동매매 메인 엔진 클래스"""
    
    def __init__(self, db_path: str = "auto_trading.db"):
        """
        초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.watchlist_manager = WatchlistManager(db_path)
        self.condition_manager = ConditionManager(db_path)
        self.signal_monitor = SignalMonitor(db_path)
        self.order_executor = OrderExecutor()
        self.kiwoom_api = KiwoomAPI()
        
        # 자동매매 상태
        self.is_running = False
        self.monitoring_task = None
        
        # 리스크 관리
        self.max_daily_orders = 10  # 일일 최대 주문 수
        self.daily_order_count = 0
        self.last_order_reset = datetime.now().date()
        
        # 중복 주문 방지 (종목별 마지막 주문 시간)
        self.last_order_time = {}
        self.order_cooldown = 300  # 5분 쿨다운
        
        self.trade_quantity = 1  # 기본값
        
        logger.info("자동매매 엔진 초기화 완료")
    
    def start(self, quantity=1):
        """자동매매 시작"""
        if self.is_running:
            logger.warning("자동매매가 이미 실행 중입니다.")
            return False
        self.trade_quantity = max(1, int(quantity))
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"자동매매 시작됨 (매매 수량: {self.trade_quantity}주)")
        return True
    
    def stop(self):
        """자동매매 중지"""
        if not self.is_running:
            logger.warning("자동매매가 실행되지 않았습니다.")
            return False
        
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("자동매매 중지됨")
        return True
    
    async def _monitoring_loop(self):
        """모니터링 루프"""
        while self.is_running:
            try:
                await self._check_conditions()
                await asyncio.sleep(30)  # 30초마다 조건 체크
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    async def _check_conditions(self):
        """등록된 조건들을 체크하고 신호 생성"""
        try:
            # 활성화된 감시 종목 조회
            active_symbols = self.watchlist_manager.get_active_symbols()
            if not active_symbols:
                return
            
            # 일일 주문 수 리셋 체크
            self._reset_daily_order_count()
            
            # 각 종목별 조건 체크
            for symbol in active_symbols:
                if not self.is_running:
                    break
                
                await self._check_symbol_conditions(symbol)
                
        except Exception as e:
            logger.error(f"조건 체크 오류: {e}")
    
    async def _check_symbol_conditions(self, symbol: str):
        """특정 종목의 조건들을 체크"""
        try:
            # 활성화된 조건들 조회
            conditions = self.condition_manager.get_conditions(
                symbol=symbol, 
                active_only=True
            )
            
            if not conditions:
                return
            
            # 현재가 조회
            current_price = await self._get_current_price(symbol)
            if current_price is None:
                return
            
            # 각 조건 평가
            for condition in conditions:
                if not self.is_running:
                    break
                
                signal = await self._evaluate_condition(condition, current_price)
                if signal:
                    # 신호 모니터링에 기록
                    signal_id = self.signal_monitor.record_signal(
                        signal.symbol, signal.signal_type, signal.condition_id,
                        signal.condition_value, signal.current_price
                    )
                    signal.id = signal_id
                    await self._execute_signal(signal)
                    
        except Exception as e:
            logger.error(f"종목 조건 체크 오류 {symbol}: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        try:
            price_data = self.kiwoom_api.get_stock_price(symbol)
            if price_data and 'output' in price_data and price_data['output']:
                output = price_data['output'][0] if isinstance(price_data['output'], list) else price_data['output']
                current_price = output.get('prpr', None)
                if current_price and current_price != '0':
                    return float(current_price)
            return None
        except Exception as e:
            logger.error(f"현재가 조회 실패 {symbol}: {e}")
            return None
    
    async def _evaluate_condition(self, condition, current_price: float) -> Optional[TradingSignal]:
        """조건 평가"""
        try:
            condition_value = condition.value.strip()
            
            # 간단한 가격 조건 평가 (예: "현재가 < 50000", "현재가 > 60000")
            if "현재가" in condition_value:
                signal = self._evaluate_price_condition(condition, condition_value, current_price)
                if signal:
                    logger.info(f"매매 신호 생성: {signal.symbol} {signal.signal_type} - {condition_value}")
                    return signal
            
            # RSI 조건 평가 (예: "RSI < 30", "RSI > 70")
            elif "RSI" in condition_value:
                signal = await self._evaluate_rsi_condition(condition, condition_value)
                if signal:
                    logger.info(f"RSI 매매 신호 생성: {signal.symbol} {signal.signal_type} - {condition_value}")
                    return signal
            
            # 이동평균 조건 평가 (예: "MA5 > MA20")
            elif "MA" in condition_value:
                signal = await self._evaluate_ma_condition(condition, condition_value)
                if signal:
                    logger.info(f"이동평균 매매 신호 생성: {signal.symbol} {signal.signal_type} - {condition_value}")
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"조건 평가 오류: {e}")
            return None
    
    def _evaluate_price_condition(self, condition, condition_value: str, current_price: float) -> Optional[TradingSignal]:
        """가격 조건 평가"""
        try:
            # "현재가 < 50000" 형태 파싱
            if "<" in condition_value:
                target_price = float(condition_value.split("<")[1].strip())
                if current_price < target_price and condition.condition_type == "buy":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="buy",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=current_price,
                        timestamp=datetime.now()
                    )
            elif ">" in condition_value:
                target_price = float(condition_value.split(">")[1].strip())
                if current_price > target_price and condition.condition_type == "sell":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="sell",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=current_price,
                        timestamp=datetime.now()
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"가격 조건 평가 오류: {e}")
            return None
    
    async def _evaluate_rsi_condition(self, condition, condition_value: str) -> Optional[TradingSignal]:
        """RSI 조건 평가 (실제 구현에서는 RSI 계산 필요)"""
        try:
            # TODO: RSI 계산 로직 구현
            # 현재는 더미 값으로 평가
            current_rsi = 50  # 실제로는 RSI 계산 필요
            
            if "<" in condition_value:
                target_rsi = float(condition_value.split("<")[1].strip())
                if current_rsi < target_rsi and condition.condition_type == "buy":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="buy",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=0,  # RSI 신호는 가격 없음
                        timestamp=datetime.now()
                    )
            elif ">" in condition_value:
                target_rsi = float(condition_value.split(">")[1].strip())
                if current_rsi > target_rsi and condition.condition_type == "sell":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="sell",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=0,
                        timestamp=datetime.now()
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"RSI 조건 평가 오류: {e}")
            return None
    
    async def _evaluate_ma_condition(self, condition, condition_value: str) -> Optional[TradingSignal]:
        """이동평균 조건 평가 (실제 구현에서는 MA 계산 필요)"""
        try:
            # TODO: 이동평균 계산 로직 구현
            # 현재는 더미 값으로 평가
            ma5 = 50000
            ma20 = 48000
            
            if "MA5 > MA20" in condition_value:
                if ma5 > ma20 and condition.condition_type == "buy":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="buy",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=0,
                        timestamp=datetime.now()
                    )
            elif "MA5 < MA20" in condition_value:
                if ma5 < ma20 and condition.condition_type == "sell":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="sell",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=0,
                        timestamp=datetime.now()
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"이동평균 조건 평가 오류: {e}")
            return None
    
    async def _execute_signal(self, signal: TradingSignal):
        """매매 신호 실행"""
        try:
            # 리스크 관리 체크
            if not self._check_risk_management(signal):
                logger.warning(f"리스크 관리로 인한 신호 실행 차단: {signal.symbol}")
                return
            
            # 주문 실행
            if signal.signal_type == "buy":
                success = await self._execute_buy_order(signal)
            else:
                success = await self._execute_sell_order(signal)
            
            if success:
                signal.executed = True
                self.daily_order_count += 1
                self.last_order_time[signal.symbol] = datetime.now()
                logger.info(f"매매 신호 실행 완료: {signal.symbol} {signal.signal_type}")
            else:
                logger.error(f"매매 신호 실행 실패: {signal.symbol} {signal.signal_type}")
                
        except Exception as e:
            logger.error(f"매매 신호 실행 오류: {e}")
    
    def _check_risk_management(self, signal: TradingSignal) -> bool:
        """리스크 관리 체크"""
        try:
            # 일일 주문 수 제한
            if self.daily_order_count >= self.max_daily_orders:
                logger.warning(f"일일 주문 수 제한 도달: {self.daily_order_count}")
                return False
            
            # 중복 주문 방지
            if signal.symbol in self.last_order_time:
                time_diff = (datetime.now() - self.last_order_time[signal.symbol]).total_seconds()
                if time_diff < self.order_cooldown:
                    logger.warning(f"주문 쿨다운 중: {signal.symbol} ({self.order_cooldown - time_diff:.0f}초 남음)")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"리스크 관리 체크 오류: {e}")
            return False
    
    async def _execute_buy_order(self, signal: TradingSignal) -> bool:
        """매수 주문 실행"""
        try:
            # TODO: 실제 주문 실행 로직 구현
            # 현재는 로그만 출력
            logger.info(f"매수 주문 실행: {signal.symbol} - {signal.condition_value} (수량: {self.trade_quantity})")
            
            # 실제 주문 실행 시:
            # from src.trading.order_executor import OrderRequest, OrderType, OrderPriceType
            # order_request = OrderRequest(
            #     symbol=signal.symbol,
            #     order_type=OrderType.BUY,
            #     quantity=self.trade_quantity,
            #     price=0,
            #     price_type=OrderPriceType.MARKET
            # )
            # result = self.order_executor.place_order(order_request)
            # return result and result.status.value not in ['거부', 'REJECTED']
            
            return True
            
        except Exception as e:
            logger.error(f"매수 주문 실행 오류: {e}")
            return False
    
    async def _execute_sell_order(self, signal: TradingSignal) -> bool:
        """매도 주문 실행"""
        try:
            # TODO: 실제 주문 실행 로직 구현
            # 현재는 로그만 출력
            logger.info(f"매도 주문 실행: {signal.symbol} - {signal.condition_value} (수량: {self.trade_quantity})")
            
            # 실제 주문 실행 시:
            # order_request = OrderRequest(
            #     symbol=signal.symbol,
            #     order_type=OrderType.SELL,
            #     quantity=self.trade_quantity,
            #     price=0,
            #     price_type=OrderPriceType.MARKET
            # )
            
            return True
            
        except Exception as e:
            logger.error(f"매도 주문 실행 오류: {e}")
            return False
    
    def _reset_daily_order_count(self):
        """일일 주문 수 리셋"""
        current_date = datetime.now().date()
        if current_date > self.last_order_reset:
            self.daily_order_count = 0
            self.last_order_reset = current_date
            logger.info("일일 주문 수 리셋됨")
    
    def get_status(self) -> Dict[str, Any]:
        """자동매매 상태 조회"""
        return {
            'is_running': self.is_running,
            'daily_order_count': self.daily_order_count,
            'max_daily_orders': self.max_daily_orders,
            'active_symbols_count': len(self.watchlist_manager.get_active_symbols()),
            'active_conditions_count': len(self.condition_manager.get_conditions(active_only=True)),
            'last_order_reset': self.last_order_reset.isoformat(),
            'timestamp': datetime.now().isoformat()
        } 