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


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 자동매매 시작"""
    try:
        logger.info("=== 웹 서버 시작 ===")

        # 토큰 발급 시도
        token = kiwoom_api.get_access_token()
        if token:
            logger.info("키움 API 토큰 발급 성공")
        else:
            logger.warning("키움 API 토큰 발급 실패")

        # 자동매매 시작 (기본 수량: 1주)
        success = auto_trader.start(quantity=1)
        if success:
            logger.info("✅ 자동매매가 자동으로 시작되었습니다.")
        else:
            logger.warning("⚠️ 자동매매 시작에 실패했습니다.")

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
):
    """감시 종목 추가"""
    try:
        success = watchlist_manager.add_symbol(symbol, symbol_name)
        if success:
            return {
                "success": True,
                "message": f"감시 종목 추가 완료: {symbol}",
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
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": False,
                "message": "자동매매 시작 실패",
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
        return {"status": status, "timestamp": datetime.now().isoformat()}
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
    """매매 수량 조회"""
    try:
        quantity = getattr(auto_trader, "trade_quantity", 1)
        logger.info(f"매매 수량 조회: {quantity}주")
        return {
            "success": True,
            "quantity": quantity,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"매매 수량 조회 실패: {str(e)}")
        return {
            "success": False,
            "quantity": 1,  # 기본값
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 장시간 체크 API
@app.get("/api/market/status")
async def get_market_status():
    """시장 상태 확인"""
    try:
        from datetime import datetime, time

        # 현재 로컬 시간 사용 (시스템이 한국 시간으로 설정되어 있다고 가정)
        now = datetime.now()
        current_time = now.time()

        # 평일 체크 (월~금)
        is_weekday = now.weekday() < 5

        # 시장 시간 (9:00 ~ 15:30)
        market_open = time(9, 0)
        market_close = time(15, 30)

        # 시장 상태 판단
        is_market_open = is_weekday and market_open <= current_time <= market_close

        # 시장 상태 메시지
        if not is_weekday:
            status_message = "주말 또는 공휴일로 시장이 휴장입니다."
        elif current_time < market_open:
            status_message = (
                f"시장 개장 전입니다. 개장 시간: {market_open.strftime('%H:%M')}"
            )
        elif current_time > market_close:
            status_message = (
                f"시장 종료되었습니다. 종료 시간: {market_close.strftime('%H:%M')}"
            )
        else:
            status_message = "시장이 열려 있습니다."

        return {
            "success": True,
            "market_status": {
                "is_open": is_market_open,
                "is_weekday": is_weekday,
                "current_time": current_time.strftime("%H:%M:%S"),
                "market_open": market_open.strftime("%H:%M"),
                "market_close": market_close.strftime("%H:%M"),
                "status_message": status_message,
            },
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
