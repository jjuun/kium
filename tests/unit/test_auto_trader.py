"""
AutoTrader 단위 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.auto_trading.auto_trader import AutoTrader
from src.auto_trading.watchlist_manager import WatchlistManager
from src.auto_trading.condition_manager import ConditionManager
from src.auto_trading.signal_monitor import SignalMonitor


class TestAutoTrader:
    """AutoTrader 클래스 테스트"""

    @pytest.fixture
    def auto_trader(self, test_db_path):
        """AutoTrader 인스턴스 fixture"""
        return AutoTrader(db_path=test_db_path)

    @pytest.fixture
    def mock_data_collector(self):
        """데이터 수집기 모킹"""
        with patch("src.auto_trading.auto_trader.DataCollector") as mock:
            instance = mock.return_value
            instance.get_historical_data.return_value = None
            instance.get_real_time_price.return_value = 50000
            yield instance

    @pytest.fixture
    def mock_trading_strategy(self):
        """거래 전략 모킹"""
        with patch("src.auto_trading.auto_trader.TradingStrategy") as mock:
            instance = mock.return_value
            instance.generate_signal.return_value = None
            yield instance

    def test_auto_trader_initialization(self, auto_trader):
        """AutoTrader 초기화 테스트"""
        # Then
        assert auto_trader is not None
        assert auto_trader.is_running is False
        assert auto_trader.trade_quantity == 1
        assert auto_trader.order_cooldown == 60  # 1분 (실제 기본값)
        assert auto_trader.daily_order_count_real == 0
        assert auto_trader.daily_order_count_test == 0

    def test_set_trade_quantity(self, auto_trader):
        """매매 수량 설정 테스트"""
        # Given
        quantity = 5

        # When
        auto_trader.trade_quantity = quantity

        # Then
        assert auto_trader.trade_quantity == quantity

    def test_set_order_cooldown(self, auto_trader):
        """주문 쿨다운 설정 테스트"""
        # Given
        cooldown = 600  # 10분

        # When
        auto_trader.order_cooldown = cooldown

        # Then
        assert auto_trader.order_cooldown == cooldown

    @pytest.mark.asyncio
    async def test_start_auto_trading(self, auto_trader):
        """자동매매 시작 테스트"""
        # Given
        quantity = 5

        # When
        result = auto_trader.start(quantity)

        # Then
        assert result is True
        assert auto_trader.is_running is True
        assert auto_trader.trade_quantity == quantity

    @pytest.mark.asyncio
    async def test_stop_auto_trading(self, auto_trader):
        """자동매매 중지 테스트"""
        # Given
        auto_trader.start()

        # When
        result = auto_trader.stop()

        # Then
        assert result is True
        assert auto_trader.is_running is False

    def test_add_watchlist_symbol(self, auto_trader):
        """감시종목 추가 테스트"""
        # Given
        symbol = "005935"
        name = "삼성전자"

        # When
        result = auto_trader.watchlist_manager.add_symbol(symbol, name)

        # Then
        assert result is True

        # 감시종목 목록 확인
        symbols = auto_trader.watchlist_manager.get_active_symbols()
        assert symbol in symbols

    def test_remove_watchlist_symbol(self, auto_trader):
        """감시종목 제거 테스트"""
        # Given
        symbol = "005935"
        name = "삼성전자"
        auto_trader.watchlist_manager.add_symbol(symbol, name)

        # When
        result = auto_trader.watchlist_manager.remove_symbol(symbol)

        # Then
        assert result is True

        # 감시종목 목록 확인
        symbols = auto_trader.watchlist_manager.get_active_symbols()
        assert symbol not in symbols

    def test_add_trading_condition(self, auto_trader):
        """거래 조건 추가 테스트"""
        # Given
        symbol = "005935"
        condition_type = "buy"
        category = "rsi"
        value = "RSI < 30"

        # When
        result = auto_trader.condition_manager.add_condition(
            symbol, condition_type, category, value
        )

        # Then
        assert result is True

        # 조건 목록 확인
        conditions = auto_trader.condition_manager.get_conditions(symbol)
        assert len(conditions) == 1
        assert conditions[0].value == value

    def test_remove_trading_condition(self, auto_trader):
        """거래 조건 제거 테스트"""
        # Given
        symbol = "005935"
        condition_type = "buy"
        category = "rsi"
        value = "RSI < 30"

        # 조건 추가
        auto_trader.condition_manager.add_condition(
            symbol, condition_type, category, value
        )

        # 조건 ID 가져오기
        conditions = auto_trader.condition_manager.get_conditions(symbol)
        condition_id = conditions[0].id

        # When
        result = auto_trader.condition_manager.remove_condition(condition_id)

        # Then
        assert result is True

        # 조건 목록 확인
        conditions = auto_trader.condition_manager.get_conditions(symbol)
        assert len(conditions) == 0

    def test_get_auto_trading_status(self, auto_trader):
        """자동매매 상태 조회 테스트"""
        # When
        status = auto_trader.get_status()

        # Then
        assert "is_running" in status
        assert "active_symbols_count" in status
        assert "active_conditions_count" in status
        assert "daily_order_count_real" in status
        assert "daily_order_count_test" in status
        assert status["is_running"] is False

    @pytest.mark.asyncio
    async def test_risk_management_check(self, auto_trader):
        """리스크 관리 체크 테스트"""
        # Given
        from src.auto_trading.auto_trader import TradingSignal

        signal = TradingSignal(
            symbol="005935",
            signal_type="buy",
            condition_id=1,
            condition_value="RSI < 30",
            current_price=50000,
            timestamp=datetime.now(),
        )

        # When
        result = auto_trader._check_risk_management(signal)

        # Then
        assert result is True

    @pytest.mark.asyncio
    async def test_daily_order_limit_exceeded(self, auto_trader):
        """일일 주문 수 제한 초과 테스트"""
        # Given
        auto_trader.daily_order_count_real = 10  # 최대치
        from src.auto_trading.auto_trader import TradingSignal

        signal = TradingSignal(
            symbol="005935",
            signal_type="buy",
            condition_id=1,
            condition_value="RSI < 30",
            current_price=50000,
            timestamp=datetime.now(),
        )

        # When
        result = auto_trader._check_risk_management(signal)

        # Then
        assert result is False

    def test_force_reset_daily_order_count(self, auto_trader):
        """일일 주문 수 강제 리셋 테스트"""
        # Given
        auto_trader.daily_order_count_real = 5
        auto_trader.daily_order_count_test = 3

        # When
        auto_trader._force_reset_daily_order_count()

        # Then
        assert auto_trader.daily_order_count_real == 0
        assert auto_trader.daily_order_count_test == 0

    def test_set_order_cooldown(self, auto_trader):
        """주문 쿨다운 설정 테스트"""
        # Given
        cooldown_minutes = 10

        # When
        auto_trader.set_order_cooldown(cooldown_minutes)

        # Then
        assert auto_trader.order_cooldown == cooldown_minutes * 60  # 분을 초로 변환

    def test_get_order_cooldown_minutes(self, auto_trader):
        """주문 쿨다운 조회 테스트"""
        # Given
        auto_trader.order_cooldown = 300  # 5분

        # When
        minutes = auto_trader.get_order_cooldown_minutes()

        # Then
        assert minutes == 5
