import json
import requests
import os

# =============================================================================
# [설정] GitHub Raw Data URL (원본 소스)
# =============================================================================
# 실제 sstoy 리포지토리 구조에 맞춘 추정 URL입니다.
# 만약 404 에러가 나면 경로를 수정해야 합니다 (예: public/data -> src/data 등)
BASE_URL = "https://raw.githubusercontent.com/jforplay/sstoy/main/public/data"
URL_CHARACTER = f"{BASE_URL}/Character.json"
URL_POTENTIAL = f"{BASE_URL}/Potential.json"

OUTPUT_DB = "mapping_db.json"

def fetch_json_from_github(url):
    """GitHub에서 JSON 파일을 다운로드합니다."""
    print(f"🌐 다운로드 시도: {url}")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("   ✅ 다운로드 성공")
            return response.json()
        else:
            print(f"   ❌ 실패 (Status Code: {response.status_code})")
            return None
    except Exception as e:
        print(f"   ❌ 네트워크 에러: {e}")
        return None

def update_database():
    print("🔄 DB 업데이트를 시작합니다...")

    # 1. GitHub에서 최신 데이터 가져오기
    chars_data = fetch_json_from_github(URL_CHARACTER)
    pots_data = fetch_json_from_github(URL_POTENTIAL)

    if not chars_data or not pots_data:
        print("⚠️ 데이터를 가져오지 못해 업데이트를 중단합니다.")
        return

    # 2. 데이터 파싱 및 정렬 (SSToy 알고리즘 적용)
    # -------------------------------------------------------------------------
    # 캐릭터 ID 정렬
    if isinstance(chars_data, list):
        char_dict = {c['Id']: c for c in chars_data if 'Id' in c}
    else:
        char_dict = {int(k): v for k, v in chars_data.items()}
    all_char_ids = sorted(list(char_dict.keys()))

    # 잠재력 ID 정렬
    if isinstance(pots_data, list):
        pot_dict = {p['Id']: p for p in pots_data if 'Id' in p}
    else:
        pot_dict = {int(k): v for k, v in pots_data.items()}
    all_pot_ids = sorted(list(pot_dict.keys()))
    
    print(f"📊 분석 결과: 캐릭터 {len(all_char_ids)}명 / 잠재력 {len(all_pot_ids)}개")

    # 3. 매핑 DB 구조 생성
    my_db = {
        "sstoy_index_map": all_char_ids,
        "sstoy_pot_map": all_pot_ids,
        "characters": {}
    }

    # 4. 상세 정보 매핑
    for real_id in all_char_ids:
        char_info = char_dict[real_id]
        str_id = str(real_id)
        
        # 이름 가져오기
        name = char_info.get('Name', f"Character_{real_id}")
        
        my_db["characters"][str_id] = {
            "name": name,
            "potentials": {} 
        }
        
        # 잠재력 매핑
        if 'Potentials' in char_info:
            raw_pot_list = char_info['Potentials']
            pot_map = {}
            for i, pid in enumerate(raw_pot_list):
                pid_int = int(pid)
                if pid_int in pot_dict:
                    p_name = pot_dict[pid_int].get('Name', str(pid_int))
                    
                    # 0, 1번 인덱스 = 메인(Main), 나머지 = 서브(Sub)
                    role_key = "main" if i < 2 else "sub"
                    
                    pot_map[str(pid_int)] = {
                        "main": p_name if role_key == "main" else None,
                        "sub": p_name if role_key == "sub" else None
                    }
            my_db["characters"][str_id]["potentials"] = pot_map

    # 5. 로컬 파일로 저장 (캐싱)
    with open(OUTPUT_DB, 'w', encoding='utf-8') as f:
        json.dump(my_db, f, indent=2, ensure_ascii=False)
        
    print(f"🎉 업데이트 완료! '{OUTPUT_DB}' 파일이 최신 버전으로 갱신되었습니다.")

if __name__ == "__main__":
    # requests 라이브러리가 없으면 설치 안내
    try:
        import requests
        update_database()
    except ImportError:
        print("❌ 'requests' 라이브러리가 필요합니다.")
        print("   설치 명령어: pip install requests")