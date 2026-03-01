import json
import requests
import re
import sys
import logging
import os
from pathlib import Path
from typing import Dict, Any

# 로거 설정
logger = logging.getLogger("Formatter")

# [Import] 표준 상대 경로 방식 (기존 코드 유지)
try:
    from config import CHAR_NAME_DB_URL, PRESETS_DIR
    from . import decoder
except ImportError:
    current_path = Path(__file__).resolve()
    app_root = current_path.parent.parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    from config import CHAR_NAME_DB_URL, PRESETS_DIR
    import decoder

def log_msg(msg: str, level="info"):
    print(f"[Formatter] {msg}")
    if level == "error": logger.error(msg)
    elif level == "warning": logger.warning(msg)
    else: logger.info(msg)

def sanitize_filename(name: str) -> str:
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
    return safe_name.strip() or "Untitled_Build"

def fetch_db(url: str, name: str) -> Dict[str, Any]:
    log_msg(f"Downloading {name}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        # 다운로드 실패 시 빈 딕셔너리 반환하여 진행 (ID 기반으로라도 저장)
        return {}

def build_id_to_name_mapping(db_json: Dict[str, Any]) -> Dict[int, str]:
    """Character Name DB를 사용하여 ID -> Name 매핑 테이블을 생성합니다."""
    mapping = {}
    pattern = re.compile(r"Character\.(\d+)\.\d+")
    
    if not db_json: return mapping

    count = 0
    for key, val in db_json.items():
        if not isinstance(val, str): continue 
        match = pattern.search(key)
        if match:
            mapping[int(match.group(1))] = val
            count += 1
            
    log_msg(f"ID->Name 매핑 테이블 생성 완료: {count}개 로드됨.")
    return mapping

def save_build_to_json(url: str, save_dir: str) -> (bool, str):
    log_msg(f"=== 작업 시작 (대상 폴더: {save_dir}) ===")

    # 1. DB 로드 (이름 매핑용)
    char_db = fetch_db(CHAR_NAME_DB_URL, "Character Name DB")
    id_map = build_id_to_name_mapping(char_db)
    
    # 2. 디코딩 (decoder가 실제 ID를 반환함)
    decoded = decoder.decode_sstoy_url(url)
    if "error" in decoded:
        return False, f"디코딩 오류: {decoded['error']}"

    # 3. 파일명 결정
    build_name = decoded.get("build_name", "Unknown Build")
    file_name = f"{sanitize_filename(build_name)}.json"
    output_path = os.path.join(save_dir, file_name)

    log_msg(f"빌드 이름: '{build_name}' -> 파일명: '{file_name}'")

    # 4. 변환
    result_json = {
        "build_name": build_name,
        "characters": {}
    }
    
    raw_chars = decoded.get('raw_characters', {})
    positions = ['master', 'assist1', 'assist2']

    for pos in positions:
        if pos not in raw_chars: continue
        
        data = raw_chars[pos]
        # decoder가 반환한 값은 이제 실제 ID입니다.
        real_char_id = int(data['char_id'])
        
        # 이름 찾기 (없으면 Unknown_ID)
        char_name_raw = id_map.get(real_char_id, f"Unknown_{real_char_id}")
        
        char_key = char_name_raw.lower().replace(" ", "_")
        log_msg(f"[{pos}] 처리: ID {real_char_id} -> {char_key}")
        
        potentials_dict = {}
        # marks 딕셔너리도 {Real_Pot_ID : Priority} 형태입니다.
        marks = data.get('marks', {})
        potentials_list = data.get('potentials', [])

        for pot_id in potentials_list:
            priority = marks.get(pot_id, 2)
            potentials_dict[str(pot_id)] = priority
            
        result_json["characters"][char_key] = potentials_dict

    # 5. 저장
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, indent=4, ensure_ascii=False)
        return True, output_path 
        
    except Exception as e:
        log_msg(f"저장 실패: {e}", "error")
        return False, f"저장 실패: {e}"