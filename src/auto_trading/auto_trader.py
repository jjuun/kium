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
from src.core.data_collector import DataCollector


@dataclass
class TradingSignal:
    """매매 신호"""

    symbol: str
    signal_type: str  # 'buy' or 'sell'
    condition_id: int
    condition_value: str
    current_price: float
    timestamp: datetime
    rsi_value: Optional[float] = None
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

        # 매매 모드 (기본값은 실제 매매 모드)
        self.test_mode = False  # True: 테스트 모드, False: 실제 매매

        # 리스크 관리 - 테스트와 실제 매매를 분리
        self.max_daily_orders_test = 50  # 테스트 모드 일일 최대 주문 수 (더 많이 허용)
        self.max_daily_orders_real = 10  # 실제 매매 일일 최대 주문 수
        self.daily_order_count_test = 0  # 테스트 모드 일일 주문 수
        self.daily_order_count_real = 0  # 실제 매매 일일 주문 수
        self.last_order_reset = datetime.now().date()

        # 중복 주문 방지 (종목별 마지막 주문 시간)
        self.last_order_time = {}
        self.order_cooldown = 60  # 1분 쿨다운 (기본값)

        self.trade_quantity = 1  # 기본값

        # 에러 추적
        self.last_error = None
        self.error_timestamp = None

        logger.info("자동매매 엔진 초기화 완료")

    def start(self, quantity=1):
        """자동매매 시작"""
        if self.is_running:
            logger.warning("자동매매가 이미 실행 중입니다.")
            return False
        self.trade_quantity = max(1, int(quantity))
        self.is_running = True

        # 이벤트 루프가 이미 실행 중인지 확인
        try:
            loop = asyncio.get_running_loop()
            # 이미 실행 중인 루프가 있으면 태스크 생성
            self.monitoring_task = loop.create_task(self._monitoring_loop())
        except RuntimeError:
            # 실행 중인 루프가 없으면 스레드에서 실행
            import threading

            def run_monitoring():
                asyncio.run(self._monitoring_loop())

            self.monitoring_thread = threading.Thread(
                target=run_monitoring, daemon=True
            )
            self.monitoring_thread.start()

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
            # 종목코드 정규화 (A 접두사 제거)
            normalized_symbol = (
                symbol.replace("A", "") if symbol.startswith("A") else symbol
            )

            # 활성화된 조건들 조회 (정규화된 종목코드로)
            conditions = self.condition_manager.get_conditions(
                symbol=normalized_symbol, active_only=True
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
                        signal.symbol,
                        signal.signal_type,
                        signal.condition_id,
                        signal.condition_value,
                        signal.current_price,
                        signal.rsi_value,
                    )
                    signal.id = signal_id
                    await self._execute_signal(signal)

        except Exception as e:
            logger.error(f"종목 조건 체크 오류 {symbol}: {e}")

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """현재가 조회"""
        try:
            # 토큰 자동 갱신 확인
            if not self.kiwoom_api.refresh_token_if_needed():
                logger.error(f"토큰 갱신 실패: {symbol} - 주문 실행을 차단합니다")
                logger.error(
                    "⚠️ 토큰 문제로 인한 자동 매매 차단 - 웹 대시보드에서 토큰을 확인하세요"
                )
                return None

            # 실제 현재가 조회 (키움 API 사용)
            price_data = self.kiwoom_api.get_stock_price(symbol)
            if price_data and "output" in price_data and price_data["output"]:
                output = (
                    price_data["output"][0]
                    if isinstance(price_data["output"], list)
                    else price_data["output"]
                )
                current_price = output.get("prpr", None)
                if current_price and current_price != "0":
                    price_value = float(current_price)
                    logger.info(f"실제 현재가 조회: {symbol} = {price_value}")
                    return price_value

            # API 조회 실패 시 None 반환 (더미 가격 사용 금지)
            logger.error(f"현재가 조회 실패: {symbol} - 주문 실행을 차단합니다")
            return None

        except Exception as e:
            logger.error(f"현재가 조회 실패 {symbol}: {e}")
            # 오류 발생 시 None 반환 (더미 가격 사용 금지)
            logger.error(f"현재가 조회 오류: {symbol} - 주문 실행을 차단합니다")
            return None

    async def _evaluate_condition(
        self, condition, current_price: float
    ) -> Optional[TradingSignal]:
        """조건 평가"""
        try:
            condition_value = condition.value.strip()

            # RSI 조건 평가 (예: "RSI < 30", "RSI > 70") - 먼저 확인
            if condition.category == "rsi" or "RSI" in condition_value:
                signal = await self._evaluate_rsi_condition(condition, condition_value)
                if signal:
                    logger.info(
                        f"RSI 매매 신호 생성: {signal.symbol} {signal.signal_type} - {condition_value}"
                    )
                    return signal

            # 이동평균 조건 평가 (예: "MA5 > MA20")
            elif condition.category == "ma" or "MA" in condition_value:
                signal = await self._evaluate_ma_condition(condition, condition_value)
                if signal:
                    logger.info(
                        f"이동평균 매매 신호 생성: {signal.symbol} {signal.signal_type} - {condition_value}"
                    )
                    return signal

            # 가격 조건 평가 (예: "< 50000", "> 60000", "현재가 < 50000") - 마지막에 확인
            elif (
                condition.category == "price"
                or "<" in condition_value
                or ">" in condition_value
            ):
                signal = self._evaluate_price_condition(
                    condition, condition_value, current_price
                )
                if signal:
                    logger.info(
                        f"가격 매매 신호 생성: {signal.symbol} {signal.signal_type} - {condition_value}"
                    )
                    return signal

            return None

        except Exception as e:
            logger.error(f"조건 평가 오류: {e}")
            return None

    def _evaluate_price_condition(
        self, condition, condition_value: str, current_price: float
    ) -> Optional[TradingSignal]:
        """가격 조건 평가"""
        try:
            # RSI 값 계산 (가격 조건에서도 RSI 정보 제공)
            current_rsi = None
            try:
                data_collector = DataCollector()
                df = data_collector.get_historical_data(condition.symbol)
                if df is not None and not df.empty and "종가" in df.columns:
                    df = data_collector.calculate_technical_indicators(df)
                    if "RSI" in df.columns and not df["RSI"].dropna().empty:
                        current_rsi = float(df["RSI"].dropna().iloc[-1])
            except Exception as e:
                logger.warning(f"가격 조건에서 RSI 계산 실패: {e}")

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
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
                    )
            elif ">" in condition_value:
                target_price = float(condition_value.split(">")[1].strip())
                if current_price > target_price and condition.condition_type == "buy":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="buy",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=current_price,
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
                    )
                elif (
                    current_price > target_price and condition.condition_type == "sell"
                ):
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="sell",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=current_price,
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
                    )

            return None

        except Exception as e:
            logger.error(f"가격 조건 평가 오류: {e}")
            return None

    async def _evaluate_rsi_condition(
        self, condition, condition_value: str
    ) -> Optional[TradingSignal]:
        """RSI 조건 평가 (실제 RSI 계산)"""
        try:
            # 과거 데이터 수집 및 RSI 계산
            data_collector = DataCollector()
            df = data_collector.get_historical_data(condition.symbol)
            if df is None or df.empty or "종가" not in df.columns:
                logger.warning(f"RSI 계산용 데이터 부족: {condition.symbol}")
                return None
            df = data_collector.calculate_technical_indicators(df)
            if "RSI" not in df.columns or df["RSI"].dropna().empty:
                logger.warning(f"RSI 계산 실패: {condition.symbol}")
                return None
            current_rsi = float(df["RSI"].dropna().iloc[-1])
            logger.info(f"실제 RSI 계산: {condition.symbol} = {current_rsi:.2f}")

            # 현재가 조회 (RSI 조건에서도 현재가 필요)
            current_price = await self._get_current_price(condition.symbol)
            if current_price is None:
                logger.warning(f"RSI 조건에서 현재가 조회 실패: {condition.symbol}")
                return None

            if "<" in condition_value:
                target_rsi = float(condition_value.split("<")[1].strip())
                if current_rsi < target_rsi and condition.condition_type == "buy":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="buy",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=current_price,
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
                    )
            elif ">" in condition_value:
                target_rsi = float(condition_value.split(">")[1].strip())
                if current_rsi > target_rsi and condition.condition_type == "sell":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="sell",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=current_price,
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
                    )
            return None
        except Exception as e:
            logger.error(f"RSI 조건 평가 오류: {e}")
            return None

    async def _evaluate_ma_condition(
        self, condition, condition_value: str
    ) -> Optional[TradingSignal]:
        """이동평균 조건 평가 (실제 구현에서는 MA 계산 필요)"""
        try:
            # RSI 값 계산 (이동평균 조건에서도 RSI 정보 제공)
            current_rsi = None
            try:
                data_collector = DataCollector()
                df = data_collector.get_historical_data(condition.symbol)
                if df is not None and not df.empty and "종가" in df.columns:
                    df = data_collector.calculate_technical_indicators(df)
                    if "RSI" in df.columns and not df["RSI"].dropna().empty:
                        current_rsi = float(df["RSI"].dropna().iloc[-1])
            except Exception as e:
                logger.warning(f"이동평균 조건에서 RSI 계산 실패: {e}")

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
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
                    )
            elif "MA5 < MA20" in condition_value:
                if ma5 < ma20 and condition.condition_type == "sell":
                    return TradingSignal(
                        symbol=condition.symbol,
                        signal_type="sell",
                        condition_id=condition.id,
                        condition_value=condition_value,
                        current_price=0,
                        timestamp=datetime.now(),
                        rsi_value=current_rsi,
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

                # 현재 모드에 따라 적절한 카운터 증가
                if self.test_mode:
                    self.daily_order_count_test += 1
                    mode_text = "테스트"
                else:
                    self.daily_order_count_real += 1
                    mode_text = "실제"

                self.last_order_time[signal.symbol] = datetime.now()

                # 신호 상태를 executed로 업데이트
                if hasattr(signal, "id") and signal.id:
                    self.signal_monitor.update_signal_execution(
                        signal.id, signal.current_price, self.trade_quantity
                    )

                logger.info(
                    f"매매 신호 실행 완료 ({mode_text}): {signal.symbol} {signal.signal_type}"
                )
            else:
                logger.error(
                    f"매매 신호 실행 실패: {signal.symbol} {signal.signal_type}"
                )

        except Exception as e:
            logger.error(f"매매 신호 실행 오류: {e}")

    def _check_risk_management(self, signal: TradingSignal) -> bool:
        """리스크 관리 체크"""
        try:
            # 현재 모드에 따라 적절한 카운터와 제한 사용
            if self.test_mode:
                current_count = self.daily_order_count_test
                max_count = self.max_daily_orders_test
                mode_text = "테스트 모드"
            else:
                current_count = self.daily_order_count_real
                max_count = self.max_daily_orders_real
                mode_text = "실제 매매"

            # 일일 주문 수 제한
            if current_count >= max_count:
                logger.warning(
                    f"일일 주문 수 제한 도달 ({mode_text}): {current_count}/{max_count}"
                )
                return False

            # 중복 주문 방지
            if signal.symbol in self.last_order_time:
                time_diff = (
                    datetime.now() - self.last_order_time[signal.symbol]
                ).total_seconds()
                if time_diff < self.order_cooldown:
                    logger.warning(
                        f"주문 쿨다운 중: {signal.symbol} ({self.order_cooldown - time_diff:.0f}초 남음)"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"리스크 관리 체크 오류: {e}")
            return False

    async def _execute_buy_order(self, signal: TradingSignal) -> bool:
        """매수 주문 실행"""
        try:
            if self.test_mode:
                # 테스트 모드: 실제 주문 없이 성공으로 처리
                logger.info(
                    f"🔵 [테스트 모드] 매수 주문 실행: {signal.symbol} - {signal.condition_value} (수량: {self.trade_quantity})"
                )
                logger.info(
                    f"✅ 매수 주문 성공 (테스트): {signal.symbol} {self.trade_quantity}주"
                )
                return True
            else:
                # 실제 주문 실행
                logger.info(
                    f"🔵 [실제 매매] 매수 주문 실행: {signal.symbol} - {signal.condition_value} (수량: {self.trade_quantity})"
                )

                # 액세스 토큰 확인 (실제 주문 실행 전 필수)
                if not self.kiwoom_api.access_token:
                    logger.error(
                        f"❌ 매수 주문 실패 (실제): {signal.symbol} - 액세스 토큰이 없습니다"
                    )
                    return False

                # 신호에서 현재가 사용 (이미 조회됨)
                current_price = signal.current_price
                logger.info(
                    f"📊 신호에서 현재가 사용: {signal.symbol} = {current_price}"
                )

                if current_price is None or current_price <= 0:
                    logger.error(
                        f"❌ 매수 주문 실패 (실제): {signal.symbol} - 현재가 조회 실패 (가격: {current_price})"
                    )
                    return False

                logger.info(
                    f"💰 매수 주문 생성: {signal.symbol} {self.trade_quantity}주 @ {int(current_price)}원"
                )

                from src.trading.order_executor import (
                    OrderRequest,
                    OrderType,
                    OrderPriceType,
                )

                order_request = OrderRequest(
                    symbol=signal.symbol,
                    order_type=OrderType.BUY,
                    quantity=self.trade_quantity,
                    price=int(current_price),  # 현재가를 정수로 변환
                    price_type=OrderPriceType.MARKET,
                )

                logger.info(
                    f"📋 주문 요청 생성 완료: {order_request.symbol} {order_request.order_type.value} {order_request.quantity}주 @ {int(order_request.price)}원"
                )
                result = self.order_executor.place_order(order_request)

                if result and result.status.value in [
                    "접수완료",
                    "ACCEPTED",
                    "전체체결",
                    "FILLED",
                ]:
                    logger.info(
                        f"✅ 매수 주문 성공 (실제): {signal.symbol} {self.trade_quantity}주 @ {int(current_price)}원"
                    )
                    logger.info(
                        f"주문 상태: {result.status.value}, 주문 ID: {result.order_id}"
                    )
                    return True
                else:
                    error_msg = f"매수 주문 실패: {signal.symbol} - {result.status.value if result else '주문 실패'}"
                    logger.error(f"❌ {error_msg}")
                    self.record_error(error_msg)
                    return False

        except Exception as e:
            logger.error(f"매수 주문 실행 오류: {e}")
            return False

    async def _execute_sell_order(self, signal: TradingSignal) -> bool:
        """매도 주문 실행"""
        try:
            if self.test_mode:
                # 테스트 모드: 실제 주문 없이 성공으로 처리
                logger.info(
                    f"🔴 [테스트 모드] 매도 주문 실행: {signal.symbol} - {signal.condition_value} (수량: {self.trade_quantity})"
                )
                logger.info(
                    f"✅ 매도 주문 성공 (테스트): {signal.symbol} {self.trade_quantity}주"
                )
                return True
            else:
                # 실제 주문 실행
                logger.info(
                    f"🔴 [실제 매매] 매도 주문 실행: {signal.symbol} - {signal.condition_value} (수량: {self.trade_quantity})"
                )

                # 액세스 토큰 확인 (실제 주문 실행 전 필수)
                if not self.kiwoom_api.access_token:
                    logger.error(
                        f"❌ 매도 주문 실패 (실제): {signal.symbol} - 액세스 토큰이 없습니다"
                    )
                    return False

                # 신호에서 현재가 사용 (이미 조회됨)
                current_price = signal.current_price
                logger.info(
                    f"📊 신호에서 현재가 사용: {signal.symbol} = {current_price}"
                )

                if current_price is None or current_price <= 0:
                    logger.error(
                        f"❌ 매도 주문 실패 (실제): {signal.symbol} - 현재가 조회 실패 (가격: {current_price})"
                    )
                    return False

                logger.info(
                    f"💰 매도 주문 생성: {signal.symbol} {self.trade_quantity}주 @ {int(current_price)}원"
                )

                from src.trading.order_executor import (
                    OrderRequest,
                    OrderType,
                    OrderPriceType,
                )

                order_request = OrderRequest(
                    symbol=signal.symbol,
                    order_type=OrderType.SELL,
                    quantity=self.trade_quantity,
                    price=int(current_price),  # 현재가를 정수로 변환
                    price_type=OrderPriceType.MARKET,
                )

                logger.info(
                    f"📋 주문 요청 생성 완료: {order_request.symbol} {order_request.order_type.value} {order_request.quantity}주 @ {int(order_request.price)}원"
                )
                result = self.order_executor.place_order(order_request)

                if result and result.status.value in [
                    "접수완료",
                    "ACCEPTED",
                    "전체체결",
                    "FILLED",
                ]:
                    logger.info(
                        f"✅ 매도 주문 성공 (실제): {signal.symbol} {self.trade_quantity}주 @ {int(current_price)}원"
                    )
                    logger.info(
                        f"주문 상태: {result.status.value}, 주문 ID: {result.order_id}"
                    )
                    return True
                else:
                    error_msg = f"매도 주문 실패: {signal.symbol} - {result.status.value if result else '주문 실패'}"
                    logger.error(f"❌ {error_msg}")
                    self.record_error(error_msg)
                    return False

        except Exception as e:
            logger.error(f"매도 주문 실행 오류: {e}")
            return False

    def _reset_daily_order_count(self):
        """일일 주문 수 리셋 (날짜가 바뀌었을 때만 자동 리셋)"""
        current_date = datetime.now().date()
        if self.last_order_reset != current_date:
            self.daily_order_count_test = 0
            self.daily_order_count_real = 0
            self.last_order_reset = current_date
            logger.info(
                f"일일 주문 수 자동 리셋됨 (날짜 변경: {self.last_order_reset} → {current_date})"
            )

    def _force_reset_daily_order_count(self):
        """일일 주문 수 강제 리셋 (버튼 클릭 시 사용)"""
        self.daily_order_count_test = 0
        self.daily_order_count_real = 0
        self.last_order_reset = datetime.now().date()
        logger.info("일일 주문 수 강제 리셋됨 (테스트 모드 및 실제 매매 모두)")

    def set_test_mode(self, test_mode: bool):
        """매매 모드 설정"""
        self.test_mode = test_mode
        mode_text = "테스트 모드" if test_mode else "실제 매매"
        logger.info(f"매매 모드 변경: {mode_text}")

    def is_test_mode(self) -> bool:
        """테스트 모드 여부 확인"""
        return self.test_mode

    def get_status(self) -> Dict[str, Any]:
        """자동매매 상태 조회"""
        return {
            "is_running": self.is_running,
            "test_mode": self.test_mode,
            "daily_order_count_test": self.daily_order_count_test,
            "daily_order_count_real": self.daily_order_count_real,
            "max_daily_orders_test": self.max_daily_orders_test,
            "max_daily_orders_real": self.max_daily_orders_real,
            "active_symbols_count": len(self.watchlist_manager.get_active_symbols()),
            "active_conditions_count": len(
                self.condition_manager.get_conditions(active_only=True)
            ),
            "order_cooldown": self.order_cooldown,
            "last_order_reset": self.last_order_reset.isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

    def set_order_cooldown(self, minutes: int):
        """주문 쿨다운 시간 설정 (분 단위)"""
        if minutes < 0:
            raise ValueError("쿨다운 시간은 0 이상이어야 합니다.")

        old_cooldown = self.order_cooldown
        self.order_cooldown = minutes * 60  # 분을 초로 변환
        logger.info(f"주문 쿨다운 시간 변경: {old_cooldown//60}분 → {minutes}분")
        return {
            "old_cooldown_minutes": old_cooldown // 60,
            "new_cooldown_minutes": minutes,
            "new_cooldown_seconds": self.order_cooldown,
        }

    def get_order_cooldown_minutes(self) -> int:
        """주문 쿨다운 시간 조회 (분 단위)"""
        return self.order_cooldown // 60

    def record_error(self, error_message: str):
        """에러 기록"""
        self.last_error = error_message
        self.error_timestamp = datetime.now()
        logger.error(f"자동매매 에러 기록: {error_message}")

    def clear_error(self):
        """에러 초기화"""
        self.last_error = None
        self.error_timestamp = None

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """마지막 에러 정보 조회"""
        if self.last_error and self.error_timestamp:
            return {
                "message": self.last_error,
                "timestamp": self.error_timestamp.isoformat(),
                "age_minutes": int(
                    (datetime.now() - self.error_timestamp).total_seconds() / 60
                ),
            }
        return None
