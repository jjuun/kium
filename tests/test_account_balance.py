"""
계좌평가잔고내역요청 테스트 (kt00018 TR)
"""

import os
import sys
from datetime import datetime

# 환경 변수 설정
os.environ["KIWOOM_APPKEY"] = "64339425"
os.environ["KIWOOM_SECRETKEY"] = "your_secret_key_here"
os.environ["KIWOOM_IS_SIMULATION"] = "False"

from src.api.kiwoom_api import KiwoomAPI
from src.core.logger import logger


def test_account_balance():
    """
    계좌평가잔고내역 조회 테스트
    """
    try:
        kiwoom = KiwoomAPI()

        # 토큰 발급
        token = kiwoom.get_access_token()
        if not token:
            logger.error("토큰 발급 실패")
            return

        logger.info("토큰 발급 성공")

        # 계좌평가잔고내역 조회 (합산)
        logger.info("=== 계좌평가잔고내역 조회 테스트 (합산) ===")
        result = kiwoom.get_account_balance_kt00018(
            qry_tp="1", dmst_stex_tp="KRX"  # 합산  # 한국거래소
        )

        if result:
            logger.info("계좌평가잔고내역 조회 성공")
            print("=== 계좌평가잔고내역 (합산) ===")
            if "output" in result and result["output"]:
                balance_data = result["output"]
                if isinstance(balance_data, list):
                    for i, item in enumerate(balance_data[:3]):  # 최근 3건만 출력
                        print(f"{i+1}. 계좌번호: {item.get('acnt_no', 'N/A')}")
                        print(f"   평가금액: {item.get('eval_amt', '0')}")
                        print(f"   평가손익: {item.get('eval_pnl', '0')}")
                        print(f"   수익률: {item.get('pnl_rt', '0')}%")
                        print(f"   보유종목수: {item.get('hldg_cnt', '0')}")
                        print("---")
                else:
                    print("잔고 데이터가 리스트 형태가 아닙니다.")
            else:
                print("잔고 내역이 없습니다.")
        else:
            logger.error("계좌평가잔고내역 조회 실패")

        # 계좌평가잔고내역 조회 (개별)
        logger.info("=== 계좌평가잔고내역 조회 테스트 (개별) ===")
        result_individual = kiwoom.get_account_balance_kt00018(
            qry_tp="2", dmst_stex_tp="KRX"  # 개별  # 한국거래소
        )

        if result_individual:
            logger.info("개별 계좌평가잔고내역 조회 성공")
            print("=== 계좌평가잔고내역 (개별) ===")
            if "output" in result_individual and result_individual["output"]:
                balance_data = result_individual["output"]
                if isinstance(balance_data, list):
                    for i, item in enumerate(balance_data[:5]):  # 최근 5건만 출력
                        print(f"{i+1}. 종목코드: {item.get('stk_cd', 'N/A')}")
                        print(f"   종목명: {item.get('stk_nm', 'N/A')}")
                        print(f"   보유수량: {item.get('hldg_qty', '0')}")
                        print(f"   매입단가: {item.get('pchs_prc', '0')}")
                        print(f"   현재가: {item.get('curr_prc', '0')}")
                        print(f"   평가손익: {item.get('eval_pnl', '0')}")
                        print(f"   수익률: {item.get('pnl_rt', '0')}%")
                        print("---")
                else:
                    print("개별 잔고 데이터가 리스트 형태가 아닙니다.")
            else:
                print("개별 잔고 내역이 없습니다.")
        else:
            logger.error("개별 계좌평가잔고내역 조회 실패")

    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")


if __name__ == "__main__":
    test_account_balance()
