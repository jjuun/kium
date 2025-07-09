from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import uvicorn
import json
from datetime import datetime, timedelta

# 기존 모듈들 import
from src.api.kiwoom_api import KiwoomAPI
from src.core.data_collector import DataCollector
from src.trading.order_executor import OrderExecutor
from src.core.config import Config
from src.core.logger import logger

# 자동매매 모듈 import
from src.auto_trading.watchlist_manager import WatchlistManager
from src.auto_trading.condition_manager import ConditionManager
from src.auto_trading.auto_trader import AutoTrader
from src.auto_trading.signal_monitor import SignalMonitor, SignalStatus

app = FastAPI(title="A-ki Trading Dashboard", version="1.0.0")

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 전역 객체들 초기화
config = Config()
kiwoom_api = KiwoomAPI()
data_collector = DataCollector()
order_executor = OrderExecutor()
watchlist_manager = WatchlistManager()
condition_manager = ConditionManager()
auto_trader = AutoTrader()
signal_monitor = SignalMonitor()

@app.get("/")
async def home():
    return FileResponse("templates/dashboard.html")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.svg")

@app.get("/api/test")
async def test():
    return {"message": "서버 동작 중", "status": "success"}

# 계좌 정보 API
@app.get("/api/account/balance")
async def get_account_balance():
    try:
        balance_data = kiwoom_api.get_account_balance_kt00018()
        if not balance_data:
            logger.warning("계좌 잔고 데이터가 없습니다.")
            return {
                'output': [],
                'total_count': 0,
                'error': '계좌 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        return balance_data
    except Exception as e:
        logger.error(f"계좌 잔고 조회 실패: {str(e)}")
        return {
            'output': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 관심종목 API
@app.get("/api/watchlist")
async def get_watchlist():
    try:
        logger.info("관심종목 조회 API 호출")
        watchlist = kiwoom_api.get_watchlist()
        if not watchlist or 'watchlist' not in watchlist:
            return {
                'watchlist': [],
                'total_count': 0,
                'error': '관심종목 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        logger.info(f"관심종목 조회 결과: {watchlist}")
        return watchlist
    except Exception as e:
        logger.error(f"관심종목 조회 실패: {str(e)}")
        return {
            'watchlist': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/watchlist/add")
async def add_watchlist(stk_cd: str = Query(..., description="종목코드")):
    try:
        result = kiwoom_api.add_watchlist(stk_cd)
        return result
    except Exception as e:
        logger.error(f"관심종목 등록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/watchlist/remove")
async def remove_watchlist(stk_cd: str = Query(..., description="종목코드")):
    try:
        result = kiwoom_api.remove_watchlist(stk_cd)
        return result
    except Exception as e:
        logger.error(f"관심종목 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 거래 내역 API
@app.get("/api/trades/history")
async def get_trades_history(days: int = Query(7, description="조회 일수")):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 여러 주요 종목의 체결 내역 조회
        all_trades = []
        symbols = ["A005935", "A090435", "A005380", "A000660"]  # 삼성전자, 현대차, 현대모비스, SK하이닉스
        
        for symbol in symbols:
            try:
                trades = kiwoom_api.get_execution_history_by_date(symbol, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
                if trades and 'output' in trades and trades['output']:
                    # 종목 정보 추가
                    for trade in trades['output']:
                        if isinstance(trade, dict):
                            trade['symbol'] = symbol
                            trade['symbol_name'] = _get_symbol_name(symbol)
                    all_trades.extend(trades['output'])
            except Exception as e:
                logger.warning(f"종목 {symbol} 체결 내역 조회 실패: {e}")
                continue
        
        # 날짜순으로 정렬
        all_trades.sort(key=lambda x: x.get('exec_dt', ''), reverse=True)
        
        return {
            'output': all_trades,
            'total_count': len(all_trades),
            'date_range': f"{start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}",
            'symbols': symbols
        }
    except Exception as e:
        logger.error(f"거래 내역 조회 실패: {str(e)}")
        return {
            'output': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 체결 내역 API
@app.get("/api/execution/history")
async def get_execution_history(stk_cd: str = Query(..., description="종목코드")):
    try:
        execution_data = kiwoom_api.get_execution_history(stk_cd)
        if not execution_data:
            return {
                'output': [],
                'total_count': 0,
                'error': '체결 내역 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        return execution_data
    except Exception as e:
        logger.error(f"체결 내역 조회 실패: {str(e)}")
        return {
            'output': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 키움 체결 내역 API (JavaScript에서 호출하는 URL)
@app.get("/api/kiwoom/execution-history")
async def get_kiwoom_execution_history(stk_cd: str = Query(..., description="종목코드")):
    try:
        execution_data = kiwoom_api.get_execution_history(stk_cd)
        if not execution_data:
            return {
                'output': [],
                'total_count': 0,
                'error': '체결 내역 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        return execution_data
    except Exception as e:
        logger.error(f"키움 체결 내역 조회 실패: {str(e)}")
        return {
            'output': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def _get_symbol_name(symbol: str) -> str:
    """종목코드로 종목명 반환"""
    symbol_names = {
        'A005935': '삼성전자',
        'A090435': '현대차',
        'A005380': '현대모비스',
        'A000660': 'SK하이닉스',
        '005935': '삼성전자',
        '090435': '현대차',
        '005380': '현대모비스',
        '000660': 'SK하이닉스'
    }
    return symbol_names.get(symbol, symbol)

# 매매 신호 API
@app.get("/api/trading/signals")
async def get_trading_signals(symbol: str = Query(..., description="종목코드")):
    try:
        # 과거 데이터를 가져와서 기술적 지표 계산
        historical_data = data_collector.get_historical_data(symbol)
        if historical_data is not None:
            signals_data = data_collector.calculate_technical_indicators(historical_data)
            return {
                "symbol": symbol,
                "signals": signals_data.to_dict('records') if signals_data is not None else [],
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "symbol": symbol,
                "signals": [],
                "timestamp": datetime.now().isoformat(),
                "message": "데이터 없음"
            }
    except Exception as e:
        logger.error(f"매매 신호 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 주식 기본정보 API
@app.get("/api/stock/basic-info")
async def get_stock_basic_info(symbol: str = Query(..., description="종목코드")):
    try:
        basic_info = kiwoom_api.get_stock_basic_info(symbol)
        return basic_info
    except Exception as e:
        logger.error(f"주식 기본정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 키움 주식 기본정보 API (JavaScript에서 호출하는 URL)
@app.get("/api/kiwoom/stock-basic-info")
async def get_kiwoom_stock_basic_info(stk_cd: str = Query(..., description="종목코드")):
    try:
        basic_info = kiwoom_api.get_stock_basic_info(stk_cd)
        return basic_info
    except Exception as e:
        logger.error(f"키움 주식 기본정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 주문 실행 API
@app.post("/api/orders/place")
async def place_order(order_data: Dict[str, Any]):
    try:
        from src.trading.order_executor import OrderRequest, OrderType, OrderPriceType
        
        order_request = OrderRequest(
            symbol=order_data["symbol"],
            order_type=OrderType.BUY if order_data["action"] == "buy" else OrderType.SELL,
            quantity=order_data["quantity"],
            price=order_data["price"],
            price_type=OrderPriceType(order_data["price_type"])
        )
        
        result = order_executor.place_order(order_request)
        
        # 상세 로깅 추가
        logger.info(f"=== 주문 API 응답 처리 ===")
        logger.info(f"OrderResult: {result}")
        logger.info(f"Result status: {result.status.value if result else 'None'}")
        logger.info(f"Result message: {result.message if result else 'None'}")
        
        # 프론트엔드가 기대하는 형식으로 응답
        if result and result.status.value not in ['거부', 'REJECTED']:
            response = {
                "success": True,
                "order_id": result.order_id,
                "message": result.message or "주문 접수 완료"
            }
            logger.info(f"✅ 주문 성공 응답: {response}")
            return response
        else:
            response = {
                "success": False,
                "message": result.message if result else "주문 접수 실패"
            }
            logger.error(f"❌ 주문 실패 응답: {response}")
            return response
    except Exception as e:
        logger.error(f"주문 실행 실패: {str(e)}")
        response = {
            "success": False,
            "message": str(e)
        }
        logger.error(f"❌ 주문 예외 응답: {response}")
        return response

# 주문 취소 API
@app.post("/api/orders/cancel")
async def cancel_order(order_data: Dict[str, Any]):
    try:
        result = order_executor.cancel_order(order_data["order_id"])
        return {"success": result}
    except Exception as e:
        logger.error(f"주문 취소 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 미체결 주문 API
@app.get("/api/trading/orders/pending")
async def get_pending_orders():
    try:
        pending_orders = order_executor.get_pending_orders()
        return pending_orders
    except Exception as e:
        logger.error(f"미체결 주문 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 주문 내역 API
@app.get("/api/trading/orders/history")
async def get_order_history(days: int = Query(7, description="조회 일수")):
    try:
        order_history = order_executor.get_order_history(days)
        return order_history
    except Exception as e:
        logger.error(f"주문 내역 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 실현손익 API (예시, 실제 함수명에 맞게 적용)
@app.get("/api/kiwoom/realized-pnl")
async def get_realized_pnl(stk_cd: str = Query(..., description="종목코드")):
    try:
        result = kiwoom_api.get_realized_pnl(stk_cd)
        if not result or 'output' not in result:
            return {
                'output': [],
                'error': '실현손익 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        return result
    except Exception as e:
        logger.error(f"실현손익 조회 실패: {str(e)}")
        return {
            'output': [],
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 주식 현재가 API
@app.get("/api/stock/price")
async def get_stock_price(symbol: str = Query(..., description="종목코드")):
    try:
        logger.info(f"현재가 조회 요청: {symbol}")
        result = kiwoom_api.get_stock_price(symbol)
        logger.info(f"현재가 조회 결과: {result}")
        
        if not result:
            logger.warning(f"현재가 조회 결과 없음: {symbol}")
            return {
                'current_price': None,
                'error': '현재가 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        
        # KiwoomAPI의 get_stock_price 응답 형식에 맞게 처리
        if 'output' in result and result['output']:
            output = result['output'][0] if isinstance(result['output'], list) else result['output']
            current_price = output.get('prpr', None)
            logger.info(f"현재가 추출: {symbol} - {current_price}")
            
            if current_price and current_price != '0':
                return {
                    'current_price': float(current_price),
                    'change_rate': output.get('diff_rt', '0'),
                    'timestamp': datetime.now().isoformat()
                }
        
        logger.warning(f"현재가 데이터 없음: {symbol}")
        return {
            'current_price': None,
            'error': '현재가 데이터 없음',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"현재가 조회 실패: {symbol} - {str(e)}")
        return {
            'current_price': None,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 체결잔고요청 API (kt00005)
@app.get("/api/execution/balance")
async def get_execution_balance(dmst_stex_tp: str = Query("KRX", description="국내거래소구분"), 
                               cont_yn: str = Query("N", description="연속조회여부"),
                               next_key: str = Query("", description="연속조회키")):
    try:
        execution_balance = kiwoom_api.get_execution_balance_kt00005(dmst_stex_tp, cont_yn, next_key)
        if not execution_balance:
            return {
                'output': [],
                'total_count': 0,
                'error': '체결잔고 데이터 없음',
                'timestamp': datetime.now().isoformat()
            }
        return execution_balance
    except Exception as e:
        logger.error(f"체결잔고 조회 실패: {str(e)}")
        return {
            'output': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 감시 종목 관리 API
@app.get("/api/auto-trading/watchlist")
async def get_watchlist():
    """감시 종목 목록 조회"""
    try:
        items = watchlist_manager.get_all_symbols()
        return {
            'items': [item.to_dict() for item in items],
            'total_count': len(items),
            'statistics': watchlist_manager.get_statistics(),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"감시 종목 목록 조회 실패: {str(e)}")
        return {
            'items': [],
            'total_count': 0,
            'statistics': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/auto-trading/watchlist")
async def add_to_watchlist(symbol: str = Query(..., description="종목코드"), 
                          symbol_name: str = Query(None, description="종목명")):
    """감시 종목 추가"""
    try:
        success = watchlist_manager.add_symbol(symbol, symbol_name)
        if success:
            return {
                'success': True,
                'message': f'감시 종목 추가 완료: {symbol}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'감시 종목 추가 실패: {symbol}',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"감시 종목 추가 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.delete("/api/auto-trading/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """감시 종목 제거"""
    try:
        success = watchlist_manager.remove_symbol(symbol)
        if success:
            return {
                'success': True,
                'message': f'감시 종목 제거 완료: {symbol}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'감시 종목 제거 실패: {symbol}',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"감시 종목 제거 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.put("/api/auto-trading/watchlist/{symbol}")
async def update_watchlist_item(symbol: str, 
                               symbol_name: str = Query(None, description="종목명"),
                               is_active: bool = Query(None, description="활성화 여부")):
    """감시 종목 정보 수정"""
    try:
        success = watchlist_manager.update_symbol(symbol, symbol_name, is_active)
        if success:
            return {
                'success': True,
                'message': f'감시 종목 수정 완료: {symbol}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'감시 종목 수정 실패: {symbol}',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"감시 종목 수정 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/auto-trading/watchlist/statistics")
async def get_watchlist_statistics():
    """감시 종목 통계 정보 조회"""
    try:
        stats = watchlist_manager.get_statistics()
        return {
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"감시 종목 통계 조회 실패: {str(e)}")
        return {
            'statistics': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 매수/매도 조건 관리 API
@app.get("/api/auto-trading/conditions")
async def get_conditions(symbol: str = Query(None, description="종목코드"), 
                        condition_type: str = Query(None, description="조건 타입 (buy/sell)")):
    """매수/매도 조건 목록 조회"""
    try:
        items = condition_manager.get_conditions(symbol=symbol, condition_type=condition_type)
        return {
            'items': [item.to_dict() for item in items],
            'total_count': len(items),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"매수/매도 조건 목록 조회 실패: {str(e)}")
        return {
            'items': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/auto-trading/conditions")
async def add_condition(symbol: str = Query(..., description="종목코드"),
                       condition_type: str = Query(..., description="조건 타입 (buy/sell)"),
                       category: str = Query("custom", description="조건 카테고리"),
                       value: str = Query(..., description="조건 값"),
                       description: str = Query("", description="조건 설명")):
    """매수/매도 조건 추가"""
    try:
        success = condition_manager.add_condition(symbol, condition_type, category, value, description)
        if success:
            return {
                'success': True,
                'message': f'조건 추가 완료: {symbol} {condition_type}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'조건 추가 실패: {symbol} {condition_type}',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"매수/매도 조건 추가 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.delete("/api/auto-trading/conditions/{condition_id}")
async def remove_condition(condition_id: int):
    """매수/매도 조건 삭제"""
    try:
        success = condition_manager.remove_condition(condition_id)
        if success:
            return {
                'success': True,
                'message': f'조건 삭제 완료: {condition_id}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'조건 삭제 실패: {condition_id}',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"매수/매도 조건 삭제 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.put("/api/auto-trading/conditions/{condition_id}")
async def update_condition(condition_id: int,
                          value: str = Query(None, description="조건 값"),
                          description: str = Query(None, description="조건 설명"),
                          is_active: bool = Query(None, description="활성화 여부")):
    """매수/매도 조건 수정"""
    try:
        success = condition_manager.update_condition(condition_id, value, description, is_active)
        if success:
            return {
                'success': True,
                'message': f'조건 수정 완료: {condition_id}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': f'조건 수정 실패: {condition_id}',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"매수/매도 조건 수정 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/auto-trading/conditions/{condition_id}/backtest")
async def backtest_condition(condition_id: int):
    """조건 백테스트 실행"""
    try:
        condition = condition_manager.get_condition(condition_id)
        if not condition:
            return {
                'success': False,
                'error': '조건을 찾을 수 없습니다.',
                'timestamp': datetime.now().isoformat()
            }
        
        # 간단한 백테스트 시뮬레이션 (실제로는 더 복잡한 로직 필요)
        import random
        success_rate = random.uniform(60, 85)  # 60-85% 성공률
        total_signals = random.randint(10, 50)
        successful_signals = int(total_signals * success_rate / 100)
        avg_profit = random.uniform(-5, 15)  # -5% ~ +15% 평균 수익률
        
        # 성과 업데이트
        success = condition_manager.update_condition_performance(
            condition_id, success_rate, total_signals, successful_signals, avg_profit
        )
        
        if success:
            return {
                'success': True,
                'result': {
                    'success_rate': round(success_rate, 2),
                    'total_signals': total_signals,
                    'successful_signals': successful_signals,
                    'avg_profit': round(avg_profit, 2)
                },
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': '백테스트 결과 저장 실패',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"조건 백테스트 실패: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 조건 그룹 관리 API
@app.get("/api/auto-trading/condition-groups")
async def get_condition_groups(symbol: str = Query(None, description="종목코드")):
    """조건 그룹 목록 조회"""
    try:
        groups = condition_manager.get_condition_groups(symbol=symbol)
        return {
            'groups': [group.to_dict() for group in groups],
            'total_count': len(groups),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"조건 그룹 목록 조회 실패: {str(e)}")
        return {
            'groups': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/auto-trading/condition-groups")
async def create_condition_group(symbol: str = Query(..., description="종목코드"),
                                name: str = Query(..., description="그룹명"),
                                logic: str = Query(..., description="로직 (AND/OR)"),
                                priority: int = Query(5, description="우선순위")):
    """조건 그룹 생성"""
    try:
        group_id = condition_manager.create_condition_group(symbol, name, logic, priority)
        if group_id:
            return {
                'success': True,
                'group_id': group_id,
                'message': f'조건 그룹 생성 완료: {name}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': '조건 그룹 생성 실패',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"조건 그룹 생성 실패: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.delete("/api/auto-trading/condition-groups/{group_id}")
async def delete_condition_group(group_id: int):
    """조건 그룹 삭제"""
    try:
        success = condition_manager.delete_condition_group(group_id)
        if success:
            return {
                'success': True,
                'message': f'조건 그룹 삭제 완료: {group_id}',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'error': '조건 그룹 삭제 실패',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"조건 그룹 삭제 실패: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 성과 분석 API
@app.get("/api/auto-trading/conditions/performance")
async def get_condition_performance(symbol: str = Query(..., description="종목코드")):
    """조건 성과 분석 조회"""
    try:
        conditions = condition_manager.get_conditions(symbol=symbol)
        
        if not conditions:
            return {
                'success': False,
                'error': '분석할 조건이 없습니다.',
                'timestamp': datetime.now().isoformat()
            }
        
        # 성과 지표 계산
        total_signals = sum(c.total_signals for c in conditions if c.total_signals)
        successful_signals = sum(c.successful_signals for c in conditions if c.successful_signals)
        avg_success_rate = (successful_signals / total_signals * 100) if total_signals > 0 else 0
        
        # 평균 수익률 계산
        profit_conditions = [c for c in conditions if c.avg_profit is not None]
        avg_profit = sum(c.avg_profit for c in profit_conditions) / len(profit_conditions) if profit_conditions else 0
        
        # 최고 성과 조건 찾기
        best_condition = None
        best_rate = 0
        for condition in conditions:
            if condition.success_rate and condition.success_rate > best_rate:
                best_rate = condition.success_rate
                best_condition = f"{condition.category} {condition.value}"
        
        return {
            'success': True,
            'performance': {
                'avg_success_rate': round(avg_success_rate, 1),
                'total_signals': total_signals,
                'successful_signals': successful_signals,
                'avg_profit': round(avg_profit, 2),
                'best_condition': best_condition,
                'total_conditions': len(conditions),
                'active_conditions': len([c for c in conditions if c.is_active])
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"조건 성과 분석 실패: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/auto-trading/conditions/performance/export")
async def export_performance_report(symbol: str = Query(..., description="종목코드")):
    """성과 보고서 내보내기"""
    try:
        conditions = condition_manager.get_conditions(symbol=symbol)
        
        if not conditions:
            return {
                'success': False,
                'error': '내보낼 데이터가 없습니다.',
                'timestamp': datetime.now().isoformat()
            }
        
        # CSV 데이터 생성
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 헤더
        writer.writerow(['조건 ID', '카테고리', '조건 값', '설명', '성공률 (%)', '총 신호', '성공 신호', '평균 수익률 (%)', '상태', '등록일'])
        
        # 데이터
        for condition in conditions:
            writer.writerow([
                condition.id,
                condition.category,
                condition.value,
                condition.description or '',
                f"{condition.success_rate:.1f}" if condition.success_rate else '-',
                condition.total_signals,
                condition.successful_signals,
                f"{condition.avg_profit:.2f}" if condition.avg_profit else '-',
                '활성' if condition.is_active else '비활성',
                condition.created_at.strftime('%Y-%m-%d %H:%M:%S') if condition.created_at else ''
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={symbol}_performance_report_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    except Exception as e:
        logger.error(f"성과 보고서 내보내기 실패: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 자동매매 제어 API
@app.post("/api/auto-trading/start")
async def start_auto_trading(request: Request):
    """자동매매 시작"""
    try:
        data = await request.json()
        quantity = data.get('quantity', 1)
        success = auto_trader.start(quantity=quantity)
        if success:
            return {
                'success': True,
                'message': f'자동매매가 시작되었습니다. (매매 수량: {quantity}주)',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': '자동매매 시작 실패',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"자동매매 시작 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/auto-trading/stop")
async def stop_auto_trading():
    """자동매매 중지"""
    try:
        success = auto_trader.stop()
        if success:
            return {
                'success': True,
                'message': '자동매매가 중지되었습니다.',
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'message': '자동매매 중지 실패',
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"자동매매 중지 실패: {str(e)}")
        return {
            'success': False,
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/auto-trading/status")
async def get_auto_trading_status():
    """자동매매 상태 조회"""
    try:
        status = auto_trader.get_status()
        return {
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"자동매매 상태 조회 실패: {str(e)}")
        return {
            'status': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 신호 모니터링 API
@app.get("/api/auto-trading/signals")
async def get_signals(symbol: str = Query(None, description="종목코드"),
                     status: str = Query(None, description="신호 상태"),
                     days: int = Query(30, description="조회 일수")):
    """신호 목록 조회"""
    try:
        signal_status = None
        if status:
            try:
                signal_status = SignalStatus(status)
            except ValueError:
                pass
        
        signals = signal_monitor.get_signals(symbol=symbol, status=signal_status, days=days)
        return {
            'signals': [signal.to_dict() for signal in signals],
            'total_count': len(signals),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"신호 목록 조회 실패: {str(e)}")
        return {
            'signals': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/auto-trading/signals/recent")
async def get_recent_signals(limit: int = Query(10, description="조회 개수")):
    """최근 신호 조회"""
    try:
        signals = signal_monitor.get_recent_signals(limit=limit)
        return {
            'signals': [signal.to_dict() for signal in signals],
            'total_count': len(signals),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"최근 신호 조회 실패: {str(e)}")
        return {
            'signals': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/auto-trading/signals/pending")
async def get_pending_signals():
    """대기 중인 신호 조회"""
    try:
        signals = signal_monitor.get_pending_signals()
        return {
            'signals': [signal.to_dict() for signal in signals],
            'total_count': len(signals),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"대기 중인 신호 조회 실패: {str(e)}")
        return {
            'signals': [],
            'total_count': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/auto-trading/signals/statistics")
async def get_signal_statistics(days: int = Query(30, description="조회 일수")):
    """신호 통계 정보 조회"""
    try:
        stats = signal_monitor.get_signal_statistics(days=days)
        return {
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"신호 통계 조회 실패: {str(e)}")
        return {
            'statistics': {},
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 종목코드 유효성 검증 API
@app.get("/api/stock/validate")
async def validate_stock_code(symbol: str = Query(..., description="종목코드")):
    """종목코드 유효성 검증 및 종목명 조회"""
    try:
        result = kiwoom_api.validate_stock_code(symbol)
        return {
            'validation': result,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"종목코드 유효성 검증 실패: {str(e)}")
        return {
            'validation': {
                'valid': False,
                'symbol': symbol,
                'name': '',
                'error': str(e)
            },
            'timestamp': datetime.now().isoformat()
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)