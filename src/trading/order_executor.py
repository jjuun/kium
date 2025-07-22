"""
주문 실행 엔진
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass
from src.core.logger import logger
from src.core.config import Config
from src.api.kiwoom_api import KiwoomAPI


class OrderType(Enum):
    """주문 유형"""

    BUY = "매수"
    SELL = "매도"


class OrderStatus(Enum):
    """주문 상태"""

    PENDING = "접수대기"
    ACCEPTED = "접수완료"
    PARTIAL_FILLED = "부분체결"
    FILLED = "전체체결"
    CANCELLED = "취소"
    REJECTED = "거부"
    EXPIRED = "만료"


class OrderPriceType(Enum):
    """주문 가격 유형"""

    LIMIT = "00"  # 지정가
    MARKET = "01"  # 시장가
    CONDITIONAL = "02"  # 조건부지정가
    BEST_LIMIT = "03"  # 최유리지정가
    FIRST_LIMIT = "04"  # 최우선지정가


@dataclass
class OrderRequest:
    """주문 요청 데이터"""

    symbol: str
    order_type: OrderType
    quantity: int
    price: float
    price_type: OrderPriceType = OrderPriceType.LIMIT
    order_time: datetime = None

    def __post_init__(self):
        if self.order_time is None:
            self.order_time = datetime.now()
        # 주문 가격을 정수로 변환 (키움 API 요구사항)
        if self.price is not None:
            self.price = int(self.price)


@dataclass
class OrderResult:
    """주문 결과 데이터"""

    order_id: str
    symbol: str
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus
    filled_quantity: int = 0
    filled_price: float = 0.0
    order_time: datetime = None
    filled_time: datetime = None
    message: str = ""

    def __post_init__(self):
        if self.order_time is None:
            self.order_time = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "order_type_code": "01" if self.order_type == OrderType.BUY else "02",
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status.value,
            "status_code": self._get_status_code(),
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "order_time": self.order_time.isoformat() if self.order_time else None,
            "filled_time": self.filled_time.isoformat() if self.filled_time else None,
            "message": self.message,
            "total_amount": self.quantity * self.price,
            "filled_amount": self.filled_quantity * self.filled_price,
        }

    def _get_status_code(self) -> str:
        """상태 코드 반환"""
        status_map = {
            OrderStatus.PENDING: "01",
            OrderStatus.ACCEPTED: "02",
            OrderStatus.PARTIAL_FILLED: "03",
            OrderStatus.FILLED: "04",
            OrderStatus.CANCELLED: "05",
            OrderStatus.REJECTED: "06",
            OrderStatus.EXPIRED: "07",
        }
        return status_map.get(self.status, "01")


class OrderExecutor:
    """주문 실행 엔진"""

    def __init__(self):
        self.kiwoom_api = KiwoomAPI()
        self.pending_orders: Dict[str, OrderResult] = {}
        self.order_history: List[OrderResult] = []
        self.max_retry_count = 3
        self.retry_delay = 1  # 초

    def place_order(self, order_request: OrderRequest) -> Optional[OrderResult]:
        """
        주문 실행

        Args:
            order_request: 주문 요청 데이터

        Returns:
            OrderResult: 주문 결과
        """
        try:
            logger.info(f"=== 주문 실행 시작 ===")
            logger.info(
                f"주문 요청: {order_request.symbol} {order_request.order_type.value} {order_request.quantity}주 @ {int(order_request.price):,}원"
            )
            logger.info(
                f"가격 유형: {order_request.price_type.value} ({order_request.price_type.name})"
            )
            logger.info(f"주문 시간: {order_request.order_time}")

            # 주문 유효성 검증
            validation_result = self._validate_order(order_request)
            if not validation_result["valid"]:
                logger.error(
                    f"❌ 주문 유효성 검증 실패: {validation_result['message']}"
                )
                return self._create_rejected_order(
                    order_request, validation_result["message"]
                )

            logger.info(f"✅ 주문 유효성 검증 통과")

            # 주문 실행
            order_type_code = (
                "01" if order_request.order_type == OrderType.BUY else "02"
            )  # 매수:01, 매도:02

            logger.info(
                f"API 호출 시작 - 주문 유형: {order_type_code} ({'매수' if order_type_code == '01' else '매도'})"
            )

            api_result = self.kiwoom_api.place_order(
                symbol=order_request.symbol,
                quantity=order_request.quantity,
                price=order_request.price,
                order_type=order_type_code,  # 주문 유형 (매수/매도)
                price_type=order_request.price_type.value,  # 주문 가격 유형 (지정가/시장가 등)
            )

            logger.info(f"=== API 응답 분석 ===")
            logger.info(f"API Result: {api_result}")

            # API 응답 분석 개선
            success = False
            order_id = None
            error_msg = "알 수 없는 오류"

            if api_result:
                # 실제 API 응답의 경우
                if api_result.get("rt_cd") == "0":
                    success = True
                    order_id = api_result.get("output", {}).get(
                        "KRX_FWDG_ORD_ORGNO", f"ORDER_{int(time.time())}"
                    )
                # 모의 주문의 경우 (API 응답이 없지만 성공으로 처리)
                elif api_result.get("success") or "모의 주문 성공" in str(api_result):
                    success = True
                    order_id = api_result.get("output", {}).get(
                        "KRX_FWDG_ORD_ORGNO", f"ORDER_{int(time.time())}"
                    )
                # 주문번호가 응답에 있는 경우 (성공으로 처리)
                elif api_result.get("output") and isinstance(
                    api_result["output"], dict
                ):
                    output = api_result["output"]
                    if output.get("ord_no") or output.get("KRX_FWDG_ORD_ORGNO"):
                        success = True
                        order_id = (
                            output.get("ord_no")
                            or output.get("KRX_FWDG_ORD_ORGNO")
                            or f"ORDER_{int(time.time())}"
                        )
                    else:
                        error_msg = api_result.get(
                            "msg1", api_result.get("message", "알 수 없는 오류")
                        )
                # 주문번호가 최상위에 있는 경우 (성공으로 처리)
                elif api_result.get("ord_no"):
                    success = True
                    order_id = api_result.get("ord_no")
                # return_code가 0인 경우 (성공으로 처리)
                elif api_result.get("return_code") == 0:
                    success = True
                    order_id = api_result.get("ord_no", f"ORDER_{int(time.time())}")
                # return_msg에 "완료"가 포함된 경우 (성공으로 처리)
                elif api_result.get("return_msg") and (
                    "완료" in api_result.get("return_msg")
                    or "성공" in api_result.get("return_msg")
                ):
                    success = True
                    order_id = api_result.get("ord_no", f"ORDER_{int(time.time())}")
                # 모의 주문 성공 메시지 확인
                elif isinstance(api_result, str) and "모의 주문 성공" in api_result:
                    success = True
                    order_id = f"ORDER_{int(time.time())}"
                else:
                    error_msg = api_result.get(
                        "msg1",
                        api_result.get(
                            "message", api_result.get("return_msg", "알 수 없는 오류")
                        ),
                    )
            else:
                error_msg = "API 응답 없음"

            logger.info(
                f"응답 분석 결과 - 성공: {success}, 주문ID: {order_id}, 에러: {error_msg}"
            )

            # 브라우저에서 볼 수 있도록 상세 로그 추가
            logger.info(f"🎯 주문 실행 결과: {'성공' if success else '실패'}")
            logger.info(
                f"📋 주문 정보: {order_request.symbol} {order_request.order_type.value} {order_request.quantity}주 @ {int(order_request.price):,}원"
            )
            logger.info(f"🆔 주문 ID: {order_id}")
            logger.info(
                f"📝 응답 메시지: {api_result.get('return_msg', api_result.get('message', 'N/A'))}"
            )
            logger.info(f"🔍 API 응답: {api_result}")

            if success:
                # 주문 성공
                order_result = OrderResult(
                    order_id=order_id,
                    symbol=order_request.symbol,
                    order_type=order_request.order_type,
                    quantity=order_request.quantity,
                    price=order_request.price,
                    status=OrderStatus.ACCEPTED,
                    order_time=order_request.order_time,
                    message="주문 접수 완료",
                )

                # 대기 주문 목록에 추가
                self.pending_orders[order_id] = order_result

                logger.info(
                    f"✅ 주문 접수 성공: {order_id} - {order_request.symbol} {order_request.order_type.value} {order_request.quantity}주 @ {int(order_request.price):,}원"
                )
                logger.info(f"주문 ID: {order_id}")
                logger.info(f"주문 상태: {order_result.status.value}")
                logger.info(f"현재 대기 주문 수: {len(self.pending_orders)}")

                # 브라우저 console 로그
                logger.info(f"✅ 주문 성공! ID: {order_id}")
                return order_result
            else:
                # 주문 실패
                logger.error(f"❌ 주문 실패: {order_request.symbol} - {error_msg}")
                logger.error(f"실패 상세: {api_result}")

                # 브라우저 console 로그
                logger.error(f"❌ 주문 실패: {error_msg}")
                return self._create_rejected_order(order_request, error_msg)

        except Exception as e:
            logger.error(f"❌ 주문 실행 중 오류: {e}")
            logger.error(f"Exception Details: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._create_rejected_order(order_request, str(e))

    def cancel_order(self, order_id: str) -> bool:
        """
        주문 취소

        Args:
            order_id: 주문 ID

        Returns:
            bool: 취소 성공 여부
        """
        try:
            logger.info(f"=== 주문 취소 시작 ===")
            logger.info(f"취소 요청 주문 ID: {order_id}")

            # 1. 로컬 pending_orders에서 주문 찾기
            order = None
            order_symbol = None
            order_quantity = None

            if order_id in self.pending_orders:
                order = self.pending_orders[order_id]
                order_symbol = order.symbol
                order_quantity = order.quantity
                logger.info(
                    f"로컬 주문 발견: {order.symbol} {order.order_type.value} {order.quantity}주 @ {order.price:,}원"
                )
                logger.info(f"현재 주문 상태: {order.status.value}")

                # 이미 체결된 주문은 취소 불가
                if order.status in [
                    OrderStatus.FILLED,
                    OrderStatus.CANCELLED,
                    OrderStatus.REJECTED,
                ]:
                    logger.warning(
                        f"⚠️ 이미 {order.status.value}된 주문은 취소할 수 없습니다: {order_id}"
                    )
                    return False
            else:
                # 2. 키움 API에서 주문 조회
                logger.info(f"로컬 주문 없음, 키움 API에서 주문 조회")
                logger.info(f"현재 대기 중인 주문: {list(self.pending_orders.keys())}")

                # 키움 API에서 미체결 주문 조회하여 해당 주문 찾기
                try:
                    api_result = self.kiwoom_api.get_pending_orders_from_api()

                    if api_result and api_result.get("return_code") == 0:
                        oso_data = api_result.get("oso", [])

                        # 해당 주문 ID 찾기
                        found_order = None
                        for order_data in oso_data:
                            if order_data.get("ord_no") == order_id:
                                found_order = order_data
                                break

                        if found_order:
                            # 키움 API에서 찾은 주문 정보 추출
                            order_symbol = found_order.get("stk_cd", "")
                            order_quantity = int(found_order.get("ord_qty", 0))
                            order_status = found_order.get("ord_sts_cd", "")

                            # A 접두사 추가
                            if order_symbol and not order_symbol.startswith("A"):
                                order_symbol = "A" + order_symbol

                            logger.info(
                                f"키움 API에서 주문 발견: {order_symbol} {order_quantity}주 (상태: {order_status})"
                            )

                            # 이미 체결되거나 취소된 주문은 취소 불가
                            if order_status in [
                                "03",
                                "04",
                                "05",
                            ]:  # 03:체결, 04:취소, 05:거부
                                status_text = {
                                    "03": "체결",
                                    "04": "취소",
                                    "05": "거부",
                                }.get(order_status, order_status)
                                logger.warning(
                                    f"⚠️ 이미 {status_text}된 주문은 취소할 수 없습니다: {order_id}"
                                )
                                return False
                        else:
                            logger.error(
                                f"❌ 키움 API에서도 주문을 찾을 수 없습니다: {order_id}"
                            )
                            return False
                    else:
                        logger.error(f"❌ 키움 API 주문 조회 실패")
                        return False

                except Exception as e:
                    logger.error(f"❌ 키움 API 주문 조회 중 오류: {e}")
                    return False

            logger.info(f"✅ 주문 취소 가능 - API 호출 시작")

            # API 호출하여 주문 취소
            api_result = self.kiwoom_api.cancel_order(
                order_no=order_id,
                symbol=order_symbol or "",
                quantity=order_quantity or 0,
            )

            logger.info(f"=== 취소 API 응답 분석 ===")
            logger.info(f"API Result: {api_result}")

            # 취소 API 응답 분석 개선
            success = False
            error_msg = "알 수 없는 오류"

            if api_result:
                # 실제 API 응답의 경우 (return_code 0 또는 ord_no 존재)
                if api_result.get("return_code") == 0:
                    success = True
                elif api_result.get("rt_cd") == "0":
                    success = True
                # 모의 취소의 경우
                elif api_result.get("success") or "모의 주문 취소 성공" in str(
                    api_result
                ):
                    success = True
                # 주문번호가 루트 레벨에 있는 경우 (성공으로 처리)
                elif api_result.get("ord_no"):
                    success = True
                # 주문번호가 output에 있는 경우
                elif api_result.get("output") and isinstance(
                    api_result["output"], dict
                ):
                    output = api_result["output"]
                    if output.get("ord_no") or output.get("KRX_FWDG_ORD_ORGNO"):
                        success = True
                    else:
                        error_msg = api_result.get(
                            "msg1",
                            api_result.get(
                                "message",
                                api_result.get("return_msg", "알 수 없는 오류"),
                            ),
                        )
                else:
                    error_msg = api_result.get(
                        "msg1",
                        api_result.get(
                            "message", api_result.get("return_msg", "알 수 없는 오류")
                        ),
                    )
            else:
                error_msg = "API 응답 없음"

            logger.info(f"취소 응답 분석 결과 - 성공: {success}, 에러: {error_msg}")

            # 브라우저에서 볼 수 있도록 상세 로그 추가
            logger.info(f"🎯 주문 취소 결과: {'성공' if success else '실패'}")
            if order:
                logger.info(
                    f"📋 취소 주문: {order.symbol} {order.order_type.value} {order.quantity}주 @ {order.price:,}원"
                )
            else:
                logger.info(
                    f"📋 취소 주문: {order_symbol} {order_quantity}주 (키움 API 조회)"
                )
            logger.info(f"🆔 주문 ID: {order_id}")
            logger.info(
                f"📝 응답 메시지: {api_result.get('return_msg', api_result.get('message', 'N/A'))}"
            )
            logger.info(f"🔍 API 응답: {api_result}")

            if success:
                # 취소 성공
                if order:
                    # 로컬 주문인 경우
                    order.status = OrderStatus.CANCELLED
                    order.message = "주문 취소 완료"

                    # 대기 목록에서 제거하고 히스토리에 추가
                    del self.pending_orders[order_id]
                    self.order_history.append(order)

                    logger.info(f"✅ 주문 취소 성공: {order_id}")
                    logger.info(
                        f"취소된 주문 정보: {order.symbol} {order.order_type.value} {order.quantity}주 @ {order.price:,}원"
                    )
                else:
                    # 키움 API 주문인 경우
                    logger.info(f"✅ 주문 취소 성공: {order_id}")
                    logger.info(
                        f"취소된 주문 정보: {order_symbol} {order_quantity}주 (키움 API 취소)"
                    )

                # 브라우저 console 로그
                logger.info(f"✅ 주문 취소 성공! ID: {order_id}")
                return True
            else:
                # 취소 실패
                logger.error(f"❌ 주문 취소 실패: {order_id} - {error_msg}")
                logger.error(f"취소 실패 상세: {api_result}")

                # 브라우저 console 로그
                logger.error(f"❌ 주문 취소 실패: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"❌ 주문 취소 중 오류: {e}")
            logger.error(f"Exception Details: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def update_order_status(self, order_id: str) -> Optional[OrderResult]:
        """
        주문 상태 업데이트

        Args:
            order_id: 주문 ID

        Returns:
            OrderResult: 업데이트된 주문 정보
        """
        try:
            if order_id not in self.pending_orders:
                return None

            order = self.pending_orders[order_id]

            # API 호출하여 주문 상태 조회
            api_result = self.kiwoom_api.get_order_status(order_id)

            if api_result and api_result.get("rt_cd") == "0":
                output = api_result.get("output", {})

                # 주문 상태 파싱
                order_status = output.get("ord_sts_cd", "")
                filled_qty = int(output.get("exec_qty", 0))
                filled_price = float(output.get("exec_avg_prc", 0))

                # 상태 매핑
                if order_status == "01":  # 접수
                    order.status = OrderStatus.ACCEPTED
                elif order_status == "02":  # 부분체결
                    order.status = OrderStatus.PARTIAL_FILLED
                elif order_status == "03":  # 전체체결
                    order.status = OrderStatus.FILLED
                elif order_status == "04":  # 취소
                    order.status = OrderStatus.CANCELLED
                elif order_status == "05":  # 거부
                    order.status = OrderStatus.REJECTED

                # 체결 정보 업데이트
                order.filled_quantity = filled_qty
                order.filled_price = filled_price

                if filled_qty > 0 and order.filled_time is None:
                    order.filled_time = datetime.now()

                # 완료된 주문은 히스토리로 이동
                if order.status in [
                    OrderStatus.FILLED,
                    OrderStatus.CANCELLED,
                    OrderStatus.REJECTED,
                ]:
                    del self.pending_orders[order_id]
                    self.order_history.append(order)

                logger.info(f"주문 상태 업데이트: {order_id} - {order.status.value}")
                return order
            else:
                logger.warning(f"주문 상태 조회 실패: {order_id}")
                return None

        except Exception as e:
            logger.error(f"주문 상태 업데이트 중 오류: {e}")
            return None

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """대기 중인 주문 목록 조회"""
        try:
            logger.info(f"=== 미체결 주문 조회 시작 ===")
            logger.info(f"현재 대기 주문 수: {len(self.pending_orders)}")
            logger.info(f"대기 주문 ID 목록: {list(self.pending_orders.keys())}")

            # 1. 로컬 pending_orders에서 조회
            local_pending_list = []
            for order_id, order in self.pending_orders.items():
                logger.info(
                    f"로컬 주문 처리: {order_id} - {order.symbol} {order.order_type.value} {order.quantity}주 @ {order.price:,}원"
                )
                order_dict = order.to_dict()
                order_dict["source"] = "local"  # 로컬에서 관리하는 주문임을 표시
                # 종목명 추가 (종목코드로부터 추정)
                order_dict["symbol_name"] = self._get_symbol_name(order.symbol)
                local_pending_list.append(order_dict)
                logger.info(f"로컬 주문 데이터 변환 완료: {order_dict}")

            # 2. 키움 API에서 실제 미체결 주문 조회 (ka10075 TR 사용)
            logger.info(f"키움 API에서 실제 미체결 주문 조회 시작 (ka10075)")
            api_pending_list = []
            try:
                api_result = self.kiwoom_api.get_pending_orders_from_api()

                # API 응답 성공 여부 판단 개선 (실제 ka10075 API 응답 구조에 맞게)
                api_success = False
                if api_result:
                    if api_result.get("rt_cd") == "0":
                        api_success = True
                    elif api_result.get("status") == "success":
                        api_success = True
                    elif api_result.get("return_code") == 0:
                        # ka10075 API는 return_code로 성공 여부 판단
                        api_success = True
                    elif "oso" in api_result:
                        # oso 데이터가 루트 레벨에 있으면 성공으로 처리
                        api_success = True

                if api_success:
                    # 실제 ka10075 API 응답 구조에 맞게 수정
                    oso_data = api_result.get(
                        "oso", []
                    )  # 미체결 주문 데이터 (루트 레벨)

                    if isinstance(oso_data, list):
                        for order_data in oso_data:
                            # ka10075 API 응답을 OrderResult 형식으로 변환 (실제 필드명에 맞게)
                            # 매수/매도 구분 수정: io_tp_nm에서 정확히 판단
                            io_tp_nm = order_data.get("io_tp_nm", "")
                            if io_tp_nm.startswith("+") or "매수" in io_tp_nm:
                                order_type = "매수"
                            elif io_tp_nm.startswith("-") or "매도" in io_tp_nm:
                                order_type = "매도"
                            else:
                                # 기본값으로 매수로 설정 (안전한 기본값)
                                order_type = "매수"

                            symbol = f"A{order_data.get('stk_cd', '')}"  # A 접두사 추가

                            order_dict = {
                                "order_id": order_data.get("ord_no", ""),
                                "symbol": symbol,
                                "order_type": order_type,
                                "order_type_code": order_data.get("io_tp_nm", ""),
                                "quantity": int(order_data.get("ord_qty", 0)),
                                "price": float(order_data.get("ord_pric", 0)),
                                "status": self._map_kiwoom_status_ka10075(
                                    order_data.get("ord_stt", "")
                                ),
                                "status_code": order_data.get("ord_stt", ""),
                                "filled_quantity": int(order_data.get("cntr_qty", 0)),
                                "filled_price": float(order_data.get("cntr_pric", 0)),
                                "order_time": order_data.get("tm", ""),
                                "filled_time": order_data.get("tm", ""),
                                "message": order_data.get("stk_nm", ""),  # 종목명
                                "symbol_name": order_data.get(
                                    "stk_nm", ""
                                ),  # 종목명을 별도 필드로 추가
                                "total_amount": int(order_data.get("ord_qty", 0))
                                * float(order_data.get("ord_pric", 0)),
                                "filled_amount": int(order_data.get("cntr_qty", 0))
                                * float(order_data.get("cntr_pric", 0)),
                                "source": "kiwoom_api_ka10075",
                            }
                            api_pending_list.append(order_dict)
                            logger.info(f"키움 API 주문 데이터 변환 완료: {order_dict}")
                    else:
                        logger.warning(
                            f"키움 API 응답 oso 데이터가 리스트가 아님: {type(oso_data)}"
                        )
                        logger.info(f"oso 데이터: {oso_data}")
                else:
                    logger.warning(f"키움 API 미체결 주문 조회 실패: {api_result}")
            except Exception as e:
                logger.error(f"키움 API 미체결 주문 조회 중 오류: {e}")
                import traceback

                logger.error(f"Traceback: {traceback.format_exc()}")

            # 3. 로컬과 API 결과 통합
            all_pending_list = local_pending_list + api_pending_list

            logger.info(f"✅ 미체결 주문 조회 완료: 총 {len(all_pending_list)}건")
            logger.info(f"  - 로컬 주문: {len(local_pending_list)}건")
            logger.info(f"  - 키움 API 주문: {len(api_pending_list)}건")
            logger.info(f"반환할 주문 목록: {all_pending_list}")
            return all_pending_list
        except Exception as e:
            logger.error(f"❌ 미체결 주문 조회 중 오류: {e}")
            logger.error(f"Exception Details: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def get_order_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """주문 히스토리 조회"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            history_list = []

            for order in self.order_history:
                if order.order_time >= cutoff_date:
                    history_list.append(order.to_dict())

            logger.info(f"주문 내역 조회: {len(history_list)}건 (최근 {days}일)")
            return history_list
        except Exception as e:
            logger.error(f"주문 내역 조회 중 오류: {e}")
            return []

    def _validate_order(self, order_request: OrderRequest) -> Dict[str, Any]:
        """
        주문 유효성 검증

        Args:
            order_request: 주문 요청 데이터

        Returns:
            Dict: 검증 결과
        """
        try:
            # 기본 검증
            if not order_request.symbol:
                return {"valid": False, "message": "종목코드가 없습니다."}

            if order_request.quantity <= 0:
                return {"valid": False, "message": "주문 수량은 0보다 커야 합니다."}

            if order_request.price <= 0:
                return {"valid": False, "message": "주문 가격은 0보다 커야 합니다."}

            # 계좌 잔고 확인 (매수인 경우)
            if order_request.order_type == OrderType.BUY:
                balance = self.kiwoom_api.get_balance()
                if balance:
                    available_cash = float(balance.get("prsm_dpst_aset_amt", 0))
                    required_amount = order_request.quantity * order_request.price

                    if available_cash < required_amount:
                        return {
                            "valid": False,
                            "message": f"잔고 부족: 필요 {required_amount:,}원, 보유 {available_cash:,}원",
                        }

            # 보유 주식 확인 (매도인 경우)
            if order_request.order_type == OrderType.SELL:
                positions = self.kiwoom_api.get_account_balance_kt00018()
                if positions and "output" in positions:
                    for position in positions["output"]:
                        if position.get("stk_cd") == order_request.symbol:
                            held_quantity = int(position.get("hldg_qty", 0))
                            if held_quantity < order_request.quantity:
                                return {
                                    "valid": False,
                                    "message": f"보유 주식 부족: 필요 {order_request.quantity}주, 보유 {held_quantity}주",
                                }
                            break
                    else:
                        return {
                            "valid": False,
                            "message": f"보유하지 않은 종목입니다: {order_request.symbol}",
                        }

            return {"valid": True, "message": "검증 통과"}

        except Exception as e:
            logger.error(f"주문 유효성 검증 중 오류: {e}")
            return {"valid": False, "message": f"검증 중 오류 발생: {str(e)}"}

    def _create_rejected_order(
        self, order_request: OrderRequest, message: str
    ) -> OrderResult:
        """거부된 주문 결과 생성"""
        return OrderResult(
            order_id=f"REJECTED_{int(time.time())}",
            symbol=order_request.symbol,
            order_type=order_request.order_type,
            quantity=order_request.quantity,
            price=order_request.price,
            status=OrderStatus.REJECTED,
            order_time=order_request.order_time,
            message=message,
        )

    def cleanup_expired_orders(self, max_age_hours: int = 24):
        """만료된 주문 정리"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_orders = []

        for order_id, order in self.pending_orders.items():
            if order.order_time < cutoff_time:
                expired_orders.append(order_id)

        for order_id in expired_orders:
            order = self.pending_orders[order_id]
            order.status = OrderStatus.EXPIRED
            order.message = "주문 만료"

            del self.pending_orders[order_id]
            self.order_history.append(order)

            logger.info(f"만료된 주문 정리: {order_id}")

    def _map_kiwoom_status(self, kiwoom_status_code: str) -> str:
        """키움 API 주문 상태 코드를 내부 상태로 매핑"""
        status_mapping = {
            "01": "접수완료",  # 접수
            "02": "부분체결",  # 부분체결
            "03": "전체체결",  # 전체체결
            "04": "취소",  # 취소
            "05": "거부",  # 거부
            "06": "접수대기",  # 접수대기
            "07": "만료",  # 만료
        }
        return status_mapping.get(kiwoom_status_code, "접수대기")

    def _map_kiwoom_status_ka10075(self, kiwoom_status_text: str) -> str:
        """키움 API ka10075 주문 상태 텍스트를 내부 상태로 매핑"""
        status_mapping = {
            "접수": "접수완료",
            "부분체결": "부분체결",
            "전체체결": "전체체결",
            "체결": "전체체결",
            "취소": "취소",
            "거부": "거부",
        }
        return status_mapping.get(kiwoom_status_text, kiwoom_status_text)
