import os
import json
import requests

# =========================================================
# [설정] GitHub 리포지토리 및 경로
# =========================================================
# 예시 주소입니다. 실제 데이터가 있는 주소로 변경하세요.
GITHUB_BASE_URL = "https://raw.githubusercontent.com/User/RepoName/main/Data"

# 가져올 파일 목록
TARGET_FILES = ["Character_en.json", "CharPotential.json", "Potential.json"]

# 저장 경로
DATA_DIR = "./resources/data"
MAPPING_FILE = "./resources/mapping.json"

def download_game_data():
    """GitHub에서 최신 데이터 다운로드"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    print("[1/2] GitHub 데이터 동기화 중...")
    
    for filename in TARGET_FILES:
        url = f"{GITHUB_BASE_URL}/{filename}"
        save_path = os.path.join(DATA_DIR, filename)
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"  -> [다운로드] {filename}")
        except Exception as e:
            print(f"  -> [오류] {filename} 다운로드 실패: {e}")
            return False
    return True

def generate_mapping():
    """데이터를 기반으로 ID <-> 파일명 매핑 생성"""
    print("[2/2] 매핑 데이터베이스 생성 중...")
    
    try:
        # 데이터 로드
        with open(f"{DATA_DIR}/Character_en.json", 'r', encoding='utf-8') as f:
            chars_en = json.load(f) # { "1": "Stella", ... }
        with open(f"{DATA_DIR}/CharPotential.json", 'r', encoding='utf-8') as f:
            char_potentials = json.load(f) # [ {"characterId":1, "potentialId":101}, ... ]
        with open(f"{DATA_DIR}/Potential.json", 'r', encoding='utf-8') as f:
            potentials = json.load(f) # { "101": { "type": 0, ... }, ... }

        mapping_db = {}

        # 1. 캐릭터별 잠재력 ID 그룹화
        char_groups = {}
        for entry in char_potentials:
            cid = str(entry["characterId"])
            pid = str(entry["potentialId"])
            if cid not in char_groups: char_groups[cid] = []
            char_groups[cid].append(pid)

        # 2. 매핑 로직 수행
        for cid, pid_list in char_groups.items():
            char_name = chars_en.get(cid, f"Unknown_{cid}")
            
            # ID 오름차순 정렬 (게임 내 순서와 일치한다고 가정)
            pid_list.sort(key=int)
            
            skill_map = {}
            main_idx, sub_idx = 1, 1
            
            for pid in pid_list:
                pot_info = potentials.get(pid)
                if not pot_info: continue
                
                # type: 0=Main, 1=Sub (데이터 구조에 따라 수정 필요)
                p_type = pot_info.get("type", 0) 
                
                if p_type == 0:
                    key = f"main_{main_idx:02d}"
                    main_idx += 1
                else:
                    key = f"sub_{sub_idx:02d}"
                    sub_idx += 1
                
                # { "1001": "main_01" } 형태로 저장
                skill_map[pid] = key
            
            mapping_db[char_name] = {
                "id": cid,
                "skills": skill_map
            }

        # 3. 매핑 파일 저장
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping_db, f, indent=4, ensure_ascii=False)
            
        print(f"  -> [완료] mapping.json 생성됨 ({len(mapping_db)}명 캐릭터)")
        
    except Exception as e:
        print(f"  -> [오류] 매핑 생성 실패: {e}")

if __name__ == "__main__":
    if download_game_data():
        generate_mapping()