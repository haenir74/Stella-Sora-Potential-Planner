import json
import os

def generate_mapping_db():
    print("🔄 매핑 DB(ID -> Key) 생성 시작...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 파일 로드
        with open(os.path.join(base_dir, 'Character.json'), 'r', encoding='utf-8') as f:
            char_data = json.load(f)
        with open(os.path.join(base_dir, 'Character_en.json'), 'r', encoding='utf-8') as f:
            char_en_data = json.load(f)
        with open(os.path.join(base_dir, 'CharPotential.json'), 'r', encoding='utf-8') as f:
            char_pot_data = json.load(f)
        with open(os.path.join(base_dir, 'Potential.json'), 'r', encoding='utf-8') as f:
            pot_data = json.load(f)
        
        # [수정됨] sstoy 인덱스 생성 기준을 '전체 데이터'로 변경
        sorted_char_ids = sorted([int(k) for k in char_data.keys() if k.isdigit()])
        sorted_pot_ids = sorted([int(k) for k in pot_data.keys() if k.isdigit()])
        
        print(f"   - 감지된 전체 캐릭터 수: {len(sorted_char_ids)}")
        print(f"   - 감지된 전체 잠재력 수: {len(sorted_pot_ids)}")

    except Exception as e:
        print(f"❌ 파일 로드 실패: {e}")
        return

    # 최종 DB 구조
    mapping_db = {
        "sstoy_index_map": sorted_char_ids, # Index -> ID 변환용 (전체 캐릭터 기준)
        "sstoy_pot_map": sorted_pot_ids,    # Index -> ID 변환용 (전체 잠재력 기준)
        "characters": {}                    # ID -> 정보 매핑
    }

    # 잠재력 매핑 정보 생성 (잠재력 ID -> {main_key, sub_key})
    # CharPotential.json을 순회하며 DB 구축
    for char_id_str, groups in char_pot_data.items():
        if not char_id_str.isdigit(): continue
        char_id = int(char_id_str)
        
        # 1. 이름 매핑
        # Character.json에 해당 ID가 있는지 확인
        if char_id_str not in char_data:
            continue
            
        name_key = char_data[char_id_str].get("Name")
        raw_en_name = char_en_data.get(name_key, f"Unknown_{char_id}")
        formatted_name = raw_en_name.lower().replace(" ", "_")

        # 2. 잠재력 ID -> Key 매핑 구조
        id_to_key_map = {}

        m_specific = groups.get("MasterSpecificPotentialIds", [])
        m_normal = groups.get("MasterNormalPotentialIds", [])
        common = groups.get("CommonPotentialIds", [])
        a_specific = groups.get("AssistSpecificPotentialIds", [])
        a_normal = groups.get("AssistNormalPotentialIds", [])

        # 슬롯 할당 함수
        def assign_keys(prefix, specific, normal, common_shared):
            # Group 1 (1~5)
            for i in range(2):
                if i < len(specific): 
                    pid = str(specific[i])
                    if pid not in id_to_key_map: id_to_key_map[pid] = {}
                    id_to_key_map[pid][prefix] = f"{prefix}_{i+1:02d}"
            for i in range(3):
                if i < len(normal): 
                    pid = str(normal[i])
                    if pid not in id_to_key_map: id_to_key_map[pid] = {}
                    id_to_key_map[pid][prefix] = f"{prefix}_{i+3:02d}"
            
            # Group 2 (6~10)
            for i in range(2):
                if i+2 < len(specific): 
                    pid = str(specific[i+2])
                    if pid not in id_to_key_map: id_to_key_map[pid] = {}
                    id_to_key_map[pid][prefix] = f"{prefix}_{i+6:02d}"
            for i in range(3):
                if i+3 < len(normal): 
                    pid = str(normal[i+3])
                    if pid not in id_to_key_map: id_to_key_map[pid] = {}
                    id_to_key_map[pid][prefix] = f"{prefix}_{i+8:02d}"

            # Common Group (11~16)
            for i in range(3):
                if i+6 < len(normal): 
                    pid = str(normal[i+6])
                    if pid not in id_to_key_map: id_to_key_map[pid] = {}
                    id_to_key_map[pid][prefix] = f"{prefix}_{i+11:02d}"
            for i in range(3):
                if i < len(common_shared): 
                    pid = str(common_shared[i])
                    if pid not in id_to_key_map: id_to_key_map[pid] = {}
                    id_to_key_map[pid][prefix] = f"{prefix}_{i+14:02d}"

        assign_keys("main", m_specific, m_normal, common)
        assign_keys("sub", a_specific, a_normal, common)

        mapping_db["characters"][str(char_id)] = {
            "name": formatted_name,
            "potentials": id_to_key_map
        }

    # 파일 저장
    out_path = os.path.join(base_dir, 'mapping_db.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(mapping_db, f, indent=2, ensure_ascii=False)
    
    print(f"✅ DB 생성 완료: {out_path}")

if __name__ == "__main__":
    generate_mapping_db()