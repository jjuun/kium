"""
DataCollector 단위 테스트
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.core.data_collector import DataCollector


class TestDataCollector:
    """DataCollector 클래스 테스트"""
    
    @pytest.fixture
    def data_collector(self):
        """DataCollector 인스턴스 fixture"""
        return DataCollector()
    
    @pytest.fixture
    def sample_stock_data(self):
        """샘플 주식 데이터"""
        dates = pd.date_range(start='2025-07-15', end='2025-07-22', freq='D')
        return pd.DataFrame({
            '종가': [50000, 51000, 52000, 53000, 54000, 53500, 54500, 55000],
            '시가': [49500, 50500, 51500, 52500, 53500, 53000, 54000, 54500],
            '고가': [51500, 52500, 53500, 54500, 55500, 55000, 56000, 56500],
            '저가': [49000, 50000, 51000, 52000, 53000, 52500, 53500, 54000],
            '거래량': [1000000, 1100000, 1200000, 1300000, 1400000, 1350000, 1450000, 1500000]
        }, index=dates)
    
    def test_data_collector_initialization(self, data_collector):
        """DataCollector 초기화 테스트"""
        # Then
        assert data_collector is not None
        assert hasattr(data_collector, 'kiwoom_api')
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, data_collector, sample_stock_data):
        """과거 데이터 수집 테스트"""
        # Given
        symbol = "005935"
        days = 30
        
        with patch.object(data_collector.kiwoom_api, 'get_historical_data') as mock_get_data:
            mock_get_data.return_value = sample_stock_data
            
            # When
            result = await data_collector.get_historical_data(symbol, days)
            
            # Then
            assert result is not None
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 8  # 샘플 데이터 길이
            assert '종가' in result.columns
            assert '시가' in result.columns
            assert '고가' in result.columns
            assert '저가' in result.columns
            assert '거래량' in result.columns
    
    @pytest.mark.asyncio
    async def test_get_real_time_price(self, data_collector):
        """실시간 가격 조회 테스트"""
        # Given
        symbol = "005935"
        expected_price = 50000
        
        with patch.object(data_collector.kiwoom_api, 'get_stock_price') as mock_get_price:
            mock_get_price.return_value = {
                'output': [{'prpr': str(expected_price)}]
            }
            
            # When
            result = await data_collector.get_real_time_price(symbol)
            
            # Then
            assert result == expected_price
    
    @pytest.mark.asyncio
    async def test_get_real_time_price_error(self, data_collector):
        """실시간 가격 조회 오류 테스트"""
        # Given
        symbol = "005935"
        
        with patch.object(data_collector.kiwoom_api, 'get_stock_price') as mock_get_price:
            mock_get_price.side_effect = Exception("API 오류")
            
            # When
            result = await data_collector.get_real_time_price(symbol)
            
            # Then
            assert result is None
    
    @pytest.mark.asyncio
    async def test_calculate_technical_indicators(self, data_collector, sample_stock_data):
        """기술적 지표 계산 테스트"""
        # When
        result = data_collector.calculate_technical_indicators(sample_stock_data)
        
        # Then
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_stock_data)
        
        # 기술적 지표 컬럼 확인
        expected_indicators = ['SMA_5', 'SMA_20', 'RSI', 'MACD', 'MACD_signal']
        for indicator in expected_indicators:
            assert indicator in result.columns
    
    def test_calculate_sma(self, data_collector, sample_stock_data):
        """이동평균선 계산 테스트"""
        # When
        sma_5 = data_collector._calculate_sma(sample_stock_data['종가'], 5)
        sma_20 = data_collector._calculate_sma(sample_stock_data['종가'], 20)
        
        # Then
        assert len(sma_5) == len(sample_stock_data)
        assert len(sma_20) == len(sample_stock_data)
        
        # NaN 값 확인 (첫 4개는 NaN이어야 함)
        assert pd.isna(sma_5.iloc[0])
        assert pd.isna(sma_5.iloc[3])
        assert not pd.isna(sma_5.iloc[4])  # 5일째부터 값이 있어야 함
    
    def test_calculate_rsi(self, data_collector, sample_stock_data):
        """RSI 계산 테스트"""
        # When
        rsi = data_collector._calculate_rsi(sample_stock_data['종가'], 14)
        
        # Then
        assert len(rsi) == len(sample_stock_data)
        
        # RSI는 0-100 사이의 값이어야 함
        valid_rsi = rsi.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)
    
    def test_calculate_macd(self, data_collector, sample_stock_data):
        """MACD 계산 테스트"""
        # When
        macd, signal = data_collector._calculate_macd(sample_stock_data['종가'])
        
        # Then
        assert len(macd) == len(sample_stock_data)
        assert len(signal) == len(sample_stock_data)
        
        # MACD와 시그널은 같은 길이여야 함
        assert len(macd) == len(signal)
    
    @pytest.mark.asyncio
    async def test_get_market_data(self, data_collector, sample_stock_data):
        """시장 데이터 조회 테스트"""
        # Given
        symbol = "005935"
        
        with patch.object(data_collector, 'get_historical_data') as mock_historical:
            with patch.object(data_collector, 'get_real_time_price') as mock_realtime:
                mock_historical.return_value = sample_stock_data
                mock_realtime.return_value = 55000
                
                # When
                historical, current_price = await data_collector.get_market_data(symbol)
                
                # Then
                assert historical is not None
                assert current_price == 55000
                assert isinstance(historical, pd.DataFrame)
    
    def test_validate_symbol(self, data_collector):
        """심볼 유효성 검사 테스트"""
        # Valid symbols
        assert data_collector._validate_symbol("005935") is True
        assert data_collector._validate_symbol("A005935") is True
        
        # Invalid symbols
        assert data_collector._validate_symbol("") is False
        assert data_collector._validate_symbol("123") is False
        assert data_collector._validate_symbol("INVALID") is False
    
    @pytest.mark.asyncio
    async def test_get_data_with_cache(self, data_collector, sample_stock_data):
        """캐시를 사용한 데이터 조회 테스트"""
        # Given
        symbol = "005935"
        
        with patch.object(data_collector, 'get_historical_data') as mock_get_data:
            mock_get_data.return_value = sample_stock_data
            
            # When - 첫 번째 호출
            result1 = await data_collector.get_historical_data(symbol, 30)
            
            # When - 두 번째 호출 (캐시 사용)
            result2 = await data_collector.get_historical_data(symbol, 30)
            
            # Then
            assert result1 is not None
            assert result2 is not None
            assert len(result1) == len(result2)
            
            # 캐시가 작동하면 두 번째 호출은 API를 다시 호출하지 않음
            assert mock_get_data.call_count == 1 