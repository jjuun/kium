"""
간단한 키움증권 API 토큰 발급 테스트
"""
import requests
import json
import os

def test_token():
    # 환경변수에서 API 키 가져오기
    appkey = os.getenv("KIWOOM_APPKEY")
    secretkey = os.getenv("KIWOOM_SECRETKEY")
    
    print(f"AppKey: {appkey[:10]}...")
    print(f"SecretKey: {secretkey[:10]}...")
    
    # 실전투자 API URL
    host = 'https://api.kiwoom.com'
    endpoint = '/oauth2/token'
    url = host + endpoint
    
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }
    
    data = {
        'grant_type': 'client_credentials',
        'appkey': appkey,
        'secretkey': secretkey,
    }
    
    print(f"요청 URL: {url}")
    print(f"요청 데이터: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        print(f'응답 상태 코드: {response.status_code}')
        print(f'응답 헤더: {dict(response.headers)}')
        print(f'응답 본문: {response.text}')
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 토큰 발급 성공!")
            print(f"Access Token: {result.get('access_token', '')[:20]}...")
            print(f"Expires In: {result.get('expires_in', '')}")
            return True
        else:
            print(f"❌ 토큰 발급 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 요청 중 오류: {e}")
        return False

if __name__ == "__main__":
    print("🔑 키움증권 API 토큰 발급 테스트")
    print("=" * 50)
    test_token() 