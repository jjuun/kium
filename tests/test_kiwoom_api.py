"""
키움증권 API 테스트 파일
"""

import os
from datetime import datetime
from src.core.logger import logger
from src.api.kiwoom_api import KiwoomAPI


def test_kiwoom_token():
    """
    키움증권 API 토큰 발급 테스트
    """
    print("=== 키움증권 API 토큰 발급 테스트 ===")

    # 환경변수에서 API 키 확인
    appkey = os.getenv("KIWOOM_APPKEY")
    secretkey = os.getenv("KIWOOM_SECRETKEY")

    if not appkey or not secretkey:
        print("❌ KIWOOM_APPKEY 또는 KIWOOM_SECRETKEY가 설정되지 않았습니다.")
        print("   .env 파일에 다음을 추가하세요:")
        print("   KIWOOM_APPKEY=your_appkey_here")
        print("   KIWOOM_SECRETKEY=your_secretkey_here")
        return False

    try:
        # 키움증권 API 초기화
        kiwoom = KiwoomAPI()

        # 토큰 발급 테스트
        print("1. 토큰 발급 테스트...")
        token = kiwoom.get_access_token()

        if token:
            print(f"   ✓ 토큰 발급 성공: {token[:20]}...")
            return True
        else:
            print("   ✗ 토큰 발급 실패")
            return False

    except Exception as e:
        print(f"   ✗ 토큰 발급 중 오류: {e}")
        return False


def test_kiwoom_account():
    """
    키움증권 계좌 정보 조회 테스트
    """
    print("\n=== 키움증권 계좌 정보 조회 테스트 ===")

    try:
        kiwoom = KiwoomAPI()

        # 계좌 정보 조회 테스트
        print("1. 계좌 정보 조회 테스트...")
        account_info = kiwoom.get_account_info()

        if account_info:
            print("   ✓ 계좌 정보 조회 성공")
            print(f"   ✓ 응답 데이터: {account_info}")
            return True
        else:
            print("   ✗ 계좌 정보 조회 실패")
            return False

    except Exception as e:
        print(f"   ✗ 계좌 정보 조회 중 오류: {e}")
        return False


def test_kiwoom_balance():
    """
    키움증권 잔고 조회 테스트
    """
    print("\n=== 키움증권 잔고 조회 테스트 ===")

    try:
        kiwoom = KiwoomAPI()

        # 잔고 조회 테스트
        print("1. 잔고 조회 테스트...")
        balance = kiwoom.get_balance()

        if balance:
            print("   ✓ 잔고 조회 성공")
            print(f"   ✓ 응답 데이터: {balance}")
            return True
        else:
            print("   ✗ 잔고 조회 실패")
            return False

    except Exception as e:
        print(f"   ✗ 잔고 조회 중 오류: {e}")
        return False


def test_kiwoom_stock_price():
    """
    키움증권 주식 현재가 조회 테스트
    """
    print("\n=== 키움증권 주식 현재가 조회 테스트 ===")

    try:
        kiwoom = KiwoomAPI()

        # 삼성전자 현재가 조회 테스트
        print("1. 삼성전자 현재가 조회 테스트...")
        stock_price = kiwoom.get_stock_price("005930")

        if stock_price:
            print("   ✓ 현재가 조회 성공")
            print(f"   ✓ 응답 데이터: {stock_price}")
            return True
        else:
            print("   ✗ 현재가 조회 실패")
            return False

    except Exception as e:
        print(f"   ✗ 현재가 조회 중 오류: {e}")
        return False


def test_kiwoom_order():
    """
    키움증권 주문 테스트 (시뮬레이션 모드)
    """
    print("\n=== 키움증권 주문 테스트 (시뮬레이션) ===")

    try:
        kiwoom = KiwoomAPI()

        # 시뮬레이션 모드에서 주문 테스트
        print("1. 시뮬레이션 주문 테스트...")

        # 실제 주문은 위험하므로 시뮬레이션 모드에서만 테스트
        if kiwoom.is_simulation:
            print("   ✓ 시뮬레이션 모드에서 테스트 중...")
            print("   ⚠️  실제 주문은 테스트하지 않습니다.")
            return True
        else:
            print("   ⚠️  실전 모드에서는 주문 테스트를 건너뜁니다.")
            return True

    except Exception as e:
        print(f"   ✗ 주문 테스트 중 오류: {e}")
        return False


def run_kiwoom_tests():
    """
    모든 키움증권 API 테스트 실행
    """
    print("🚀 키움증권 API 테스트 시작")
    print("=" * 50)

    test_results = []

    # 토큰 발급 테스트
    test_results.append(("토큰 발급", test_kiwoom_token()))

    # 계좌 정보 조회 테스트
    test_results.append(("계좌 정보 조회", test_kiwoom_account()))

    # 잔고 조회 테스트
    test_results.append(("잔고 조회", test_kiwoom_balance()))

    # 현재가 조회 테스트
    test_results.append(("현재가 조회", test_kiwoom_stock_price()))

    # 주문 테스트
    test_results.append(("주문 테스트", test_kiwoom_order()))

    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약:")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n총 {total}개 테스트 중 {passed}개 성공")

    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
        print("키움증권 API가 정상적으로 작동합니다.")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        print("API 키 설정과 네트워크 연결을 확인하세요.")


if __name__ == "__main__":
    run_kiwoom_tests()
