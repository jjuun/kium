"""
RiskManager 단위 테스트
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.trading.risk_manager import RiskManager


class TestRiskManager:
    @pytest.fixture
    def risk_manager(self):
        """RiskManager 인스턴스 fixture"""
        return RiskManager()

    @pytest.fixture
    def sample_position(self):
        """샘플 포지션 데이터 fixture"""
        return {
            "symbol": "005935",
            "quantity": 10,
            "entry_price": 50000,
            "entry_time": datetime.now(),
            "current_price": 52000
        }

    @pytest.fixture
    def sample_order(self):
        """샘플 주문 데이터 fixture"""
        return {
            "symbol": "005935",
            "quantity": 5,
            "price": 52000,
            "order_type": "buy"
        }

    @pytest.fixture
    def current_positions(self):
        """현재 포지션 목록 fixture"""
        return {
            "005935": {
                "quantity": 10,
                "entry_price": 50000,
                "entry_time": datetime.now()
            },
            "000660": {
                "quantity": 5,
                "entry_price": 80000,
                "entry_time": datetime.now()
            }
        }

    def test_risk_manager_initialization(self, risk_manager):
        """RiskManager 초기화 테스트"""
        # Then
        assert risk_manager is not None
        assert hasattr(risk_manager, "max_position_size")
        assert hasattr(risk_manager, "stop_loss_percent")
        assert hasattr(risk_manager, "take_profit_percent")
        assert hasattr(risk_manager, "positions")
        assert hasattr(risk_manager, "trade_history")

    def test_calculate_position_size(self, risk_manager):
        """포지션 크기 계산 테스트"""
        # Given
        current_price = 50000
        available_capital = 1000000

        # When
        quantity, actual_size = risk_manager.calculate_position_size(current_price, available_capital)

        # Then
        assert quantity > 0
        assert actual_size > 0
        assert actual_size == quantity * current_price

    def test_calculate_position_size_minimum(self, risk_manager):
        """최소 포지션 크기 계산 테스트"""
        # Given
        current_price = 1000000  # 매우 높은 가격
        available_capital = 500000  # 제한된 자본

        # When
        quantity, actual_size = risk_manager.calculate_position_size(current_price, available_capital)

        # Then
        assert quantity >= 1  # 최소 1주
        assert actual_size > 0

    def test_check_stop_loss(self, risk_manager, sample_position):
        """손절 조건 확인 테스트"""
        # Given
        symbol = "005935"
        risk_manager.positions[symbol] = {
            "quantity": sample_position["quantity"],
            "entry_price": sample_position["entry_price"],
            "entry_time": sample_position["entry_time"]
        }
        
        # 손절 조건을 만족하는 현재 가격 (20% 하락)
        current_price = 40000

        # When
        should_stop, stop_info = risk_manager.check_stop_loss(symbol, current_price)

        # Then
        assert should_stop is True
        assert stop_info is not None
        assert stop_info["action"] == "STOP_LOSS"
        assert stop_info["symbol"] == symbol

    def test_check_stop_loss_no_position(self, risk_manager):
        """포지션이 없는 경우 손절 확인 테스트"""
        # Given
        symbol = "005935"
        current_price = 40000

        # When
        should_stop, stop_info = risk_manager.check_stop_loss(symbol, current_price)

        # Then
        assert should_stop is False
        assert stop_info is None

    def test_check_take_profit(self, risk_manager, sample_position):
        """익절 조건 확인 테스트"""
        # Given
        symbol = "005935"
        risk_manager.positions[symbol] = {
            "quantity": sample_position["quantity"],
            "entry_price": sample_position["entry_price"],
            "entry_time": sample_position["entry_time"]
        }
        
        # 익절 조건을 만족하는 현재 가격 (20% 상승)
        current_price = 60000

        # When
        should_take, take_info = risk_manager.check_take_profit(symbol, current_price)

        # Then
        assert should_take is True
        assert take_info is not None
        assert take_info["action"] == "TAKE_PROFIT"
        assert take_info["symbol"] == symbol

    def test_check_take_profit_no_position(self, risk_manager):
        """포지션이 없는 경우 익절 확인 테스트"""
        # Given
        symbol = "005935"
        current_price = 60000

        # When
        should_take, take_info = risk_manager.check_take_profit(symbol, current_price)

        # Then
        assert should_take is False
        assert take_info is None

    def test_add_position(self, risk_manager):
        """포지션 추가 테스트"""
        # Given
        symbol = "005935"
        quantity = 10
        price = 50000

        # When
        risk_manager.add_position(symbol, quantity, price)

        # Then
        assert symbol in risk_manager.positions
        position = risk_manager.positions[symbol]
        assert position["quantity"] == quantity
        assert position["entry_price"] == price
        assert "entry_time" in position

    def test_remove_position(self, risk_manager):
        """포지션 제거 테스트"""
        # Given
        symbol = "005935"
        quantity = 10
        entry_price = 50000
        exit_price = 52000
        
        risk_manager.add_position(symbol, quantity, entry_price)

        # When
        risk_manager.remove_position(symbol, exit_price)

        # Then
        assert symbol not in risk_manager.positions
        assert len(risk_manager.trade_history) > 0

    def test_get_portfolio_summary(self, risk_manager):
        """포트폴리오 요약 테스트"""
        # Given
        risk_manager.add_position("005935", 10, 50000)
        risk_manager.add_position("000660", 5, 80000)

        # When
        summary = risk_manager.get_portfolio_summary()

        # Then
        assert summary is not None
        assert "total_positions" in summary
        assert "total_value" in summary
        assert "total_pnl" in summary
        assert "total_pnl_percent" in summary
        assert "total_trades" in summary
        assert "winning_trades" in summary
        assert "losing_trades" in summary
        assert summary["total_positions"] == 2

    def test_check_risk_limits(self, risk_manager):
        """리스크 한도 확인 테스트"""
        # Given
        symbol = "005935"
        quantity = 10
        price = 50000

        # When
        is_valid, message = risk_manager.check_risk_limits(symbol, quantity, price)

        # Then
        assert isinstance(is_valid, bool)
        assert isinstance(message, str)

    def test_get_position_info(self, risk_manager):
        """포지션 정보 조회 테스트"""
        # Given
        symbol = "005935"
        quantity = 10
        price = 50000
        risk_manager.add_position(symbol, quantity, price)

        # When
        position_info = risk_manager.get_position_info(symbol)

        # Then
        assert position_info is not None
        assert position_info["quantity"] == quantity
        assert position_info["entry_price"] == price

    def test_get_position_info_not_found(self, risk_manager):
        """존재하지 않는 포지션 정보 조회 테스트"""
        # Given
        symbol = "INVALID"

        # When
        position_info = risk_manager.get_position_info(symbol)

        # Then
        assert position_info is None

    def test_get_all_positions(self, risk_manager):
        """모든 포지션 조회 테스트"""
        # Given
        risk_manager.add_position("005935", 10, 50000)
        risk_manager.add_position("000660", 5, 80000)

        # When
        positions = risk_manager.get_all_positions()

        # Then
        assert isinstance(positions, dict)
        assert len(positions) == 2
        assert "005935" in positions
        assert "000660" in positions

    def test_get_trade_history(self, risk_manager):
        """거래 이력 조회 테스트"""
        # Given
        symbol = "005935"
        risk_manager.add_position(symbol, 10, 50000)
        risk_manager.remove_position(symbol, 52000)

        # When
        history = risk_manager.get_trade_history()

        # Then
        assert isinstance(history, list)
        assert len(history) > 0

    def test_get_trade_history_by_symbol(self, risk_manager):
        """특정 종목 거래 이력 조회 테스트"""
        # Given
        symbol = "005935"
        risk_manager.add_position(symbol, 10, 50000)
        risk_manager.remove_position(symbol, 52000)

        # When
        history = risk_manager.get_trade_history(symbol=symbol)

        # Then
        assert isinstance(history, list)
        assert len(history) > 0
        for trade in history:
            assert trade["symbol"] == symbol
