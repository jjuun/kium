"""
TradingStrategy 단위 테스트
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.trading.trading_strategy import TradingStrategy


class TestTradingStrategy:
    @pytest.fixture
    def trading_strategy(self):
        """TradingStrategy 인스턴스 fixture"""
        return TradingStrategy()

    @pytest.fixture
    def sample_market_data(self):
        """샘플 시장 데이터 fixture (충분한 데이터 포인트 포함)"""
        dates = pd.date_range(start="2025-06-01", end="2025-07-22", freq="D")
        data = pd.DataFrame({
            "시가": [49500] * 52,
            "고가": [51500] * 52,
            "저가": [49000] * 52,
            "종가": [50000 + i * 100 for i in range(52)],
            "거래량": [1000000 + i * 10000 for i in range(52)],
            "SMA_5": [50000 + i * 100 for i in range(52)],
            "SMA_20": [48000 + i * 100 for i in range(52)],
            "RSI": [45 + i for i in range(52)],
            "MACD": [100 + i * 2 for i in range(52)],
            "MACD_Signal": [90 + i * 2 for i in range(52)],
            "MACD_Histogram": [10] * 52,
            "BB_Middle": [50000 + i * 100 for i in range(52)],
            "BB_Upper": [52000 + i * 100 for i in range(52)],
            "BB_Lower": [48000 + i * 100 for i in range(52)],
            "Volume_SMA": [1000000 + i * 10000 for i in range(52)]
        }, index=dates)
        return data

    def test_trading_strategy_initialization(self, trading_strategy):
        """TradingStrategy 초기화 테스트"""
        # Then
        assert trading_strategy is not None
        assert hasattr(trading_strategy, "strategy_name")
        assert hasattr(trading_strategy, "short_period")
        assert hasattr(trading_strategy, "long_period")

    def test_sma_crossover_strategy_buy_signal(self, trading_strategy, sample_market_data):
        """SMA 교차 전략 매수 신호 테스트"""
        # Given - 매수 신호 조건 설정
        # 마지막 두 행을 수정하여 매수 신호 생성
        sample_market_data.iloc[-2, 5] = 53000  # 이전 SMA_5
        sample_market_data.iloc[-2, 6] = 53000  # 이전 SMA_20
        sample_market_data.iloc[-1, 5] = 53500  # 현재 SMA_5 (상향 돌파)
        sample_market_data.iloc[-1, 6] = 53000  # 현재 SMA_20
        sample_market_data.iloc[-1, 7] = 25     # RSI 과매도
        sample_market_data.iloc[-1, 8] = 180    # MACD
        sample_market_data.iloc[-1, 9] = 160    # MACD_Signal (MACD > Signal)

        # When
        signal = trading_strategy.sma_crossover_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["confidence"] > 0

    def test_sma_crossover_strategy_sell_signal(self, trading_strategy, sample_market_data):
        """SMA 교차 전략 매도 신호 테스트"""
        # Given - 매도 신호 조건 설정
        # 마지막 두 행을 수정하여 매도 신호 생성
        sample_market_data.iloc[-2, 5] = 53500  # 이전 SMA_5
        sample_market_data.iloc[-2, 6] = 53000  # 이전 SMA_20
        sample_market_data.iloc[-1, 5] = 52500  # 현재 SMA_5 (하향 돌파)
        sample_market_data.iloc[-1, 6] = 53000  # 현재 SMA_20
        sample_market_data.iloc[-1, 7] = 75     # RSI 과매수
        sample_market_data.iloc[-1, 8] = 160    # MACD
        sample_market_data.iloc[-1, 9] = 170    # MACD_Signal (MACD < Signal)

        # When
        signal = trading_strategy.sma_crossover_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "SELL"
        assert signal["confidence"] > 0

    def test_sma_crossover_strategy_no_signal(self, trading_strategy, sample_market_data):
        """SMA 교차 전략 신호 없음 테스트"""
        # Given - 신호가 없는 조건 설정
        sample_market_data.iloc[-1, 5] = 53000  # SMA_5
        sample_market_data.iloc[-1, 6] = 53000  # SMA_20 (교차 없음)

        # When
        signal = trading_strategy.sma_crossover_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "HOLD"

    def test_rsi_strategy_oversold_buy(self, trading_strategy, sample_market_data):
        """RSI 전략 과매도 매수 테스트"""
        # Given - RSI 과매도 조건
        sample_market_data.iloc[-1, 7] = 25  # RSI 25 (과매도)

        # When
        signal = trading_strategy.rsi_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["confidence"] > 0

    def test_rsi_strategy_overbought_sell(self, trading_strategy, sample_market_data):
        """RSI 전략 과매수 매도 테스트"""
        # Given - RSI 과매수 조건
        sample_market_data.iloc[-1, 7] = 75  # RSI 75 (과매수)

        # When
        signal = trading_strategy.rsi_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "SELL"
        assert signal["confidence"] > 0

    def test_rsi_strategy_no_signal(self, trading_strategy, sample_market_data):
        """RSI 전략 신호 없음 테스트"""
        # Given - RSI 중립 조건
        sample_market_data.iloc[-1, 7] = 50  # RSI 50 (중립)

        # When
        signal = trading_strategy.rsi_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "HOLD"

    def test_macd_strategy_bullish_signal(self, trading_strategy, sample_market_data):
        """MACD 전략 상승 신호 테스트"""
        # Given - MACD 상향 돌파 조건
        sample_market_data.iloc[-2, 8] = 160  # 이전 MACD
        sample_market_data.iloc[-2, 9] = 170  # 이전 MACD_Signal (MACD <= Signal)
        sample_market_data.iloc[-1, 8] = 180  # 현재 MACD
        sample_market_data.iloc[-1, 9] = 160  # 현재 MACD_Signal (MACD > Signal)

        # When
        signal = trading_strategy.macd_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "BUY"
        assert signal["confidence"] > 0

    def test_macd_strategy_bearish_signal(self, trading_strategy, sample_market_data):
        """MACD 전략 하락 신호 테스트"""
        # Given - MACD 하락 신호 조건
        sample_market_data.iloc[-1, 8] = 160  # MACD
        sample_market_data.iloc[-1, 9] = 180  # MACD_Signal (MACD < Signal)

        # When
        signal = trading_strategy.macd_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert signal["action"] == "SELL"
        assert signal["confidence"] > 0

    def test_bollinger_bands_strategy(self, trading_strategy, sample_market_data):
        """볼린저 밴드 전략 테스트"""
        # Given - 볼린저 밴드 하단 터치 조건
        sample_market_data.iloc[-1, 2] = 53000  # 저가를 BB_Lower 근처로 설정

        # When
        signal = trading_strategy.bollinger_bands_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert "action" in signal
        assert "confidence" in signal

    def test_combined_strategy(self, trading_strategy, sample_market_data):
        """복합 전략 테스트"""
        # Given - 복합 신호 조건 설정
        sample_market_data.iloc[-1, 5] = 53500  # SMA_5
        sample_market_data.iloc[-1, 6] = 53000  # SMA_20
        sample_market_data.iloc[-1, 7] = 25     # RSI 과매도
        sample_market_data.iloc[-1, 8] = 180    # MACD
        sample_market_data.iloc[-1, 9] = 160    # MACD_Signal

        # When
        signal = trading_strategy.combined_strategy(sample_market_data)

        # Then
        assert signal is not None
        assert "action" in signal
        assert "confidence" in signal
        assert "reason" in signal

    def test_generate_signal(self, trading_strategy, sample_market_data):
        """신호 생성 테스트"""
        # When
        signal = trading_strategy.generate_signal(sample_market_data)

        # Then
        assert signal is not None
        assert "action" in signal
        assert "confidence" in signal
        assert "price" in signal
        assert "timestamp" in signal

    def test_strategy_with_insufficient_data(self, trading_strategy):
        """부족한 데이터로 전략 실행 테스트"""
        # Given - 부족한 데이터
        insufficient_data = pd.DataFrame({
            "종가": [50000, 51000],
            "SMA_5": [50000, 50500],
            "SMA_20": [48000, 48500]
        })

        # When
        signal = trading_strategy.sma_crossover_strategy(insufficient_data)

        # Then
        assert signal is None

    def test_strategy_with_none_data(self, trading_strategy):
        """None 데이터로 전략 실행 테스트"""
        # When
        signal = trading_strategy.sma_crossover_strategy(None)

        # Then
        assert signal is None

    def test_strategy_with_empty_data(self, trading_strategy):
        """빈 데이터로 전략 실행 테스트"""
        # Given
        empty_data = pd.DataFrame()

        # When
        signal = trading_strategy.sma_crossover_strategy(empty_data)

        # Then
        assert signal is None

    def test_signal_structure(self, trading_strategy, sample_market_data):
        """신호 구조 테스트"""
        # When
        signal = trading_strategy.generate_signal(sample_market_data)

        # Then
        required_fields = ["action", "confidence", "price", "timestamp", "reason"]
        for field in required_fields:
            assert field in signal

        # 값 타입 확인
        assert signal["action"] in ["BUY", "SELL", "HOLD"]
        assert 0 <= signal["confidence"] <= 1
        assert isinstance(signal["price"], (int, float, np.integer, np.floating))
        assert isinstance(signal["timestamp"], datetime)
        assert isinstance(signal["reason"], list)
