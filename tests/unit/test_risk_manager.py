"""
RiskManager 단위 테스트
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.trading.risk_manager import RiskManager


class TestRiskManager:
    """RiskManager 클래스 테스트"""
    
    @pytest.fixture
    def risk_manager(self):
        """RiskManager 인스턴스 fixture"""
        return RiskManager()
    
    @pytest.fixture
    def sample_position(self):
        """샘플 포지션 데이터"""
        return {
            'symbol': '005935',
            'quantity': 10,
            'avg_price': 50000,
            'current_price': 52000,
            'unrealized_pnl': 200000,  # 10 * (52000 - 50000)
            'realized_pnl': 0,
            'entry_time': datetime.now() - timedelta(days=5)
        }
    
    @pytest.fixture
    def sample_order(self):
        """샘플 주문 데이터"""
        return {
            'symbol': '005935',
            'order_type': 'buy',
            'quantity': 5,
            'price': 50000,
            'total_amount': 250000
        }
    
    def test_risk_manager_initialization(self, risk_manager):
        """RiskManager 초기화 테스트"""
        # Then
        assert risk_manager is not None
        assert hasattr(risk_manager, 'max_position_size')
        assert hasattr(risk_manager, 'max_daily_loss')
        assert hasattr(risk_manager, 'stop_loss_pct')
        assert hasattr(risk_manager, 'take_profit_pct')
    
    def test_check_position_size_limit(self, risk_manager, sample_order):
        """포지션 크기 제한 체크 테스트"""
        # Given - 현재 포지션 크기가 제한 내
        current_positions = {'005935': {'quantity': 5, 'avg_price': 50000}}
        risk_manager.max_position_size = 1000000  # 100만원
        
        # When
        result = risk_manager.check_position_size_limit(sample_order, current_positions)
        
        # Then
        assert result is True
        
        # Given - 포지션 크기 초과
        large_order = sample_order.copy()
        large_order['quantity'] = 50  # 250만원
        result = risk_manager.check_position_size_limit(large_order, current_positions)
        assert result is False
    
    def test_check_daily_loss_limit(self, risk_manager):
        """일일 손실 제한 체크 테스트"""
        # Given - 일일 손실이 제한 내
        daily_pnl = -50000  # 5만원 손실
        risk_manager.max_daily_loss = 100000  # 10만원
        
        # When
        result = risk_manager.check_daily_loss_limit(daily_pnl)
        
        # Then
        assert result is True
        
        # Given - 일일 손실 초과
        large_loss = -150000  # 15만원 손실
        result = risk_manager.check_daily_loss_limit(large_loss)
        assert result is False
    
    def test_check_stop_loss(self, risk_manager, sample_position):
        """손절 체크 테스트"""
        # Given - 손절 조건 만족 (2% 손실)
        sample_position['current_price'] = 49000  # 2% 하락
        risk_manager.stop_loss_pct = 0.02
        
        # When
        result = risk_manager.check_stop_loss(sample_position)
        
        # Then
        assert result is True
        
        # Given - 손절 조건 불만족
        sample_position['current_price'] = 49500  # 1% 하락
        result = risk_manager.check_stop_loss(sample_position)
        assert result is False
    
    def test_check_take_profit(self, risk_manager, sample_position):
        """익절 체크 테스트"""
        # Given - 익절 조건 만족 (5% 수익)
        sample_position['current_price'] = 52500  # 5% 상승
        risk_manager.take_profit_pct = 0.05
        
        # When
        result = risk_manager.check_take_profit(sample_position)
        
        # Then
        assert result is True
        
        # Given - 익절 조건 불만족
        sample_position['current_price'] = 52000  # 4% 상승
        result = risk_manager.check_take_profit(sample_position)
        assert result is False
    
    def test_calculate_position_risk(self, risk_manager, sample_position):
        """포지션 리스크 계산 테스트"""
        # When
        risk_score = risk_manager.calculate_position_risk(sample_position)
        
        # Then
        assert 0 <= risk_score <= 1
        assert isinstance(risk_score, float)
    
    def test_check_portfolio_diversification(self, risk_manager):
        """포트폴리오 분산 체크 테스트"""
        # Given - 분산된 포트폴리오
        positions = {
            '005935': {'quantity': 5, 'avg_price': 50000},
            '000660': {'quantity': 3, 'avg_price': 80000},
            '035420': {'quantity': 2, 'avg_price': 120000}
        }
        
        # When
        result = risk_manager.check_portfolio_diversification(positions)
        
        # Then
        assert result is True
        
        # Given - 집중된 포트폴리오
        concentrated_positions = {
            '005935': {'quantity': 20, 'avg_price': 50000}
        }
        result = risk_manager.check_portfolio_diversification(concentrated_positions)
        assert result is False
    
    def test_check_market_volatility(self, risk_manager):
        """시장 변동성 체크 테스트"""
        # Given - 낮은 변동성
        price_history = [50000, 50100, 50200, 50300, 50400]
        
        # When
        result = risk_manager.check_market_volatility(price_history)
        
        # Then
        assert result is True
        
        # Given - 높은 변동성
        volatile_history = [50000, 48000, 52000, 46000, 54000]
        result = risk_manager.check_market_volatility(volatile_history)
        assert result is False
    
    def test_calculate_max_order_size(self, risk_manager):
        """최대 주문 크기 계산 테스트"""
        # Given
        available_capital = 1000000  # 100만원
        current_positions = {'005935': {'quantity': 5, 'avg_price': 50000}}
        
        # When
        max_size = risk_manager.calculate_max_order_size(available_capital, current_positions)
        
        # Then
        assert max_size > 0
        assert max_size <= available_capital * 0.1  # 최대 10% 제한
    
    def test_check_order_frequency(self, risk_manager):
        """주문 빈도 체크 테스트"""
        # Given - 정상적인 주문 빈도
        recent_orders = [
            datetime.now() - timedelta(minutes=30),
            datetime.now() - timedelta(minutes=20),
            datetime.now() - timedelta(minutes=10)
        ]
        
        # When
        result = risk_manager.check_order_frequency(recent_orders)
        
        # Then
        assert result is True
        
        # Given - 과도한 주문 빈도
        frequent_orders = [
            datetime.now() - timedelta(minutes=1),
            datetime.now() - timedelta(seconds=30),
            datetime.now() - timedelta(seconds=10)
        ]
        result = risk_manager.check_order_frequency(frequent_orders)
        assert result is False
    
    def test_validate_order(self, risk_manager, sample_order):
        """주문 유효성 검사 테스트"""
        # Given - 유효한 주문
        current_positions = {}
        daily_pnl = 0
        
        # When
        result = risk_manager.validate_order(sample_order, current_positions, daily_pnl)
        
        # Then
        assert result['valid'] is True
        assert 'reason' in result
        
        # Given - 무효한 주문 (수량이 0)
        invalid_order = sample_order.copy()
        invalid_order['quantity'] = 0
        result = risk_manager.validate_order(invalid_order, current_positions, daily_pnl)
        assert result['valid'] is False
    
    def test_get_risk_metrics(self, risk_manager):
        """리스크 지표 조회 테스트"""
        # Given
        positions = {
            '005935': {'quantity': 5, 'avg_price': 50000, 'current_price': 52000},
            '000660': {'quantity': 3, 'avg_price': 80000, 'current_price': 78000}
        }
        
        # When
        metrics = risk_manager.get_risk_metrics(positions)
        
        # Then
        assert 'total_exposure' in metrics
        assert 'portfolio_risk_score' in metrics
        assert 'diversification_score' in metrics
        assert 'max_drawdown' in metrics
        assert all(isinstance(v, (int, float)) for v in metrics.values())
    
    def test_update_risk_parameters(self, risk_manager):
        """리스크 파라미터 업데이트 테스트"""
        # Given
        new_params = {
            'max_position_size': 2000000,
            'max_daily_loss': 150000,
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.07
        }
        
        # When
        risk_manager.update_risk_parameters(new_params)
        
        # Then
        assert risk_manager.max_position_size == 2000000
        assert risk_manager.max_daily_loss == 150000
        assert risk_manager.stop_loss_pct == 0.03
        assert risk_manager.take_profit_pct == 0.07
    
    def test_calculate_var(self, risk_manager):
        """VaR (Value at Risk) 계산 테스트"""
        # Given
        returns = [0.01, -0.02, 0.015, -0.01, 0.025, -0.005, 0.02, -0.015]
        confidence_level = 0.95
        
        # When
        var = risk_manager.calculate_var(returns, confidence_level)
        
        # Then
        assert var < 0  # VaR은 보통 음수
        assert isinstance(var, float)
    
    def test_check_correlation_risk(self, risk_manager):
        """상관관계 리스크 체크 테스트"""
        # Given - 높은 상관관계를 가진 종목들
        positions = {
            '005935': {'quantity': 5, 'avg_price': 50000},  # 삼성전자
            '000660': {'quantity': 3, 'avg_price': 80000},  # SK하이닉스
            '035420': {'quantity': 2, 'avg_price': 120000}  # NAVER
        }
        
        # When
        result = risk_manager.check_correlation_risk(positions)
        
        # Then
        assert isinstance(result, bool)
        assert 'correlation_score' in risk_manager.get_risk_metrics(positions) 