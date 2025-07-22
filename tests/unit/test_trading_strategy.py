"""
TradingStrategy 단위 테스트
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.trading.trading_strategy import TradingStrategy


class TestTradingStrategy:
    """TradingStrategy 클래스 테스트"""
    
    @pytest.fixture
    def trading_strategy(self):
        """TradingStrategy 인스턴스 fixture"""
        return TradingStrategy()
    
    @pytest.fixture
    def sample_market_data(self):
        """샘플 시장 데이터"""
        dates = pd.date_range(start='2025-07-15', end='2025-07-22', freq='D')
        data = pd.DataFrame({
            '종가': [50000, 51000, 52000, 53000, 54000, 53500, 54500, 55000],
            '시가': [49500, 50500, 51500, 52500, 53500, 53000, 54000, 54500],
            '고가': [51500, 52500, 53500, 54500, 55500, 55000, 56000, 56500],
            '저가': [49000, 50000, 51000, 52000, 53000, 52500, 53500, 54000],
            '거래량': [1000000, 1100000, 1200000, 1300000, 1400000, 1350000, 1450000, 1500000],
            'SMA_5': [np.nan, np.nan, np.nan, np.nan, 52000, 52500, 53000, 53500],
            'SMA_20': [np.nan] * 8,  # 20일 이동평균은 데이터가 부족
            'RSI': [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 65.5],
            'MACD': [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 0.5],
            'MACD_signal': [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, 0.3]
        }, index=dates)
        return data
    
    def test_trading_strategy_initialization(self, trading_strategy):
        """TradingStrategy 초기화 테스트"""
        # Then
        assert trading_strategy is not None
        assert hasattr(trading_strategy, 'strategy_name')
        assert hasattr(trading_strategy, 'parameters')
    
    def test_sma_crossover_strategy_buy_signal(self, trading_strategy, sample_market_data):
        """SMA 크로스오버 매수 신호 테스트"""
        # Given - 단기 이동평균이 장기 이동평균을 상향 돌파하는 상황
        sample_market_data.loc[sample_market_data.index[-2], 'SMA_5'] = 53000
        sample_market_data.loc[sample_market_data.index[-2], 'SMA_20'] = 53100
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_5'] = 53200
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_20'] = 53100
        
        # When
        signal = trading_strategy.sma_crossover_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'buy'
        assert signal['confidence'] > 0.5
        assert 'SMA 크로스오버' in signal['reason']
    
    def test_sma_crossover_strategy_sell_signal(self, trading_strategy, sample_market_data):
        """SMA 크로스오버 매도 신호 테스트"""
        # Given - 단기 이동평균이 장기 이동평균을 하향 돌파하는 상황
        sample_market_data.loc[sample_market_data.index[-2], 'SMA_5'] = 53200
        sample_market_data.loc[sample_market_data.index[-2], 'SMA_20'] = 53100
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_5'] = 53000
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_20'] = 53100
        
        # When
        signal = trading_strategy.sma_crossover_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'sell'
        assert signal['confidence'] > 0.5
        assert 'SMA 크로스오버' in signal['reason']
    
    def test_sma_crossover_strategy_no_signal(self, trading_strategy, sample_market_data):
        """SMA 크로스오버 신호 없음 테스트"""
        # Given - 크로스오버가 없는 상황
        sample_market_data.loc[sample_market_data.index[-2], 'SMA_5'] = 53000
        sample_market_data.loc[sample_market_data.index[-2], 'SMA_20'] = 53100
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_5'] = 53050
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_20'] = 53100
        
        # When
        signal = trading_strategy.sma_crossover_strategy(sample_market_data)
        
        # Then
        assert signal is None
    
    def test_rsi_strategy_oversold_buy(self, trading_strategy, sample_market_data):
        """RSI 과매도 매수 신호 테스트"""
        # Given - RSI가 30 이하 (과매도)
        sample_market_data.loc[sample_market_data.index[-1], 'RSI'] = 25
        
        # When
        signal = trading_strategy.rsi_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'buy'
        assert signal['confidence'] > 0.6
        assert 'RSI 과매도' in signal['reason']
    
    def test_rsi_strategy_overbought_sell(self, trading_strategy, sample_market_data):
        """RSI 과매수 매도 신호 테스트"""
        # Given - RSI가 70 이상 (과매수)
        sample_market_data.loc[sample_market_data.index[-1], 'RSI'] = 75
        
        # When
        signal = trading_strategy.rsi_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'sell'
        assert signal['confidence'] > 0.6
        assert 'RSI 과매수' in signal['reason']
    
    def test_rsi_strategy_no_signal(self, trading_strategy, sample_market_data):
        """RSI 신호 없음 테스트"""
        # Given - RSI가 중립 구간
        sample_market_data.loc[sample_market_data.index[-1], 'RSI'] = 50
        
        # When
        signal = trading_strategy.rsi_strategy(sample_market_data)
        
        # Then
        assert signal is None
    
    def test_macd_strategy_bullish_signal(self, trading_strategy, sample_market_data):
        """MACD 상승 신호 테스트"""
        # Given - MACD가 시그널을 상향 돌파
        sample_market_data.loc[sample_market_data.index[-2], 'MACD'] = 0.2
        sample_market_data.loc[sample_market_data.index[-2], 'MACD_signal'] = 0.3
        sample_market_data.loc[sample_market_data.index[-1], 'MACD'] = 0.4
        sample_market_data.loc[sample_market_data.index[-1], 'MACD_signal'] = 0.3
        
        # When
        signal = trading_strategy.macd_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'buy'
        assert signal['confidence'] > 0.5
        assert 'MACD 상승' in signal['reason']
    
    def test_macd_strategy_bearish_signal(self, trading_strategy, sample_market_data):
        """MACD 하락 신호 테스트"""
        # Given - MACD가 시그널을 하향 돌파
        sample_market_data.loc[sample_market_data.index[-2], 'MACD'] = 0.4
        sample_market_data.loc[sample_market_data.index[-2], 'MACD_signal'] = 0.3
        sample_market_data.loc[sample_market_data.index[-1], 'MACD'] = 0.2
        sample_market_data.loc[sample_market_data.index[-1], 'MACD_signal'] = 0.3
        
        # When
        signal = trading_strategy.macd_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'sell'
        assert signal['confidence'] > 0.5
        assert 'MACD 하락' in signal['reason']
    
    def test_volume_strategy_high_volume(self, trading_strategy, sample_market_data):
        """거래량 전략 고거래량 테스트"""
        # Given - 평균 대비 높은 거래량
        avg_volume = sample_market_data['거래량'].mean()
        sample_market_data.loc[sample_market_data.index[-1], '거래량'] = avg_volume * 2
        
        # When
        signal = trading_strategy.volume_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['confidence'] > 0.4
        assert '거래량 급증' in signal['reason']
    
    def test_combined_strategy(self, trading_strategy, sample_market_data):
        """복합 전략 테스트"""
        # Given - 여러 지표가 매수 신호를 보내는 상황
        sample_market_data.loc[sample_market_data.index[-1], 'RSI'] = 25  # 과매도
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_5'] = 53200
        sample_market_data.loc[sample_market_data.index[-1], 'SMA_20'] = 53100
        
        # When
        signal = trading_strategy.combined_strategy(sample_market_data)
        
        # Then
        assert signal is not None
        assert signal['signal_type'] == 'buy'
        assert signal['confidence'] > 0.7  # 여러 지표가 일치하면 신뢰도가 높아짐
    
    def test_calculate_signal_confidence(self, trading_strategy):
        """신호 신뢰도 계산 테스트"""
        # Given
        indicators = ['RSI', 'SMA', 'MACD']
        weights = {'RSI': 0.4, 'SMA': 0.4, 'MACD': 0.2}
        
        # When
        confidence = trading_strategy._calculate_signal_confidence(indicators, weights)
        
        # Then
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # 여러 지표가 일치하면 높은 신뢰도
    
    def test_validate_market_data(self, trading_strategy, sample_market_data):
        """시장 데이터 유효성 검사 테스트"""
        # Valid data
        assert trading_strategy._validate_market_data(sample_market_data) is True
        
        # Invalid data - 빈 DataFrame
        empty_data = pd.DataFrame()
        assert trading_strategy._validate_market_data(empty_data) is False
        
        # Invalid data - 필수 컬럼 없음
        invalid_data = sample_market_data.drop(columns=['종가'])
        assert trading_strategy._validate_market_data(invalid_data) is False
    
    def test_get_strategy_parameters(self, trading_strategy):
        """전략 파라미터 조회 테스트"""
        # When
        params = trading_strategy.get_strategy_parameters()
        
        # Then
        assert isinstance(params, dict)
        assert 'sma_short' in params
        assert 'sma_long' in params
        assert 'rsi_oversold' in params
        assert 'rsi_overbought' in params
    
    def test_update_strategy_parameters(self, trading_strategy):
        """전략 파라미터 업데이트 테스트"""
        # Given
        new_params = {
            'sma_short': 10,
            'sma_long': 30,
            'rsi_oversold': 25,
            'rsi_overbought': 75
        }
        
        # When
        trading_strategy.update_strategy_parameters(new_params)
        
        # Then
        updated_params = trading_strategy.get_strategy_parameters()
        assert updated_params['sma_short'] == 10
        assert updated_params['sma_long'] == 30
        assert updated_params['rsi_oversold'] == 25
        assert updated_params['rsi_overbought'] == 75 