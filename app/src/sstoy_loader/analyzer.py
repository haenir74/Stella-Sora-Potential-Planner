import requests
import json
import decoder

# === 설정: GitHub Raw Data URL ===
REPO_BASE_URL = "https://raw.githubusercontent.com/JforPlay/sstoy/refs/heads/main/public/data"
CHARACTER_DB_URL = f"{REPO_BASE_URL}/Character.json"
POTENTIAL_DB_URL = f"{REPO_BASE_URL}/Potential.json"
CHAR_NAME_DB_URL = f"{REPO_BASE_URL}/EN/Character.json"

def fetch_db(url, name):
    print(f"📥 {name} DB 다운로드 중...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ {name} 다운로드 실패: {e}")
        return None

def build_id_mapping(db_json):
    if not db_json: return []
    all_ids = [int(k) for k in db_json.keys()]
    return sorted(list(set(all_ids)))

def get_real_id(mapped_idx, id_map):
    if 0 < mapped_idx <= len(id_map):
        return id_map[mapped_idx - 1]
    return f"Unknown({mapped_idx})"

def get_char_name(id, name_db):
    if not name_db: return "Unknown"
    
    key = f"Character.{id}.1"
    return name_db.get(key, "Unknown")

def analyze_build_formatted(url):
    # 1. DB 데이터 가져오기 (캐릭터 & 잠재력만)
    char_db = fetch_db(CHARACTER_DB_URL, "Character")
    pot_db = fetch_db(POTENTIAL_DB_URL, "Potential")
    name_db = fetch_db(CHAR_NAME_DB_URL, "Character Name")
    
    if not char_db or not pot_db:
        print("DB를 가져오지 못해 분석을 중단합니다.")
        return

    # 2. 매핑 테이블 생성
    char_map = build_id_mapping(char_db)
    pot_map = build_id_mapping(pot_db)
    
    # 3. URL 디코딩
    decoded = decoder.decode_url_raw(url)
    if "error" in decoded:
        print(decoded["error"])
        return

    # 4. 출력
    print("\n" + "="*50)
    print(f"Build Name : {decoded['build_name']},")
    
    raw_chars = decoded['raw_characters']
    positions = ['master', 'assist1', 'assist2']
    
    for pos in positions:
        if pos not in raw_chars:
            continue
            
        data = raw_chars[pos]
        
        real_char_id = get_real_id(data['mapped_char_idx'], char_map)
        char_name = get_char_name(real_char_id, name_db)
        
        print(f"{pos.capitalize()}:{{")
        print(f"  Char_ID: {real_char_id} ({char_name})")
        print(f"  Potentials: {{")
        
        # 잠재력 목록 순회
        for mapped_pot_idx in data['mapped_potentials']:
            real_pot_id = get_real_id(mapped_pot_idx, pot_map)
            
            # 우선순위 값 가져오기 (없으면 기본값 0 또는 1, 여기선 1로 설정)
            priority = data['marks'].get(mapped_pot_idx, 1)
            
            print(f"    {real_pot_id} : {priority},")
            
        print("  }")
        print("}")
    print("="*50)

# === 실행 ===
TARGET_URL = "https://jforplay.github.io/sstoy/app.html#build=v2d-hcWyouZY~47~%7C%23k%2300ruyGeb)H3GU4%5EX9pnZ%5D(tY4LkS%23Q6IA%3Ch*%3D6L3.(upfE%5D%24yFx%2C%2F)U%3A~%7Di!NWy1v%246h8%40j%3C%3CUcjWS%26%2C(_Q35%3E%2FJctFl3Wq%24aLgS%7Bh%40bf8BW50g6(kL6%40O%23LV0F%23Btvlly%5DGGNK%2CQI!0!O(yxN%60c6%7D%40F_7RH6%5BBy0%3AFT.CA"

if __name__ == "__main__":
    analyze_build_formatted(TARGET_URL)