import json
import requests
import re
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# 로거 설정
logger = logging.getLogger("Formatter")
logging.basicConfig(level=logging.INFO)

# [설정 연결] config.py 및 같은 패키지 모듈 임포트
try:
    from config import (
        CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, 
        PRESETS_DIR
    )
    from src.sstoy_loader import decoder
except ImportError:
    # 단독 실행 시 경로 보정
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from config import (
        CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, 
        PRESETS_DIR
    )
    from src.sstoy_loader import decoder

def fetch_db(url: str, name: str) -> Dict[str, Any]:
    print(f"📥 {name} 데이터 다운로드 중...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"{name} 다운로드 실패: {e}")
        return {}

def build_id_mapping(db_json: Dict[str, Any]) -> List[int]:
    if not db_json: return []
    all_ids = [int(k) for k in db_json.keys()]
    return sorted(list(set(all_ids)))

def get_real_id(mapped_idx: int, id_map: List[int]) -> Optional[int]:
    """매핑된 인덱스 -> 실제 ID 변환"""
    if 0 < mapped_idx <= len(id_map):
        return id_map[mapped_idx - 1]
    return None

def get_program_char_key(real_id: int, name_db: Dict[str, str]) -> str:
    if not name_db: return f"unknown_{real_id}"
    
    # DB 키 형식: "Character.{ID}.1"
    key = f"Character.{real_id}.1"
    english_name = name_db.get(key, f"Unknown_{real_id}")
    
    # 포맷 변환
    formatted_key = english_name.lower().replace(" ", "_")
    formatted_key = re.sub(r'[^a-z0-9_]', '', formatted_key)
    
    return formatted_key

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def save_build_to_json(url: str):
    """URL을 변환하여 Presets 폴더에 JSON으로 저장합니다."""
    
    # 1. 필수 DB 다운로드
    char_db = fetch_db(CHARACTER_DB_URL, "Character")
    pot_db = fetch_db(POTENTIAL_DB_URL, "Potential")
    name_db = fetch_db(CHAR_NAME_DB_URL, "Character Name (EN)")
    
    if not char_db or not pot_db or not name_db:
        logger.error("데이터 다운로드 실패로 중단합니다.")
        return

    # 2. 매핑 테이블 생성
    char_map = build_id_mapping(char_db)
    pot_map = build_id_mapping(pot_db)

    # 3. URL 해독
    decoded = decoder.decode_url_raw(url)
    if "error" in decoded:
        logger.error(f"URL 해독 에러: {decoded['error']}")
        return

    build_name = decoded['build_name']
    safe_filename = f"{sanitize_filename(build_name)}.json"
    
    # 저장 경로 설정 (config.PRESETS_DIR 사용)
    if not PRESETS_DIR.exists():
        try:
            PRESETS_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"폴더 생성됨: {PRESETS_DIR}")
        except Exception as e:
            logger.error(f"폴더 생성 실패: {e}")
            return

    output_path = PRESETS_DIR / safe_filename
    
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
        if real_char_id is None: continue

        char_key = get_program_char_key(real_char_id, name_db)
        
        print(f"  - [{pos.upper()}] ID:{real_char_id} -> Key: \"{char_key}\"")
        
        # 잠재력 데이터 변환
        potentials_dict = {}
        for mapped_pot_idx in data['mapped_potentials']:
            real_pot_id = get_real_id(mapped_pot_idx, pot_map)
            if real_pot_id is None: continue

            # 마크 정보가 없으면 기본값 2 적용
            priority = data['marks'].get(mapped_pot_idx, 2) 
            potentials_dict[str(real_pot_id)] = priority
            
        result_json["characters"][char_key] = potentials_dict

    # 5. 파일 저장
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 변환 완료! 파일 저장됨: {output_path}")
        
    except Exception as e:
        logger.error(f"파일 저장 중 에러 발생: {e}")

# === 실행 설정 ===
if __name__ == "__main__":
    # 변환하고 싶은 URL을 여기에 넣으세요 (CLI 모드)
    TARGET_URL = ""
    
    if TARGET_URL:
        save_build_to_json(TARGET_URL)
    else:
        print("TARGET_URL 변수에 변환할 URL을 입력하고 실행해주세요.")