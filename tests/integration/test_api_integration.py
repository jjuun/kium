"""
API 통합 테스트
웹 대시보드와 자동매매 시스템 간의 통합 테스트
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from src.web.web_dashboard import app
from src.auto_trading.auto_trader import AutoTrader


class TestAPIIntegration:
    """API 통합 테스트"""
    
    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auto_trader(self):
        """AutoTrader 모킹"""
        with patch('src.web.web_dashboard.auto_trader') as mock:
            instance = mock.return_value
            instance.is_running = False
            instance.trade_quantity = 1
            instance.order_cooldown = 60
            instance.get_status.return_value = {
                'is_running': False,
                'active_symbols_count': 0,
                'active_conditions_count': 0,
                'daily_order_count_test': 0
            }
            yield instance
    
    def test_auto_trading_status_endpoint(self, client, mock_auto_trader):
        """자동매매 상태 조회 엔드포인트 테스트"""
        # When
        response = client.get("/api/auto-trading/status")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert "is_running" in data
        assert "active_symbols_count" in data
        assert "active_conditions_count" in data
        assert "daily_order_count_test" in data
    
    def test_start_auto_trading_endpoint(self, client, mock_auto_trader):
        """자동매매 시작 엔드포인트 테스트"""
        # Given
        mock_auto_trader.start.return_value = True
        
        # When
        response = client.post("/api/auto-trading/start", json={"quantity": 5})
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_auto_trader.start.assert_called_once_with(5)
    
    def test_stop_auto_trading_endpoint(self, client, mock_auto_trader):
        """자동매매 중지 엔드포인트 테스트"""
        # Given
        mock_auto_trader.stop.return_value = True
        
        # When
        response = client.post("/api/auto-trading/stop")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_auto_trader.stop.assert_called_once()
    
    def test_set_cooldown_endpoint(self, client, mock_auto_trader):
        """쿨다운 설정 엔드포인트 테스트"""
        # When
        response = client.post("/api/auto-trading/cooldown?minutes=10")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert mock_auto_trader.order_cooldown == 600  # 10분 = 600초
    
    def test_add_watchlist_symbol_endpoint(self, client, mock_auto_trader):
        """감시종목 추가 엔드포인트 테스트"""
        # Given
        mock_auto_trader.watchlist_manager.add_symbol.return_value = True
        
        # When
        response = client.post("/api/watchlist/add", json={"symbol": "005935"})
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_auto_trader.watchlist_manager.add_symbol.assert_called_once_with("005935")
    
    def test_remove_watchlist_symbol_endpoint(self, client, mock_auto_trader):
        """감시종목 제거 엔드포인트 테스트"""
        # Given
        mock_auto_trader.watchlist_manager.remove_symbol.return_value = True
        
        # When
        response = client.delete("/api/watchlist/remove/005935")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_auto_trader.watchlist_manager.remove_symbol.assert_called_once_with("005935")
    
    def test_add_trading_condition_endpoint(self, client, mock_auto_trader):
        """거래 조건 추가 엔드포인트 테스트"""
        # Given
        mock_auto_trader.condition_manager.add_condition.return_value = True
        condition_data = {
            "symbol": "005935",
            "condition_type": "buy",
            "category": "rsi",
            "value": "RSI < 30"
        }
        
        # When
        response = client.post("/api/conditions/add", json=condition_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_auto_trader.condition_manager.add_condition.assert_called_once_with(
            "005935", "buy", "rsi", "RSI < 30"
        )
    
    def test_remove_trading_condition_endpoint(self, client, mock_auto_trader):
        """거래 조건 제거 엔드포인트 테스트"""
        # Given
        mock_auto_trader.condition_manager.remove_condition.return_value = True
        
        # When
        response = client.delete("/api/conditions/remove/1")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_auto_trader.condition_manager.remove_condition.assert_called_once_with(1)
    
    def test_get_watchlist_endpoint(self, client, mock_auto_trader):
        """감시종목 목록 조회 엔드포인트 테스트"""
        # Given
        mock_auto_trader.watchlist_manager.get_active_symbols.return_value = ["005935", "000660"]
        
        # When
        response = client.get("/api/watchlist")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "005935" in data["symbols"]
        assert "000660" in data["symbols"]
    
    def test_get_conditions_endpoint(self, client, mock_auto_trader):
        """거래 조건 목록 조회 엔드포인트 테스트"""
        # Given
        mock_conditions = [
            {"id": 1, "symbol": "005935", "condition_type": "buy", "category": "rsi", "value": "RSI < 30"}
        ]
        mock_auto_trader.condition_manager.get_conditions.return_value = mock_conditions
        
        # When
        response = client.get("/api/conditions")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["symbol"] == "005935"
    
    def test_error_handling_invalid_symbol(self, client, mock_auto_trader):
        """잘못된 종목코드 에러 처리 테스트"""
        # When
        response = client.post("/api/watchlist/add", json={"symbol": "INVALID"})
        
        # Then
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "잘못된 종목코드" in data["message"]
    
    def test_error_handling_invalid_quantity(self, client, mock_auto_trader):
        """잘못된 매매 수량 에러 처리 테스트"""
        # When
        response = client.post("/api/auto-trading/start", json={"quantity": 0})
        
        # Then
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "매매 수량은 1 이상" in data["message"]
    
    def test_error_handling_invalid_cooldown(self, client, mock_auto_trader):
        """잘못된 쿨다운 시간 에러 처리 테스트"""
        # When
        response = client.post("/api/auto-trading/cooldown?minutes=-1")
        
        # Then
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "쿨다운 시간은 0 이상" in data["message"] 