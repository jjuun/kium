"""
체결 내역 조회 테스트
"""
import os
import sys
from datetime import datetime, timedelta

# 환경 변수 설정
os.environ['KIWOOM_APPKEY'] = '64339425'
os.environ['KIWOOM_SECRETKEY'] = 'your_secret_key_here'
os.environ['KIWOOM_IS_SIMULATION'] = 'False'

from src.api.kiwoom_api import KiwoomAPI
from src.core.logger import logger

def test_execution_history():
    """
    체결 내역 조회 테스트
    """
    try:
        kiwoom = KiwoomAPI()
        
        # 토큰 발급
        token = kiwoom.get_access_token()
        if not token:
            logger.error("토큰 발급 실패")
            return
        
        logger.info("토큰 발급 성공")
        
        # 체결 내역 조회 (삼성전자)
        logger.info("=== 체결 내역 조회 테스트 ===")
        result = kiwoom.get_execution_history(
            stk_cd="005930",  # 삼성전자
            qry_tp="1",       # 종목별 조회
            sell_tp="0",      # 전체
            ord_no="",        # 주문번호 (빈값)
            stex_tp="0"       # 통합
        )
        
        if result:
            logger.info("체결 내역 조회 성공")
            print("=== 체결 내역 ===")
            if 'output' in result and result['output']:
                executions = result['output']
                if isinstance(executions, list):
                    for i, exec_item in enumerate(executions[:5]):  # 최근 5건만 출력
                        print(f"{i+1}. 종목: {exec_item.get('stk_cd', 'N/A')}")
                        print(f"   체결시간: {exec_item.get('exec_tm', 'N/A')}")
                        print(f"   매도수: {'매도' if exec_item.get('sell_buy') == '1' else '매수'}")
                        print(f"   체결수량: {exec_item.get('exec_qty', '0')}")
                        print(f"   체결단가: {exec_item.get('exec_prc', '0')}")
                        print(f"   체결금액: {exec_item.get('exec_amt', '0')}")
                        print(f"   수수료: {exec_item.get('fee', '0')}")
                        print("---")
                else:
                    print("체결 데이터가 리스트 형태가 아닙니다.")
            else:
                print("체결 내역이 없습니다.")
        else:
            logger.error("체결 내역 조회 실패")
        
        # 날짜별 체결 내역 조회 (연속 조회 포함)
        logger.info("=== 날짜별 체결 내역 조회 테스트 ===")
        strt_dt = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        end_dt = datetime.now().strftime("%Y%m%d")
        
        result_by_date = kiwoom.get_execution_history_by_date(
            stk_cd="005930",
            strt_dt=strt_dt,
            end_dt=end_dt
        )
        
        if result_by_date:
            logger.info("날짜별 체결 내역 조회 성공")
            print(f"=== 날짜별 체결 내역 ({strt_dt} ~ {end_dt}) ===")
            print(f"총 체결 건수: {result_by_date.get('total_count', 0)}")
            
            if 'output' in result_by_date and result_by_date['output']:
                executions = result_by_date['output']
                if isinstance(executions, list):
                    for i, exec_item in enumerate(executions[:3]):  # 최근 3건만 출력
                        print(f"{i+1}. 종목: {exec_item.get('stk_cd', 'N/A')}")
                        print(f"   체결시간: {exec_item.get('exec_tm', 'N/A')}")
                        print(f"   매도수: {'매도' if exec_item.get('sell_buy') == '1' else '매수'}")
                        print(f"   체결수량: {exec_item.get('exec_qty', '0')}")
                        print(f"   체결단가: {exec_item.get('exec_prc', '0')}")
                        print("---")
                else:
                    print("체결 데이터가 리스트 형태가 아닙니다.")
            else:
                print("해당 기간의 체결 내역이 없습니다.")
        else:
            logger.error("날짜별 체결 내역 조회 실패")
            
    except Exception as e:
        logger.error(f"테스트 중 오류: {e}")

if __name__ == "__main__":
    test_execution_history() 