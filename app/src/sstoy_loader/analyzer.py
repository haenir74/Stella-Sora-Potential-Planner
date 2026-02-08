import sys
import requests
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

# 로거 설정
logger = logging.getLogger("Analyzer")
logging.basicConfig(level=logging.INFO)

# [설정 연결] config.py 및 같은 패키지 모듈 임포트
try:
    from config import CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL
    from src.sstoy_loader import decoder
except ImportError:
    # 단독 실행 시 경로 보정
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from config import CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL
    from src.sstoy_loader import decoder

def fetch_db(url: str, name: str) -> Optional[Dict[str, Any]]:
    """DB 다운로드 헬퍼"""
    print(f"📥 {name} DB 다운로드 중...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"{name} 다운로드 실패: {e}")
        return None

def build_id_mapping(db_json: Dict[str, Any]) -> List[int]:
    if not db_json: return []
    all_ids = [int(k) for k in db_json.keys()]
    return sorted(list(set(all_ids)))

def get_real_id(mapped_idx: int, id_map: List[int]) -> str:
    if 0 < mapped_idx <= len(id_map):
        return str(id_map[mapped_idx - 1])
    return f"Unknown({mapped_idx})"

def get_char_name(char_id: str, name_db: Dict[str, str]) -> str:
    if not name_db: return "Unknown"
    key = f"Character.{char_id}.1"
    return name_db.get(key, f"Unknown_{char_id}")

def analyze_build_formatted(url: str):
    """SSToy 빌드 URL을 해독하여 콘솔에 상세 정보를 출력합니다."""
    
    # 1. DB 데이터 가져오기
    char_db = fetch_db(CHARACTER_DB_URL, "Character")
    pot_db = fetch_db(POTENTIAL_DB_URL, "Potential")
    name_db = fetch_db(CHAR_NAME_DB_URL, "Character Name")
    
    if not char_db or not pot_db:
        logger.error("DB를 가져오지 못해 분석을 중단합니다.")
        return

    # 2. 매핑 테이블 생성
    char_map = build_id_mapping(char_db)
    pot_map = build_id_mapping(pot_db)
    
    # 3. URL 디코딩
    decoded = decoder.decode_url_raw(url)
    if "error" in decoded:
        logger.error(decoded["error"])
        return

    # 4. 결과 출력
    build_name = decoded['build_name']
    print("\n" + "="*60)
    print(f"🏗️  Build Analysis: {build_name}")
    print("="*60)
    
    raw_chars = decoded['raw_characters']
    positions = ['master', 'assist1', 'assist2']
    
    for pos in positions:
        if pos not in raw_chars:
            continue
            
        data = raw_chars[pos]
        
        real_char_id = get_real_id(data['mapped_char_idx'], char_map)
        char_name = get_char_name(real_char_id, name_db)
        
        print(f"\n[{pos.upper()}] {char_name} (ID: {real_char_id})")
        print("-" * 40)
        
        # 잠재력 목록 순회
        if not data['mapped_potentials']:
            print("  (No Potentials)")
        
        for mapped_pot_idx in data['mapped_potentials']:
            real_pot_id = get_real_id(mapped_pot_idx, pot_map)
            
            # 우선순위 값 (기본값 2: Lv.1 권장)
            priority = data['marks'].get(mapped_pot_idx, 2)
            
            # 우선순위 텍스트 변환
            p_text = {
                5: "★ Lv.6 Essential",
                4: "Lv.6 Recommended",
                3: "★ Lv.1 Essential",
                2: "Lv.1 Recommended",
                1: "Wait/Later"
            }.get(priority, f"Priority {priority}")

            print(f"  - Potential ID {real_pot_id:<5} : {p_text}")
            
    print("\n" + "="*60)

# === 테스트용 실행 블록 ===
if __name__ == "__main__":
    # 테스트용 URL (필요 시 수정하여 사용)
    TARGET_URL = "https://jforplay.github.io/sstoy/app.html#build=v2d-Hig_gu6Y*)U%3E8%60%40Kdg%7DSnju3%3Bzjeg%3D!eC!ls!nabwLRoo~%5Bywg%7C.RM_D%5Bz%2F.V%7BWSxR%2BN.B%60nYwE%7Bqfv%5D9%23%7D%3Cb%7D%7D%7CY%3E~ZZ%3Ahj3%25~%25qEV%7BRkA%25S%7D6cg%24fLGBr~5CZzQ6R%5DzwRIec_q1_%24!_fXboNqIIBI%22qPGOBVCjkuv%402fqqHg%5Ew%5DMV%60aC%3AyCrs%3DVK)u%5D%3FTq(%5EW%3E%5DkqPQIE%3BHX%3D4aA2%3D4%2BnHE2%407!jC66%40K~IC"
    print(f"Analyzing: {TARGET_URL[:50]}...")
    logger.info(f"=== Analysis Start: {TARGET_URL} ===")

    decoded = decoder.decode_url_raw(TARGET_URL)
    if "error" in decoded:
        logger.error(f"Decoding Error: {decoded['error']}") # [추가]
        print(f"Error: {decoded['error']}")
        sys.exit(1)
    logger.info(f"Analyzer Result:\n{json.dumps(decoded, indent=4, ensure_ascii=False)}")
    
    if "build=" in TARGET_URL:
        analyze_build_formatted(TARGET_URL)
    else:
        print("스크립트 내 TARGET_URL 변수에 유효한 빌드 URL을 입력해주세요.")