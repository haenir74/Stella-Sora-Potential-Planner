import sys
import requests
import json
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

def get_char_name(char_id: int, name_db: Dict[str, str]) -> str:
    """실제 ID를 기반으로 이름을 찾습니다."""
    if not name_db: return f"Unknown_{char_id}"
    # DB 키 형식: "Character.{ID}.1" 등
    key = f"Character.{char_id}.1"
    return name_db.get(key, f"Unknown_{char_id}")

def analyze_build_formatted(url: str):
    """SSToy 빌드 URL을 해독하여 콘솔에 상세 정보를 출력합니다."""
    
    # 1. URL 디코딩 (이제 decoder가 실제 ID를 반환함)
    decoded = decoder.decode_sstoy_url(url)
    if "error" in decoded:
        logger.error(decoded["error"])
        return
    
    # 2. 이름 조회를 위한 DB 가져오기 (필요한 경우)
    name_db = fetch_db(CHAR_NAME_DB_URL, "Character Name")
    
    # 3. 결과 출력
    build_name = decoded['build_name']
    print("\n" + "="*60)
    print(f"🏗️  Build Analysis: {build_name} (v{decoded.get('version', '?')})")
    print("="*60)
    
    raw_chars = decoded['raw_characters']
    positions = ['master', 'assist1', 'assist2']
    
    for pos in positions:
        if pos not in raw_chars:
            continue
            
        data = raw_chars[pos]
        
        # decoder가 이미 실제 ID를 반환하므로 바로 사용
        real_char_id = int(data['char_id'])
        char_name = get_char_name(real_char_id, name_db)
        
        print(f"\n[{pos.upper()}] {char_name} (ID: {real_char_id})")
        print("-" * 40)
        
        # 잠재력 목록
        pot_list = data.get('potentials', [])
        marks = data.get('marks', {})
        
        if not pot_list:
            print("  (No Potentials)")
        
        for real_pot_id in pot_list:
            # 우선순위 값
            priority = marks.get(real_pot_id, 2)
            
            # 우선순위 텍스트 변환
            p_text = {
                5: "★ Lv.6 Essential",
                4: "Lv.6 Recommended",
                3: "★ Lv.1 Essential",
                2: "Lv.1 Recommended",
                1: "Wait/Later"
            }.get(priority, f"Priority {priority}")

            print(f"  - Potential ID {real_pot_id:<6} : {p_text}")
            
    print("\n" + "="*60)

if __name__ == "__main__":
    TARGET_URL = "https://jforplay.github.io/sstoy/app.html#build=v2d-Hig_gu6Y..." # 테스트용 URL
    
    if len(sys.argv) > 1:
        TARGET_URL = sys.argv[1]

    if "build=" in TARGET_URL or "v2d-" in TARGET_URL or "v3d-" in TARGET_URL:
        analyze_build_formatted(TARGET_URL)
    else:
        print("유효한 SSToy URL을 입력해주세요.")