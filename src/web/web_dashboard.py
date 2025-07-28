from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
import uvicorn
import json
from datetime import datetime, timedelta
import pytz
import asyncio

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
from src.auto_trading.symbol_selector import SymbolSelector

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
symbol_selector = SymbolSelector()

# 조건 검색 클라이언트 초기화
condition_search_client = None


def is_market_open() -> dict:
    """
    현재 시간이 장 시간인지 확인
    
    Returns:
        dict: 장 상태 정보
    """
    # 한국 시간대 설정
    korea_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(korea_tz)
    
    # 주말 확인
    if now.weekday() >= 5:  # 토요일(5), 일요일(6)
        return {
            "is_open": False,
            "reason": "주말",
            "next_open": _get_next_market_open(now),
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # 장 시간 확인 (9:00-15:30)
    market_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    if now < market_start:
        return {
            "is_open": False,
            "reason": "장 시작 전",
            "next_open": market_start.strftime("%Y-%m-%d %H:%M:%S"),
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S")
        }
    elif now > market_end:
        return {
            "is_open": False,
            "reason": "장 종료 후",
            "next_open": _get_next_market_open(now),
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        return {
            "is_open": True,
            "reason": "장 운영 중",
            "market_end": market_end.strftime("%Y-%m-%d %H:%M:%S"),
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S")
        }


def _get_next_market_open(current_time: datetime) -> str:
    """다음 장 시작 시간 계산"""
    korea_tz = pytz.timezone('Asia/Seoul')
    
    # 다음 영업일 계산
    next_day = current_time + timedelta(days=1)
    while next_day.weekday() >= 5:  # 주말이면 다음 날로
        next_day += timedelta(days=1)
    
    # 다음 장 시작 시간 (9:00)
    next_market_open = next_day.replace(hour=9, minute=0, second=0, microsecond=0)
    return next_market_open.strftime("%Y-%m-%d %H:%M:%S")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화"""
    try:
        logger.info("=== 웹 서버 시작 ===")

        # 토큰 발급 시도 (선택사항)
        try:
            token = kiwoom_api.get_access_token()
            if token:
                logger.info("키움 API 토큰 발급 성공")
            else:
                logger.warning("키움 API 토큰 발급 실패")
        except Exception as e:
            logger.warning(f"키움 API 토큰 발급 시도 중 오류: {e}")

        # 조건 검색 클라이언트 초기화 및 연결
        global condition_search_client
        try:
            condition_search_client = kiwoom_api.condition_search_client
            if condition_search_client and token:
                # 조건 검색 클라이언트에 토큰 설정
                condition_search_client.set_access_token(token)
                
                # 조건 검색 결과 콜백 설정
                async def on_condition_result(result_data):
                    try:
                        # 구조화된 결과 데이터 처리
                        condition_name = result_data.get('condition_name', '알 수 없는 조건')
                        symbol = result_data.get('symbol', '')
                        symbol_name = result_data.get('symbol_name', '')
                        current_price = result_data.get('current_price', 0)
                        price_change = result_data.get('price_change', 0)
                        volume = result_data.get('volume', 0)
                        signal_type = result_data.get('signal_type', 'UNKNOWN')
                        timestamp = result_data.get('timestamp', '')
                        
                        # 상세 로그 기록
                        logger.info(f"🔍 조건 검색 결과 수신:")
                        logger.info(f"   - 조건식: {condition_name}")
                        logger.info(f"   - 종목: {symbol_name} ({symbol})")
                        logger.info(f"   - 현재가: {current_price:,}원")
                        logger.info(f"   - 등락률: {price_change:+.2f}%")
                        logger.info(f"   - 거래량: {volume:,}")
                        logger.info(f"   - 신호: {signal_type}")
                        logger.info(f"   - 시간: {timestamp}")
                        
                        # 여기서 조건 검색 결과를 추가로 처리할 수 있습니다
                        # 예: 데이터베이스 저장, 알림 발송, 자동매매 신호 생성 등
                        
                    except Exception as e:
                        logger.error(f"조건 검색 결과 처리 중 오류: {e}")
                
                condition_search_client.set_callback(on_condition_result)
                
                # WebSocket 연결 시도 (타임아웃 설정)
                try:
                    # 연결 시도 (최대 10초 대기)
                    connect_task = asyncio.create_task(condition_search_client.connect())
                    await asyncio.wait_for(connect_task, timeout=10.0)
                    
                    if condition_search_client.connected:
                        # 백그라운드에서 메시지 수신 (중복 실행 방지)
                        if not condition_search_client.receive_task or condition_search_client.receive_task.done():
                            asyncio.create_task(condition_search_client.receive_messages())
                        logger.info("조건 검색 클라이언트 초기화 및 연결 완료")
                    else:
                        logger.warning("조건 검색 WebSocket 연결 실패")
                except asyncio.TimeoutError:
                    logger.warning("조건 검색 WebSocket 연결 시간 초과")
                except Exception as e:
                    logger.warning(f"조건 검색 WebSocket 연결 중 오류: {e}")
            else:
                logger.warning("조건 검색 클라이언트 초기화 실패")
        except Exception as e:
            logger.warning(f"조건 검색 클라이언트 초기화 중 오류: {e}")

        # 자동매매는 수동으로 시작하도록 변경
        logger.info("✅ 웹 서버가 성공적으로 시작되었습니다.")
        logger.info("📝 자동매매를 시작하려면 /api/auto-trading/start API를 호출하세요.")

    except Exception as e:
        logger.error(f"서버 시작 중 오류: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 자동매매 중지"""
    try:
        if auto_trader.is_running:
            auto_trader.stop()
            logger.info("✅ 자동매매가 중지되었습니다.")
        logger.info("=== 웹 서버 종료 ===")
    except Exception as e:
        logger.error(f"서버 종료 중 오류: {e}")


@app.get("/")
async def home():
    return FileResponse("templates/dashboard.html")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("static/favicon.svg")


@app.get("/api/test")
async def test():
    return {"message": "서버 동작 중", "status": "success"}


# 키움 API 토큰 발급
@app.get("/api/kiwoom/token")
async def get_kiwoom_token():
    try:
        token = kiwoom_api.get_access_token()
        if token:
            return {
                "status": "success",
                "message": "토큰 발급 성공",
                "token": token[:20] + "..." if len(token) > 20 else token,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "error",
                "message": "토큰 발급 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"키움 API 토큰 발급 실패: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 키움 API 상태 확인
@app.get("/api/kiwoom/status")
async def get_kiwoom_status():
    try:
        # 토큰 발급 시도
        token = kiwoom_api.get_access_token()
        if token:
            return {
                "status": "connected",
                "message": "키움 API 연결 성공",
                "simulation": kiwoom_api.is_simulation,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "disconnected",
                "message": "키움 API 연결 실패",
                "simulation": kiwoom_api.is_simulation,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"키움 API 상태 확인 실패: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "simulation": kiwoom_api.is_simulation,
            "timestamp": datetime.now().isoformat(),
        }


# 계좌 정보 API
@app.get("/api/account/balance")
async def get_account_balance():
    try:
        balance_data = kiwoom_api.get_account_balance_kt00018()
        if not balance_data:
            logger.warning("계좌 잔고 데이터가 없습니다.")
            return {
                "output": [],
                "total_count": 0,
                "error": "계좌 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }
        return balance_data
    except Exception as e:
        logger.error(f"계좌 잔고 조회 실패: {str(e)}")
        return {
            "output": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 관심종목 API
@app.get("/api/watchlist")
async def get_watchlist():
    try:
        logger.info("관심종목 조회 API 호출")
        watchlist = kiwoom_api.get_watchlist()
        if not watchlist or "watchlist" not in watchlist:
            return {
                "watchlist": [],
                "total_count": 0,
                "error": "관심종목 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }
        logger.info(f"관심종목 조회 결과: {watchlist}")
        return watchlist
    except Exception as e:
        logger.error(f"관심종목 조회 실패: {str(e)}")
        return {
            "watchlist": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
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
        symbols = [
            "A005935",
            "A090435",
            "A005380",
            "A000660",
        ]  # 삼성전자, 현대차, 현대모비스, SK하이닉스

        for symbol in symbols:
            try:
                trades = kiwoom_api.get_execution_history_by_date(
                    symbol, start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")
                )
                if trades and "output" in trades and trades["output"]:
                    # 종목 정보 추가
                    for trade in trades["output"]:
                        if isinstance(trade, dict):
                            trade["symbol"] = symbol
                            trade["symbol_name"] = _get_symbol_name(symbol)
                    all_trades.extend(trades["output"])
            except Exception as e:
                logger.warning(f"종목 {symbol} 체결 내역 조회 실패: {e}")
                continue

        # 날짜순으로 정렬
        all_trades.sort(key=lambda x: x.get("exec_dt", ""), reverse=True)

        return {
            "output": all_trades,
            "total_count": len(all_trades),
            "date_range": f"{start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}",
            "symbols": symbols,
        }
    except Exception as e:
        logger.error(f"거래 내역 조회 실패: {str(e)}")
        return {
            "output": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 체결 내역 API
@app.get("/api/execution/history")
async def get_execution_history(stk_cd: str = Query(..., description="종목코드")):
    try:
        execution_data = kiwoom_api.get_execution_history(stk_cd)
        if not execution_data:
            return {
                "output": [],
                "total_count": 0,
                "error": "체결 내역 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }
        return execution_data
    except Exception as e:
        logger.error(f"체결 내역 조회 실패: {str(e)}")
        return {
            "output": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 키움 체결 내역 API (JavaScript에서 호출하는 URL)
@app.get("/api/kiwoom/execution-history")
async def get_kiwoom_execution_history(
    stk_cd: str = Query(..., description="종목코드")
):
    try:
        execution_data = kiwoom_api.get_execution_history(stk_cd)
        if not execution_data:
            return {
                "output": [],
                "total_count": 0,
                "error": "체결 내역 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }
        return execution_data
    except Exception as e:
        logger.error(f"키움 체결 내역 조회 실패: {str(e)}")
        return {
            "output": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


def _get_symbol_name(symbol: str) -> str:
    """종목코드로 종목명 반환"""
    symbol_names = {
        "A005935": "삼성전자",
        "A090435": "현대차",
        "A005380": "현대모비스",
        "A000660": "SK하이닉스",
        "005935": "삼성전자",
        "090435": "현대차",
        "005380": "현대모비스",
        "000660": "SK하이닉스",
    }
    return symbol_names.get(symbol, symbol)


# 매매 신호 API
@app.get("/api/trading/signals")
async def get_trading_signals(symbol: str = Query(..., description="종목코드")):
    try:
        # 과거 데이터를 가져와서 기술적 지표 계산
        historical_data = data_collector.get_historical_data(symbol)
        if historical_data is not None:
            signals_data = data_collector.calculate_technical_indicators(
                historical_data
            )
            return {
                "symbol": symbol,
                "signals": (
                    signals_data.to_dict("records") if signals_data is not None else []
                ),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "symbol": symbol,
                "signals": [],
                "timestamp": datetime.now().isoformat(),
                "message": "데이터 없음",
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
            order_type=(
                OrderType.BUY if order_data["action"] == "buy" else OrderType.SELL
            ),
            quantity=order_data["quantity"],
            price=order_data["price"],
            price_type=OrderPriceType(order_data["price_type"]),
        )

        result = order_executor.place_order(order_request)

        # 상세 로깅 추가
        logger.info(f"=== 주문 API 응답 처리 ===")
        logger.info(f"OrderResult: {result}")
        logger.info(f"Result status: {result.status.value if result else 'None'}")
        logger.info(f"Result message: {result.message if result else 'None'}")

        # 프론트엔드가 기대하는 형식으로 응답
        if result and result.status.value not in ["거부", "REJECTED"]:
            response = {
                "success": True,
                "order_id": result.order_id,
                "message": result.message or "주문 접수 완료",
            }
            logger.info(f"✅ 주문 성공 응답: {response}")
            return response
        else:
            response = {
                "success": False,
                "message": result.message if result else "주문 접수 실패",
            }
            logger.error(f"❌ 주문 실패 응답: {response}")
            return response
    except Exception as e:
        logger.error(f"주문 실행 실패: {str(e)}")
        response = {"success": False, "message": str(e)}
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


# 실제 주문 테스트 API
@app.post("/api/orders/test")
async def test_real_order():
    try:
        # 테스트용 주문 데이터 (SGA 1주 시장가 매수)
        symbol = "A049470"  # SGA
        quantity = 1
        price = 0  # 시장가
        order_type = "01"  # 매수
        price_type = "03"  # 시장가

        logger.info(f"실제 주문 테스트: {symbol} - {order_type} {quantity}주 @ 시장가")

        result = kiwoom_api.place_order(symbol, quantity, price, order_type, price_type)

        if result:
            logger.info(f"실제 주문 테스트 성공: {symbol}")
            return {
                "status": "success",
                "message": "실제 주문 테스트 성공",
                "order_data": result,
                "symbol": symbol,
                "quantity": quantity,
                "order_type": "매수",
                "price_type": "시장가",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            logger.error(f"실제 주문 테스트 실패: {symbol}")
            return {
                "status": "error",
                "message": "실제 주문 테스트 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"실제 주문 테스트 중 오류: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


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
        if not result or "output" not in result:
            return {
                "output": [],
                "error": "실현손익 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }
        return result
    except Exception as e:
        logger.error(f"실현손익 조회 실패: {str(e)}")
        return {"output": [], "error": str(e), "timestamp": datetime.now().isoformat()}


# 토큰 상태 API
@app.get("/api/auth/token/status")
async def get_token_status():
    """토큰 상태 확인"""
    try:
        status = kiwoom_api.get_token_status()
        return {
            "success": True,
            "token_status": status,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"토큰 상태 확인 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auth/token/refresh")
async def refresh_token():
    """토큰 강제 갱신"""
    try:
        success = kiwoom_api.force_refresh_token()
        if success:
            return {
                "success": True,
                "message": "토큰 갱신 성공",
                "token_status": kiwoom_api.get_token_status(),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "토큰 갱신 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"토큰 갱신 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
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
                "current_price": None,
                "error": "현재가 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }

        # KiwoomAPI의 get_stock_price 응답 형식에 맞게 처리
        if "output" in result and result["output"]:
            output = (
                result["output"][0]
                if isinstance(result["output"], list)
                else result["output"]
            )
            current_price = output.get("prpr", None)
            logger.info(f"현재가 추출: {symbol} - {current_price}")

            if current_price and current_price != "0":
                return {
                    "current_price": float(current_price),
                    "change_rate": output.get("diff_rt", "0"),
                    "timestamp": datetime.now().isoformat(),
                }

        logger.warning(f"현재가 데이터 없음: {symbol}")
        return {
            "current_price": None,
            "error": "현재가 데이터 없음",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"현재가 조회 실패: {symbol} - {str(e)}")
        return {
            "current_price": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 체결잔고요청 API (kt00005)
@app.get("/api/execution/balance")
async def get_execution_balance(
    dmst_stex_tp: str = Query("KRX", description="국내거래소구분"),
    cont_yn: str = Query("N", description="연속조회여부"),
    next_key: str = Query("", description="연속조회키"),
):
    try:
        execution_balance = kiwoom_api.get_execution_balance_kt00005(
            dmst_stex_tp, cont_yn, next_key
        )
        if not execution_balance:
            return {
                "output": [],
                "total_count": 0,
                "error": "체결잔고 데이터 없음",
                "timestamp": datetime.now().isoformat(),
            }
        return execution_balance
    except Exception as e:
        logger.error(f"체결잔고 조회 실패: {str(e)}")
        return {
            "output": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 감시 종목 관리 API
@app.get("/api/auto-trading/watchlist")
async def get_watchlist():
    """감시 종목 목록 조회"""
    try:
        items = watchlist_manager.get_all_symbols()
        return {
            "items": [item.to_dict() for item in items],
            "total_count": len(items),
            "statistics": watchlist_manager.get_statistics(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"감시 종목 목록 조회 실패: {str(e)}")
        return {
            "items": [],
            "total_count": 0,
            "statistics": {},
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/watchlist")
async def add_to_watchlist(
    symbol: str = Query(..., description="종목코드"),
    symbol_name: str = Query(None, description="종목명"),
    is_test: bool = Query(False, description="테스트 데이터 여부"),
):
    """감시 종목 추가"""
    try:
        success = watchlist_manager.add_symbol(symbol, symbol_name, is_test)
        if success:
            test_flag = " (테스트)" if is_test else ""
            return {
                "success": True,
                "message": f"감시 종목 추가 완료: {symbol}{test_flag}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"감시 종목 추가 실패: {symbol}",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"감시 종목 추가 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.delete("/api/auto-trading/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """감시 종목 제거"""
    try:
        success = watchlist_manager.remove_symbol(symbol)
        if success:
            return {
                "success": True,
                "message": f"감시 종목 제거 완료: {symbol}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"감시 종목 제거 실패: {symbol}",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"감시 종목 제거 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.put("/api/auto-trading/watchlist/{symbol}")
async def update_watchlist_item(
    symbol: str,
    symbol_name: str = Query(None, description="종목명"),
    is_active: bool = Query(None, description="활성화 여부"),
):
    """감시 종목 정보 수정"""
    try:
        success = watchlist_manager.update_symbol(symbol, symbol_name, is_active)
        if success:
            return {
                "success": True,
                "message": f"감시 종목 수정 완료: {symbol}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"감시 종목 수정 실패: {symbol}",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"감시 종목 수정 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/watchlist/statistics")
async def get_watchlist_statistics():
    """감시 종목 통계 정보 조회"""
    try:
        stats = watchlist_manager.get_statistics()
        return {"statistics": stats, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"감시 종목 통계 조회 실패: {str(e)}")
        return {
            "statistics": {},
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/watchlist/user-symbols")
async def get_user_symbols():
    """사용자가 직접 등록한 종목명 목록 조회"""
    try:
        user_symbols = watchlist_manager.get_user_symbols()
        return {
            "user_symbols": user_symbols,
            "count": len(user_symbols),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"사용자 등록 종목 조회 실패: {str(e)}")
        return {
            "user_symbols": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/watchlist/test-symbols")
async def get_test_symbols():
    """테스트 종목명 목록 조회"""
    try:
        test_symbols = watchlist_manager.get_test_symbols()
        return {
            "test_symbols": test_symbols,
            "count": len(test_symbols),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"테스트 종목 조회 실패: {str(e)}")
        return {
            "test_symbols": [],
            "count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/watchlist/cleanup-test")
async def cleanup_test_data():
    """테스트 데이터 정리"""
    try:
        deleted_count = watchlist_manager.cleanup_test_data()
        return {
            "success": True,
            "message": f"테스트 데이터 정리 완료: {deleted_count}개 삭제",
            "deleted_count": deleted_count,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"테스트 데이터 정리 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 매수/매도 조건 관리 API
@app.get("/api/auto-trading/conditions")
async def get_conditions(
    symbol: str = Query(None, description="종목코드"),
    condition_type: str = Query(None, description="조건 타입 (buy/sell)"),
):
    """매수/매도 조건 목록 조회"""
    try:
        items = condition_manager.get_conditions(
            symbol=symbol, condition_type=condition_type
        )
        return {
            "items": [item.to_dict() for item in items],
            "total_count": len(items),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"매수/매도 조건 목록 조회 실패: {str(e)}")
        return {
            "items": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/conditions")
async def add_condition(
    symbol: str = Query(..., description="종목코드"),
    condition_type: str = Query(..., description="조건 타입 (buy/sell)"),
    category: str = Query("custom", description="조건 카테고리"),
    value: str = Query(..., description="조건 값"),
    description: str = Query("", description="조건 설명"),
):
    """매수/매도 조건 추가"""
    try:
        success = condition_manager.add_condition(
            symbol, condition_type, category, value, description
        )
        if success:
            return {
                "success": True,
                "message": f"조건 추가 완료: {symbol} {condition_type}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"조건 추가 실패: {symbol} {condition_type}",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"매수/매도 조건 추가 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.delete("/api/auto-trading/conditions/{condition_id}")
async def remove_condition(condition_id: int):
    """매수/매도 조건 삭제"""
    try:
        success = condition_manager.remove_condition(condition_id)
        if success:
            return {
                "success": True,
                "message": f"조건 삭제 완료: {condition_id}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"조건 삭제 실패: {condition_id}",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"매수/매도 조건 삭제 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.put("/api/auto-trading/conditions/{condition_id}")
async def update_condition(
    condition_id: int,
    value: str = Query(None, description="조건 값"),
    description: str = Query(None, description="조건 설명"),
    is_active: bool = Query(None, description="활성화 여부"),
):
    """매수/매도 조건 수정"""
    try:
        success = condition_manager.update_condition(
            condition_id, value, description, is_active
        )
        if success:
            return {
                "success": True,
                "message": f"조건 수정 완료: {condition_id}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": f"조건 수정 실패: {condition_id}",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"매수/매도 조건 수정 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/conditions/{condition_id}/backtest")
async def backtest_condition(condition_id: int):
    """조건 백테스트 실행"""
    try:
        condition = condition_manager.get_condition(condition_id)
        if not condition:
            return {
                "success": False,
                "error": "조건을 찾을 수 없습니다.",
                "timestamp": datetime.now().isoformat(),
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
                "success": True,
                "result": {
                    "success_rate": round(success_rate, 2),
                    "total_signals": total_signals,
                    "successful_signals": successful_signals,
                    "avg_profit": round(avg_profit, 2),
                },
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "백테스트 결과 저장 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"조건 백테스트 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 조건 그룹 관리 API
@app.get("/api/auto-trading/condition-groups")
async def get_condition_groups(symbol: str = Query(None, description="종목코드")):
    """조건 그룹 목록 조회"""
    try:
        groups = condition_manager.get_condition_groups(symbol=symbol)
        return {
            "groups": [group.to_dict() for group in groups],
            "total_count": len(groups),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"조건 그룹 목록 조회 실패: {str(e)}")
        return {
            "groups": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/condition-groups")
async def create_condition_group(
    symbol: str = Query(..., description="종목코드"),
    name: str = Query(..., description="그룹명"),
    logic: str = Query(..., description="로직 (AND/OR)"),
    priority: int = Query(5, description="우선순위"),
):
    """조건 그룹 생성"""
    try:
        group_id = condition_manager.create_condition_group(
            symbol, name, logic, priority
        )
        if group_id:
            return {
                "success": True,
                "group_id": group_id,
                "message": f"조건 그룹 생성 완료: {name}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "조건 그룹 생성 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"조건 그룹 생성 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.delete("/api/auto-trading/condition-groups/{group_id}")
async def delete_condition_group(group_id: int):
    """조건 그룹 삭제"""
    try:
        success = condition_manager.delete_condition_group(group_id)
        if success:
            return {
                "success": True,
                "message": f"조건 그룹 삭제 완료: {group_id}",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "error": "조건 그룹 삭제 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"조건 그룹 삭제 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 성과 분석 API
@app.get("/api/auto-trading/conditions/performance")
async def get_condition_performance(symbol: str = Query(..., description="종목코드")):
    """조건 성과 분석 조회"""
    try:
        conditions = condition_manager.get_conditions(symbol=symbol)

        if not conditions:
            return {
                "success": False,
                "error": "분석할 조건이 없습니다.",
                "timestamp": datetime.now().isoformat(),
            }

        # 성과 지표 계산
        total_signals = sum(c.total_signals for c in conditions if c.total_signals)
        successful_signals = sum(
            c.successful_signals for c in conditions if c.successful_signals
        )
        avg_success_rate = (
            (successful_signals / total_signals * 100) if total_signals > 0 else 0
        )

        # 평균 수익률 계산
        profit_conditions = [c for c in conditions if c.avg_profit is not None]
        avg_profit = (
            sum(c.avg_profit for c in profit_conditions) / len(profit_conditions)
            if profit_conditions
            else 0
        )

        # 최고 성과 조건 찾기
        best_condition = None
        best_rate = 0
        for condition in conditions:
            if condition.success_rate and condition.success_rate > best_rate:
                best_rate = condition.success_rate
                best_condition = f"{condition.category} {condition.value}"

        return {
            "success": True,
            "performance": {
                "avg_success_rate": round(avg_success_rate, 1),
                "total_signals": total_signals,
                "successful_signals": successful_signals,
                "avg_profit": round(avg_profit, 2),
                "best_condition": best_condition,
                "total_conditions": len(conditions),
                "active_conditions": len([c for c in conditions if c.is_active]),
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"조건 성과 분석 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/conditions/performance/export")
async def export_performance_report(symbol: str = Query(..., description="종목코드")):
    """성과 보고서 내보내기"""
    try:
        conditions = condition_manager.get_conditions(symbol=symbol)

        if not conditions:
            return {
                "success": False,
                "error": "내보낼 데이터가 없습니다.",
                "timestamp": datetime.now().isoformat(),
            }

        # CSV 데이터 생성
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # 헤더
        writer.writerow(
            [
                "조건 ID",
                "카테고리",
                "조건 값",
                "설명",
                "성공률 (%)",
                "총 신호",
                "성공 신호",
                "평균 수익률 (%)",
                "상태",
                "등록일",
            ]
        )

        # 데이터
        for condition in conditions:
            writer.writerow(
                [
                    condition.id,
                    condition.category,
                    condition.value,
                    condition.description or "",
                    f"{condition.success_rate:.1f}" if condition.success_rate else "-",
                    condition.total_signals,
                    condition.successful_signals,
                    f"{condition.avg_profit:.2f}" if condition.avg_profit else "-",
                    "활성" if condition.is_active else "비활성",
                    (
                        condition.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if condition.created_at
                        else ""
                    ),
                ]
            )

        csv_content = output.getvalue()
        output.close()

        from fastapi.responses import Response

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={symbol}_performance_report_{datetime.now().strftime('%Y%m%d')}.csv"
            },
        )
    except Exception as e:
        logger.error(f"성과 보고서 내보내기 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 자동매매 제어 API
@app.post("/api/auto-trading/start")
async def start_auto_trading(request: Request):
    """자동매매 시작"""
    try:
        # 장 시간 확인
        market_status = is_market_open()
        if not market_status["is_open"]:
            return {
                "success": False,
                "message": f"장이 열려있지 않습니다. ({market_status['reason']})",
                "market_status": market_status,
                "timestamp": datetime.now().isoformat(),
            }

        # 요청 본문이 비어있을 경우 기본값 사용
        try:
            data = await request.json()
            quantity = data.get("quantity", 1)
        except:
            quantity = 1

        success = auto_trader.start(quantity=quantity)
        if success:
            return {
                "success": True,
                "message": f"자동매매가 시작되었습니다. (매매 수량: {quantity}주)",
                "market_status": market_status,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "자동매매 시작 실패",
                "market_status": market_status,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"자동매매 시작 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/stop")
async def stop_auto_trading():
    """자동매매 중지"""
    try:
        success = auto_trader.stop()
        if success:
            return {
                "success": True,
                "message": "자동매매가 중지되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "자동매매 중지 실패",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"자동매매 중지 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/status")
async def get_auto_trading_status():
    """자동매매 상태 조회"""
    try:
        status = auto_trader.get_status()
        market_status = is_market_open()
        
        # 장이 닫혀있고 자동매매가 실행 중이면 자동으로 중지
        if not market_status["is_open"] and status.get("is_running", False):
            logger.info(f"장이 닫혀있어 자동매매를 자동으로 중지합니다. ({market_status['reason']})")
            auto_trader.stop()
            status = auto_trader.get_status()
        
        return {
            "status": status, 
            "market_status": market_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"자동매매 상태 조회 실패: {str(e)}")
        return {"status": {}, "error": str(e), "timestamp": datetime.now().isoformat()}


# 신호 모니터링 API
@app.get("/api/auto-trading/signals")
async def get_signals(
    symbol: str = Query(None, description="종목코드"),
    status: str = Query(None, description="신호 상태"),
    days: int = Query(30, description="조회 일수"),
):
    """신호 목록 조회"""
    try:
        signal_status = None
        if status:
            try:
                signal_status = SignalStatus(status)
            except ValueError:
                pass

        signals = signal_monitor.get_signals(
            symbol=symbol, status=signal_status, days=days
        )
        return {
            "signals": [signal.to_dict() for signal in signals],
            "total_count": len(signals),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"신호 목록 조회 실패: {str(e)}")
        return {
            "signals": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/signals/recent")
async def get_recent_signals(limit: int = Query(10, description="조회 개수")):
    """최근 신호 조회"""
    try:
        signals = signal_monitor.get_recent_signals(limit=limit)
        return {
            "signals": [signal.to_dict() for signal in signals],
            "total_count": len(signals),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"최근 신호 조회 실패: {str(e)}")
        return {
            "signals": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/signals/pending")
async def get_pending_signals():
    """대기 중인 신호 조회"""
    try:
        signals = signal_monitor.get_pending_signals()
        return {
            "signals": [signal.to_dict() for signal in signals],
            "total_count": len(signals),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"대기 중인 신호 조회 실패: {str(e)}")
        return {
            "signals": [],
            "total_count": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/signals/statistics")
async def get_signal_statistics(days: int = Query(30, description="조회 일수")):
    """신호 통계 정보 조회"""
    try:
        stats = signal_monitor.get_signal_statistics(days=days)
        return {"statistics": stats, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"신호 통계 조회 실패: {str(e)}")
        return {
            "statistics": {},
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 종목코드 유효성 검증 API
@app.get("/api/stock/validate")
async def validate_stock_code(symbol: str = Query(..., description="종목코드")):
    """종목코드 유효성 검증 및 종목명 조회"""
    try:
        result = kiwoom_api.validate_stock_code(symbol)
        return {"validation": result, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"종목코드 유효성 검증 실패: {str(e)}")
        return {
            "validation": {
                "valid": False,
                "symbol": symbol,
                "name": "",
                "error": str(e),
            },
            "timestamp": datetime.now().isoformat(),
        }


# 매매 모드 설정 API
@app.post("/api/auto-trading/mode")
async def set_trading_mode(
    test_mode: bool = Query(..., description="테스트 모드 여부")
):
    """매매 모드 설정 (테스트/실제)"""
    try:
        auto_trader.set_test_mode(test_mode)
        mode_text = "테스트 모드" if test_mode else "실제 매매"

        return {
            "success": True,
            "message": f"매매 모드가 {mode_text}로 변경되었습니다.",
            "test_mode": test_mode,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"매매 모드 설정 실패: {str(e)}")
        return {
            "success": False,
            "message": f"매매 모드 설정 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# 실행된 주문 내역 조회 API
@app.get("/api/auto-trading/executed-orders")
async def get_executed_orders(days: int = Query(1, description="조회 일수")):
    """실행된 주문 내역 조회"""
    try:
        # 실행된 신호들 조회
        executed_signals = signal_monitor.get_executed_signals(days=days)

        # 주문 내역 포맷팅
        orders = []
        for signal in executed_signals:
            orders.append(
                {
                    "id": signal.id,
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type,
                    "condition_value": signal.condition_value,
                    "executed_price": signal.executed_price,
                    "executed_quantity": signal.executed_quantity,
                    "executed_at": (
                        signal.executed_at.isoformat() if signal.executed_at else None
                    ),
                    "profit_loss": signal.profit_loss,
                    "rsi_value": signal.rsi_value,
                }
            )

        return {
            "success": True,
            "orders": orders,
            "total_count": len(orders),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"실행된 주문 내역 조회 실패: {str(e)}")
        return {
            "success": False,
            "message": f"주문 내역 조회 실패: {str(e)}",
            "orders": [],
            "total_count": 0,
            "timestamp": datetime.now().isoformat(),
        }


# 주문 쿨다운 설정 API
@app.post("/api/auto-trading/cooldown")
async def set_order_cooldown(
    minutes: int = Query(..., description="주문 쿨다운 시간 (분)")
):
    """주문 쿨다운 시간 설정"""
    try:
        result = auto_trader.set_order_cooldown(minutes)
        return {
            "success": True,
            "message": f"주문 쿨다운 시간이 {result['old_cooldown_minutes']}분에서 {result['new_cooldown_minutes']}분으로 변경되었습니다.",
            "old_cooldown_minutes": result["old_cooldown_minutes"],
            "new_cooldown_minutes": result["new_cooldown_minutes"],
            "new_cooldown_seconds": result["new_cooldown_seconds"],
            "timestamp": datetime.now().isoformat(),
        }
    except ValueError as e:
        logger.error(f"주문 쿨다운 설정 실패: {e}")
        return {
            "success": False,
            "message": f"주문 쿨다운 설정 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"주문 쿨다운 설정 실패: {e}")
        return {
            "success": False,
            "message": f"주문 쿨다운 설정 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# 일일 주문 제한 초기화 API
@app.post("/api/auto-trading/reset-daily-count")
async def reset_daily_order_count():
    """일일 주문 제한 카운터 초기화"""
    try:
        auto_trader._force_reset_daily_order_count()
        return {
            "success": True,
            "message": "일일 주문 제한 카운터가 초기화되었습니다.",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"일일 주문 제한 초기화 실패: {e}")
        return {
            "success": False,
            "message": f"일일 주문 제한 초기화 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# 자동매매 에러 조회 API
@app.get("/api/auto-trading/errors")
async def get_auto_trading_errors():
    """자동매매 에러 정보 조회"""
    try:
        last_error = auto_trader.get_last_error()
        return {
            "success": True,
            "has_error": last_error is not None,
            "error": last_error,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"자동매매 에러 조회 실패: {e}")
        return {
            "success": False,
            "has_error": False,
            "error": None,
            "message": f"에러 조회 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# 자동매매 에러 초기화 API
@app.post("/api/auto-trading/clear-error")
async def clear_auto_trading_error():
    """자동매매 에러 초기화"""
    try:
        auto_trader.clear_error()
        return {
            "success": True,
            "message": "에러가 초기화되었습니다.",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"자동매매 에러 초기화 실패: {e}")
        return {
            "success": False,
            "message": f"에러 초기화 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/cooldown")
async def get_order_cooldown():
    """주문 쿨다운 시간 조회"""
    try:
        minutes = auto_trader.get_order_cooldown_minutes()
        return {
            "success": True,
            "cooldown_minutes": minutes,
            "cooldown_seconds": auto_trader.order_cooldown,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"주문 쿨다운 조회 실패: {e}")
        return {
            "success": False,
            "message": f"주문 쿨다운 조회 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/quantity")
async def set_trade_quantity(quantity: int = Query(..., description="매매 수량")):
    """매매 수량 설정"""
    try:
        if quantity < 1:
            return {
                "success": False,
                "message": "매매 수량은 1 이상이어야 합니다.",
                "timestamp": datetime.now().isoformat(),
            }

        auto_trader.trade_quantity = quantity
        logger.info(f"매매 수량 설정: {quantity}주")

        return {
            "success": True,
            "message": f"매매 수량이 {quantity}주로 설정되었습니다.",
            "quantity": quantity,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"매매 수량 설정 실패: {str(e)}")
        return {
            "success": False,
            "message": f"매매 수량 설정 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/quantity")
async def get_trade_quantity():
    """현재 매매 수량 조회"""
    try:
        quantity = auto_trader.trade_quantity
        return {
            "quantity": quantity,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"매매 수량 조회 실패: {str(e)}")
        return {
            "quantity": 1,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 자동 종목 선정 API
@app.post("/api/auto-trading/symbol-selection/run")
async def run_symbol_selection():
    """자동 종목 선정 실행"""
    try:
        logger.info("자동 종목 선정 시작")
        
        # 종목 선정 실행
        selected_symbols = symbol_selector.select_symbols()
        
        if not selected_symbols:
            return {
                "success": False,
                "message": "선정 가능한 종목이 없습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        
        # 감시 종목 업데이트
        update_success = symbol_selector.update_watchlist(selected_symbols)
        
        if not update_success:
            return {
                "success": False,
                "message": "감시 종목 업데이트 실패",
                "timestamp": datetime.now().isoformat(),
            }
        
        # 선정 결과 요약
        summary = symbol_selector.get_selection_summary(selected_symbols)
        
        return {
            "success": True,
            "message": f"종목 선정 완료: {len(selected_symbols)}개 종목",
            "selected_count": len(selected_symbols),
            "summary": summary,
            "selected_symbols": [
                {
                    "symbol": s.symbol,
                    "symbol_name": s.symbol_name,
                    "sector": s.sector,
                    "score": round(s.score, 3),
                    "selection_reason": s.selection_reason,
                    "avg_volume": int(s.avg_volume),
                    "avg_price": int(s.avg_price),
                    "volatility": round(s.volatility * 100, 2),
                    "rsi": round(s.rsi, 2)
                }
                for s in selected_symbols
            ],
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"자동 종목 선정 실패: {str(e)}")
        return {
            "success": False,
            "message": f"종목 선정 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/auto-trading/symbol-selection/criteria")
async def get_selection_criteria():
    """종목 선정 기준 조회"""
    try:
        criteria = {
            "max_symbols": symbol_selector.max_symbols,
            "min_volume": symbol_selector.min_volume,
            "min_market_cap": symbol_selector.min_market_cap,
            "max_volatility": symbol_selector.max_volatility,
            "min_volatility": symbol_selector.min_volatility,
            "volatility_range_percent": f"{symbol_selector.min_volatility*100:.1f}% - {symbol_selector.max_volatility*100:.1f}%",
            "rsi_range": "20 - 80",
            "timestamp": datetime.now().isoformat(),
        }
        return criteria
        
    except Exception as e:
        logger.error(f"선정 기준 조회 실패: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/auto-trading/symbol-selection/criteria")
async def update_selection_criteria(
    max_symbols: int = Query(15, description="최대 선정 종목 수"),
    min_volume: int = Query(500000, description="최소 일평균 거래량"),
    min_market_cap: int = Query(1000000000000, description="최소 시가총액"),
    max_volatility: float = Query(0.15, description="최대 변동성"),
    min_volatility: float = Query(0.02, description="최소 변동성"),
):
    """종목 선정 기준 업데이트"""
    try:
        # 기준 업데이트
        symbol_selector.max_symbols = max_symbols
        symbol_selector.min_volume = min_volume
        symbol_selector.min_market_cap = min_market_cap
        symbol_selector.max_volatility = max_volatility
        symbol_selector.min_volatility = min_volatility
        
        logger.info(f"종목 선정 기준 업데이트: 최대 {max_symbols}개, 거래량 {min_volume:,}주 이상")
        
        return {
            "success": True,
            "message": "선정 기준이 업데이트되었습니다.",
            "criteria": {
                "max_symbols": max_symbols,
                "min_volume": min_volume,
                "min_market_cap": min_market_cap,
                "max_volatility": max_volatility,
                "min_volatility": min_volatility,
            },
            "timestamp": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"선정 기준 업데이트 실패: {str(e)}")
        return {
            "success": False,
            "message": f"기준 업데이트 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


# 장시간 체크 API
@app.get("/api/market/status")
async def get_market_status():
    """시장 상태 확인"""
    try:
        market_status = is_market_open()
        return {
            "success": True,
            "market_status": market_status,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"시장 상태 확인 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 에러 상황 체크 API
@app.get("/api/system/errors")
async def get_system_errors():
    """시스템 에러 상황 체크"""
    try:
        errors = []

        # 1. 토큰 상태 체크 (실제 API 호출로 검증)
        try:
            # 실제 토큰 유효성 검증
            if not kiwoom_api.is_token_valid():
                errors.append(
                    {
                        "type": "token",
                        "level": "error",
                        "message": "토큰이 유효하지 않습니다. 토큰을 갱신해주세요.",
                        "action": "refresh_token",
                    }
                )
        except Exception as e:
            errors.append(
                {
                    "type": "token",
                    "level": "error",
                    "message": f"토큰 상태 확인 실패: {str(e)}",
                    "action": "refresh_token",
                }
            )

        # 2. 시장 상태 체크
        try:
            market_response = await get_market_status()
            if market_response.get("success") and market_response.get("market_status"):
                market_status = market_response["market_status"]
                if not market_status.get("is_open", False):
                    errors.append(
                        {
                            "type": "market",
                            "level": "warning",
                            "message": market_status.get(
                                "status_message", "시장이 열려 있지 않습니다."
                            ),
                            "action": "check_market",
                        }
                    )
        except Exception as e:
            errors.append(
                {
                    "type": "market",
                    "level": "warning",
                    "message": f"시장 상태 확인 실패: {str(e)}",
                    "action": "check_market",
                }
            )

        # 3. 자동매매 상태 체크
        try:
            if auto_trader.is_running:
                # 자동매매가 실행 중인데 에러가 있는 경우
                if not kiwoom_api.is_token_valid():
                    errors.append(
                        {
                            "type": "general",
                            "level": "error",
                            "message": "자동매매가 실행 중이지만 토큰이 유효하지 않습니다.",
                            "action": "stop_trading",
                        }
                    )
        except Exception as e:
            errors.append(
                {
                    "type": "general",
                    "level": "error",
                    "message": f"자동매매 상태 확인 실패: {str(e)}",
                    "action": "check_system",
                }
            )

        return {
            "success": True,
            "errors": errors,
            "error_count": len(errors),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"시스템 에러 체크 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 조건 검색 API
@app.get("/api/condition-search/list")
async def get_condition_search_list():
    """조건 검색식 목록 조회"""
    try:
        global condition_search_client
        
        if condition_search_client and condition_search_client.connected:
            # WebSocket 클라이언트를 통한 조건 검색식 목록 조회
            try:
                conditions = await condition_search_client.get_condition_list()
                
                if conditions:
                    return {
                        "success": True,
                        "conditions": conditions,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    logger.warning("WebSocket을 통한 조건 검색식 목록이 비어있습니다.")
            except Exception as ws_error:
                logger.warning(f"WebSocket 조건 검색식 목록 조회 실패: {ws_error}")
        
        # WebSocket 연결이 안 되었거나 실패한 경우 기존 API 방식으로 폴백
        logger.info("기존 API 방식으로 조건 검색식 목록 조회 시도")
        response = await kiwoom_api.get_condition_search_list()
        
        if response.get("success"):
            return {
                "success": True,
                "conditions": response.get("data", []),
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": response.get("message", "조건 검색식 목록 조회 실패"),
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"조건 검색식 목록 조회 실패: {str(e)}")
        return {
            "success": False,
            "message": f"조건 검색식 목록 조회 실패: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/condition-search/register")
async def register_condition_search(condition_seq: str = Form(..., description="조건 검색식 일련번호")):
    """조건 검색식 등록"""
    try:
        global condition_search_client
        
        if condition_search_client and condition_search_client.connected:
            # WebSocket 클라이언트를 통한 조건 검색식 등록
            try:
                success = await condition_search_client.register_condition(condition_seq)
                
                if success:
                    return {
                        "success": True,
                        "message": "조건 검색식이 등록되었습니다.",
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    logger.warning(f"WebSocket을 통한 조건 검색식 등록 실패: {condition_seq}")
            except Exception as ws_error:
                logger.warning(f"WebSocket 조건 검색식 등록 오류: {ws_error}")
        
        # WebSocket 연결이 안 되었거나 실패한 경우 기존 API 방식으로 폴백
        logger.info("기존 API 방식으로 조건 검색식 등록 시도")
        response = await kiwoom_api.register_condition_search(condition_seq)
        
        if response.get("success"):
            return {
                "success": True,
                "message": "조건 검색식이 등록되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": response.get("message", "조건 검색식 등록 실패"),
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"조건 검색식 등록 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.delete("/api/condition-search/unregister")
async def unregister_condition_search(condition_seq: str = Form(..., description="조건 검색식 일련번호")):
    """조건 검색식 해제"""
    try:
        global condition_search_client
        
        if condition_search_client and condition_search_client.connected:
            # WebSocket 클라이언트를 통한 조건 검색식 해제
            try:
                success = await condition_search_client.unregister_condition(condition_seq)
                
                if success:
                    return {
                        "success": True,
                        "message": "조건 검색식이 해제되었습니다.",
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    logger.warning(f"WebSocket을 통한 조건 검색식 해제 실패: {condition_seq}")
            except Exception as ws_error:
                logger.warning(f"WebSocket 조건 검색식 해제 오류: {ws_error}")
        
        # WebSocket 연결이 안 되었거나 실패한 경우 기존 API 방식으로 폴백
        logger.info("기존 API 방식으로 조건 검색식 해제 시도")
        response = await kiwoom_api.unregister_condition_search(condition_seq)
        
        if response.get("success"):
            return {
                "success": True,
                "message": "조건 검색식이 해제되었습니다.",
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": response.get("message", "조건 검색식 해제 실패"),
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error(f"조건 검색식 해제 실패: {str(e)}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.post("/api/condition-search/connect")
async def connect_condition_search():
    """조건 검색 WebSocket 연결"""
    try:
        global condition_search_client
        
        if not condition_search_client:
            return {
                "success": False,
                "message": "조건 검색 클라이언트가 초기화되지 않았습니다.",
                "timestamp": datetime.now().isoformat()
            }
        
        # 토큰 확인
        token = kiwoom_api.get_access_token()
        if not token:
            return {
                "success": False,
                "message": "키움 API 토큰이 없습니다.",
                "timestamp": datetime.now().isoformat()
            }
        
        # WebSocket 연결 시도
        if await condition_search_client.connect():
            # 백그라운드에서 메시지 수신 시작 (중복 실행 방지)
            if not condition_search_client.receive_task or condition_search_client.receive_task.done():
                asyncio.create_task(condition_search_client.receive_messages())
            
            return {
                "success": True,
                "message": "조건 검색 WebSocket 연결 성공",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "message": "조건 검색 WebSocket 연결 실패",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"조건 검색 WebSocket 연결 실패: {e}")
        return {
            "success": False,
            "message": f"연결 실패: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
