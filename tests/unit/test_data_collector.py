"""
DataCollector 단위 테스트
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.data_collector import DataCollector


class TestDataCollector:
    @pytest.fixture
    def data_collector(self):
        """DataCollector 인스턴스 fixture"""
        return DataCollector()

    @pytest.fixture
    def sample_stock_data(self):
        """샘플 주식 데이터 fixture (yfinance 형식)"""
        dates = pd.date_range(start="2025-07-15", end="2025-07-22", freq="D")
        data = pd.DataFrame({
            "Open": [49500, 50500, 51500, 52500, 53500, 53000, 54000, 54500],
            "High": [51500, 52500, 53500, 54500, 55500, 55000, 56000, 56500],
            "Low": [49000, 50000, 51000, 52000, 53000, 52500, 53500, 54000],
            "Close": [50000, 51000, 52000, 53000, 54000, 53500, 54500, 55000],
            "Volume": [1000000, 1200000, 1100000, 1300000, 1400000, 1250000, 1350000, 1450000],
            "Dividends": [0, 0, 0, 0, 0, 0, 0, 0],
            "Stock Splits": [0, 0, 0, 0, 0, 0, 0, 0]
        }, index=dates)
        return data

    def test_data_collector_initialization(self, data_collector):
        """DataCollector 초기화 테스트"""
        # Then
        assert data_collector is not None
        assert hasattr(data_collector, "symbol")
        assert hasattr(data_collector, "interval")
        assert hasattr(data_collector, "history_days")

    @patch('yfinance.Ticker')
    def test_get_historical_data(self, mock_ticker, data_collector, sample_stock_data):
        """과거 데이터 수집 테스트"""
        # Given
        symbol = "005935"
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = sample_stock_data
        mock_ticker.return_value = mock_ticker_instance

        # When
        result = data_collector.get_historical_data(symbol, 30)

        # Then
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "종가" in result.columns
        assert "시가" in result.columns
        assert "고가" in result.columns
        assert "저가" in result.columns
        assert "거래량" in result.columns

    @patch('yfinance.Ticker')
    def test_get_realtime_price(self, mock_ticker, data_collector):
        """실시간 가격 조회 테스트"""
        # Given
        symbol = "005935"
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            "regularMarketPrice": 55000,
            "previousClose": 54000
        }
        mock_ticker.return_value = mock_ticker_instance

        # When
        result = data_collector.get_realtime_price(symbol)

        # Then
        assert result is not None
        assert "symbol" in result
        assert "current_price" in result
        assert "previous_close" in result
        assert "change" in result
        assert "change_percent" in result
        assert "timestamp" in result
        assert result["symbol"] == symbol
        assert result["current_price"] == 55000

    @patch('yfinance.Ticker')
    def test_get_realtime_price_error(self, mock_ticker, data_collector):
        """실시간 가격 조회 오류 테스트"""
        # Given
        symbol = "INVALID"
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {}
        mock_ticker.return_value = mock_ticker_instance

        # When
        result = data_collector.get_realtime_price(symbol)

        # Then
        assert result is not None
        assert result["current_price"] == 0
        assert result["previous_close"] == 0

    def test_calculate_technical_indicators(self, data_collector, sample_stock_data):
        """기술적 지표 계산 테스트"""
        # Given - 한글 컬럼명으로 변환된 데이터
        korean_data = sample_stock_data.copy()
        korean_data.columns = ["시가", "고가", "저가", "종가", "거래량", "Dividends", "Stock Splits"]
        korean_data = korean_data[["시가", "고가", "저가", "종가", "거래량"]]

        # When
        result = data_collector.calculate_technical_indicators(korean_data)

        # Then
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        
        # 기술적 지표 컬럼 확인
        expected_indicators = ["SMA_5", "SMA_20", "RSI", "MACD", "MACD_Signal", "MACD_Histogram", "BB_Middle", "BB_Upper", "BB_Lower", "Volume_SMA"]
        for indicator in expected_indicators:
            assert indicator in result.columns

    @patch('yfinance.Ticker')
    def test_get_market_data(self, mock_ticker, data_collector):
        """시장 데이터 조회 테스트"""
        # Given
        symbol = "005935"
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            "marketCap": 1000000000000,
            "volume": 1500000,
            "averageVolume": 1400000,
            "trailingPE": 15.5,
            "priceToBook": 1.2,
            "dividendYield": 2.5
        }
        mock_ticker.return_value = mock_ticker_instance

        # When
        result = data_collector.get_market_data(symbol)

        # Then
        assert result is not None
        assert "symbol" in result
        assert "market_cap" in result
        assert "volume" in result
        assert "avg_volume" in result
        assert "pe_ratio" in result
        assert "pb_ratio" in result
        assert "dividend_yield" in result
        assert "timestamp" in result
        assert result["symbol"] == symbol

    @patch('yfinance.Ticker')
    def test_symbol_validation(self, mock_ticker, data_collector, sample_stock_data):
        """종목코드 검증 테스트"""
        # Given
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = sample_stock_data
        mock_ticker.return_value = mock_ticker_instance

        # When & Then
        result1 = data_collector.get_historical_data("005935")
        result2 = data_collector.get_historical_data("A005935")  # 우선주
        result3 = data_collector.get_historical_data("AAPL")  # 해외주

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None

    @patch('yfinance.Ticker')
    def test_get_data_with_cache(self, mock_ticker, data_collector, sample_stock_data):
        """캐시를 사용한 데이터 조회 테스트"""
        # Given
        symbol = "005935"
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = sample_stock_data
        mock_ticker.return_value = mock_ticker_instance

        # When - 첫 번째 호출
        result1 = data_collector.get_historical_data(symbol, 30)
        
        # When - 두 번째 호출 (캐시 사용)
        result2 = data_collector.get_historical_data(symbol, 30)

        # Then
        assert result1 is not None
        assert result2 is not None
        assert len(result1) == len(result2)
