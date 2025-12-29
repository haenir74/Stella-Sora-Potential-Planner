import json
import requests
import os
import re
import decoder

# === 설정 ===
REPO_BASE_URL = "https://raw.githubusercontent.com/JforPlay/sstoy/refs/heads/main/public/data"
CHARACTER_DB_URL = f"{REPO_BASE_URL}/Character.json"
POTENTIAL_DB_URL = f"{REPO_BASE_URL}/Potential.json"
CHAR_NAME_DB_URL = f"{REPO_BASE_URL}/EN/Character.json"  # 영문 이름 DB 필수

def fetch_db(url, name):
    """GitHub에서 DB 데이터를 가져옵니다."""
    print(f"📥 {name} 데이터 다운로드 중...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ {name} 다운로드 실패: {e}")
        return {}

def build_id_mapping(db_json):
    """DB ID를 정렬하여 매핑 리스트 생성"""
    if not db_json: return []
    all_ids = [int(k) for k in db_json.keys()]
    return sorted(list(set(all_ids)))

def get_real_id(mapped_idx, id_map):
    """매핑된 인덱스 -> 실제 ID 변환"""
    if 0 < mapped_idx <= len(id_map):
        return id_map[mapped_idx - 1]
    return None

def get_program_char_key(real_id, name_db):
    """
    ID를 프로그램용 키 포맷(소문자_언더바)으로 변환합니다.
    예: 158 (Snowish Laru) -> "snowish_laru"
    """
    if not name_db: return f"unknown_{real_id}"
    
    # DB 키 형식: "Character.{ID}.1"
    key = f"Character.{real_id}.1"
    english_name = name_db.get(key, f"Unknown_{real_id}")
    
    # 포맷 변환: 소문자화 -> 공백을 언더바로 변경 -> 특수문자 제거
    formatted_key = english_name.lower().replace(" ", "_")
    formatted_key = re.sub(r'[^a-z0-9_]', '', formatted_key) # 안전을 위해 알파벳,숫자,_ 만 허용
    
    return formatted_key

def sanitize_filename(name):
    """파일 시스템에서 사용할 수 없는 특수문자 제거"""
    # 윈도우/리눅스 공통 금지 문자 제거 (<, >, :, ", /, \, |, ?, *)
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def save_build_to_json(url):
    # 1. 필수 DB 다운로드
    char_db = fetch_db(CHARACTER_DB_URL, "Character")
    pot_db = fetch_db(POTENTIAL_DB_URL, "Potential")
    name_db = fetch_db(CHAR_NAME_DB_URL, "Character Name (EN)")
    
    if not char_db or not pot_db or not name_db:
        print("데이터 다운로드 실패로 중단합니다.")
        return

    # 2. 매핑 테이블 생성
    char_map = build_id_mapping(char_db)
    pot_map = build_id_mapping(pot_db)

    # 3. URL 해독
    decoded = decoder.decode_url_raw(url)
    if "error" in decoded:
        print(f"URL 해독 에러: {decoded['error']}")
        return

    # [수정] 빌드 이름으로 파일명 생성
    build_name = decoded['build_name']
    safe_filename = f"{sanitize_filename(build_name)}.json"
    
    print(f"\n🏗️  빌드 변환 시작: {build_name}")

    # 4. JSON 구조 생성
    result_json = {
        "build_name": build_name,
        "characters": {}
    }

    raw_chars = decoded['raw_characters']
    positions = ['master', 'assist1', 'assist2']

    for pos in positions:
        if pos not in raw_chars: continue
        
        data = raw_chars[pos]
        
        # 캐릭터 ID 및 키 변환
        real_char_id = get_real_id(data['mapped_char_idx'], char_map)
        char_key = get_program_char_key(real_char_id, name_db)
        
        print(f"  - [{pos.upper()}] ID:{real_char_id} -> Key: \"{char_key}\"")
        
        # 잠재력 데이터 변환
        potentials_dict = {}
        for mapped_pot_idx in data['mapped_potentials']:
            real_pot_id = get_real_id(mapped_pot_idx, pot_map)
            
            # [수정] 마크가 없으면 기본값 2 적용
            priority = data['marks'].get(mapped_pot_idx, 2) 
            
            # ID는 문자열 키로 저장 ("510301": 5)
            potentials_dict[str(real_pot_id)] = priority
            
        result_json["characters"][char_key] = potentials_dict

    # 5. 파일 저장
    try:
        with open(safe_filename, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 변환 완료! 파일 저장됨: {safe_filename}")
        
    except Exception as e:
        print(f"파일 저장 중 에러 발생: {e}")

# === 실행 설정 ===
if __name__ == "__main__":
    # 변환하고 싶은 URL을 여기에 넣으세요
    TARGET_URL = "https://jforplay.github.io/sstoy/app.html#build=v2d-hcWyouZY~47~%7C%23k%2300ruyGeb)H3GU4%5EX9pnZ%5D(tY4LkS%23Q6IA%3Ch*%3D6L3.(upfE%5D%24yFx%2C%2F)U%3A~%7Di!NWy1v%246h8%40j%3C%3CUcjWS%26%2C(_Q35%3E%2FJctFl3Wq%24aLgS%7Bh%40bf8BW50g6(kL6%40O%23LV0F%23Btvlly%5DGGNK%2CQI!0!O(yxN%60c6%7D%40F_7RH6%5BBy0%3AFT.CA"
    
    save_build_to_json(TARGET_URL)