"""
전체 거래 워크플로우 E2E 테스트
자동매매 시스템의 전체 흐름을 테스트
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.web.web_dashboard import app
from src.auto_trading.auto_trader import AutoTrader
from src.auto_trading.watchlist_manager import WatchlistManager
from src.auto_trading.condition_manager import ConditionManager
from src.auto_trading.signal_monitor import SignalMonitor


class TestFullTradingWorkflow:
    """전체 거래 워크플로우 E2E 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 경로"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        yield db_path
        
        # 테스트 후 정리
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auto_trader(self, temp_db_path):
        """AutoTrader 모킹"""
        with patch('src.web.web_dashboard.auto_trader') as mock:
            instance = mock.return_value
            instance.db_path = temp_db_path
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
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_complete_trading_setup_workflow(self, client, mock_auto_trader, temp_db_path):
        """완전한 거래 설정 워크플로우 테스트"""
        # Given - 초기 상태
        mock_auto_trader.watchlist_manager.get_active_symbols.return_value = []
        mock_auto_trader.condition_manager.get_conditions.return_value = []
        
        # When 1 - 감시종목 추가
        response1 = client.post("/api/watchlist/add", json={"symbol": "005935"})
        
        # Then 1
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["success"] is True
        
        # When 2 - 거래 조건 추가
        condition_data = {
            "symbol": "005935",
            "condition_type": "buy",
            "category": "rsi",
            "value": "RSI < 30"
        }
        response2 = client.post("/api/conditions/add", json=condition_data)
        
        # Then 2
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is True
        
        # When 3 - 쿨다운 설정
        response3 = client.post("/api/auto-trading/cooldown?minutes=5")
        
        # Then 3
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["success"] is True
        
        # When 4 - 자동매매 시작
        response4 = client.post("/api/auto-trading/start", json={"quantity": 3})
        
        # Then 4
        assert response4.status_code == 200
        data4 = response4.json()
        assert data4["success"] is True
        
        # When 5 - 상태 확인
        response5 = client.get("/api/auto-trading/status")
        
        # Then 5
        assert response5.status_code == 200
        data5 = response5.json()
        assert data5["is_running"] is True
        
        # When 6 - 자동매매 중지
        response6 = client.post("/api/auto-trading/stop")
        
        # Then 6
        assert response6.status_code == 200
        data6 = response6.json()
        assert data6["success"] is True
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_multiple_symbols_trading_workflow(self, client, mock_auto_trader):
        """다중 종목 거래 워크플로우 테스트"""
        # Given
        symbols = ["005935", "000660", "035420"]
        conditions = [
            {"symbol": "005935", "condition_type": "buy", "category": "rsi", "value": "RSI < 30"},
            {"symbol": "000660", "condition_type": "sell", "category": "rsi", "value": "RSI > 70"},
            {"symbol": "035420", "condition_type": "buy", "category": "ma", "value": "MA5 > MA20"}
        ]
        
        # When 1 - 여러 종목 추가
        for symbol in symbols:
            response = client.post("/api/watchlist/add", json={"symbol": symbol})
            assert response.status_code == 200
            assert response.json()["success"] is True
        
        # When 2 - 여러 조건 추가
        for condition in conditions:
            response = client.post("/api/conditions/add", json=condition)
            assert response.status_code == 200
            assert response.json()["success"] is True
        
        # When 3 - 감시종목 목록 확인
        response = client.get("/api/watchlist")
        
        # Then 3
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["symbols"]) == 3
        for symbol in symbols:
            assert symbol in data["symbols"]
        
        # When 4 - 거래 조건 목록 확인
        response = client.get("/api/conditions")
        
        # Then 4
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["conditions"]) == 3
        
        # When 5 - 자동매매 시작
        response = client.post("/api/auto-trading/start", json={"quantity": 2})
        
        # Then 5
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_error_recovery_workflow(self, client, mock_auto_trader):
        """에러 복구 워크플로우 테스트"""
        # Given - 잘못된 요청들
        invalid_requests = [
            {"endpoint": "/api/watchlist/add", "data": {"symbol": "INVALID"}},
            {"endpoint": "/api/auto-trading/start", "data": {"quantity": 0}},
            {"endpoint": "/api/auto-trading/cooldown", "params": "minutes=-1"},
            {"endpoint": "/api/conditions/add", "data": {"symbol": "005935", "condition_type": "invalid"}}
        ]
        
        # When & Then - 잘못된 요청들 처리
        for request in invalid_requests:
            if "params" in request:
                response = client.post(f"{request['endpoint']}?{request['params']}")
            else:
                response = client.post(request["endpoint"], json=request["data"])
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "message" in data
        
        # When - 정상적인 요청으로 복구
        response = client.post("/api/watchlist/add", json={"symbol": "005935"})
        
        # Then
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_data_persistence_workflow(self, client, mock_auto_trader, temp_db_path):
        """데이터 영속성 워크플로우 테스트"""
        # Given - 데이터 추가
        symbol = "005935"
        condition_data = {
            "symbol": symbol,
            "condition_type": "buy",
            "category": "rsi",
            "value": "RSI < 30"
        }
        
        # When 1 - 데이터 추가
        client.post("/api/watchlist/add", json={"symbol": symbol})
        client.post("/api/conditions/add", json=condition_data)
        
        # When 2 - 새로운 AutoTrader 인스턴스로 데이터 확인
        new_auto_trader = AutoTrader(db_path=temp_db_path)
        
        # Then 2
        symbols = new_auto_trader.watchlist_manager.get_active_symbols()
        conditions = new_auto_trader.condition_manager.get_conditions()
        
        assert symbol in symbols
        assert len(conditions) == 1
        assert conditions[0]["symbol"] == symbol
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_real_time_monitoring_workflow(self, client, mock_auto_trader):
        """실시간 모니터링 워크플로우 테스트"""
        # Given - 기본 설정
        client.post("/api/watchlist/add", json={"symbol": "005935"})
        client.post("/api/auto-trading/start", json={"quantity": 1})
        
        # When 1 - 실시간 상태 확인
        response1 = client.get("/api/auto-trading/status")
        
        # Then 1
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["is_running"] is True
        
        # When 2 - 감시종목 목록 확인
        response2 = client.get("/api/watchlist")
        
        # Then 2
        assert response2.status_code == 200
        data2 = response2.json()
        assert "005935" in data2["symbols"]
        
        # When 3 - 거래 조건 목록 확인
        response3 = client.get("/api/conditions")
        
        # Then 3
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["success"] is True
        
        # When 4 - 자동매매 중지
        response4 = client.post("/api/auto-trading/stop")
        
        # Then 4
        assert response4.status_code == 200
        assert response4.json()["success"] is True
        
        # When 5 - 중지 후 상태 확인
        response5 = client.get("/api/auto-trading/status")
        
        # Then 5
        assert response5.status_code == 200
        data5 = response5.json()
        assert data5["is_running"] is False
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_performance_workflow(self, client, mock_auto_trader):
        """성능 워크플로우 테스트"""
        # Given - 대량의 데이터
        symbols = [f"00{i:04d}" for i in range(1, 101)]  # 100개 종목
        conditions = [
            {"symbol": symbol, "condition_type": "buy", "category": "rsi", "value": "RSI < 30"}
            for symbol in symbols[:50]  # 50개 조건
        ]
        
        # When 1 - 대량 종목 추가 (성능 테스트)
        start_time = datetime.now()
        for symbol in symbols:
            response = client.post("/api/watchlist/add", json={"symbol": symbol})
            assert response.status_code == 200
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Then 1 - 성능 검증 (100개 종목 추가가 10초 이내)
        assert duration < 10.0
        
        # When 2 - 대량 조건 추가 (성능 테스트)
        start_time = datetime.now()
        for condition in conditions:
            response = client.post("/api/conditions/add", json=condition)
            assert response.status_code == 200
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Then 2 - 성능 검증 (50개 조건 추가가 5초 이내)
        assert duration < 5.0
        
        # When 3 - 대량 데이터 조회 (성능 테스트)
        start_time = datetime.now()
        response = client.get("/api/watchlist")
        response2 = client.get("/api/conditions")
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Then 3 - 성능 검증 (조회가 1초 이내)
        assert duration < 1.0
        assert response.status_code == 200
        assert response2.status_code == 200
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_concurrent_access_workflow(self, client, mock_auto_trader):
        """동시 접근 워크플로우 테스트"""
        import threading
        import time
        
        # Given
        results = []
        errors = []
        
        def concurrent_request(request_type, data):
            try:
                if request_type == "add_symbol":
                    response = client.post("/api/watchlist/add", json=data)
                elif request_type == "get_status":
                    response = client.get("/api/auto-trading/status")
                elif request_type == "start_trading":
                    response = client.post("/api/auto-trading/start", json=data)
                
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # When - 동시 요청
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=concurrent_request,
                args=("add_symbol", {"symbol": f"00{i:04d}"})
            )
            threads.append(thread)
            thread.start()
        
        # 대기
        for thread in threads:
            thread.join()
        
        # Then - 에러 없이 처리
        assert len(errors) == 0
        assert len(results) == 10
        assert all(status == 200 for status in results) 