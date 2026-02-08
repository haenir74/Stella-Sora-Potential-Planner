import json
import requests
import re
import sys
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

# 로거 설정
logger = logging.getLogger("Formatter")

# =========================================================
# [Import] 표준 상대 경로 방식
# =========================================================
try:
    from config import (
        CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, 
        PRESETS_DIR
    )
    from . import decoder
except ImportError:
    current_path = Path(__file__).resolve()
    app_root = current_path.parent.parent.parent
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    from config import (
        CHARACTER_DB_URL, POTENTIAL_DB_URL, CHAR_NAME_DB_URL, 
        PRESETS_DIR
    )
    import decoder

# =========================================================
# 헬퍼 함수
# =========================================================

def log_msg(msg: str, level="info"):
    print(f"[Formatter] {msg}")
    if level == "error": logger.error(msg)
    elif level == "warning": logger.warning(msg)
    else: logger.info(msg)

def sanitize_filename(name: str) -> str:
    """파일명으로 쓸 수 없는 특수문자를 제거합니다."""
    # 윈도우/리눅스 금지 문자 제거: \ / : * ? " < > |
    safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
    return safe_name.strip() or "Untitled_Build"

def fetch_db(url: str, name: str) -> Dict[str, Any]:
    log_msg(f"Downloading {name}...")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_msg(f"{name} 다운로드 실패: {e}", "error")
        return {}

def build_id_mapping(db_json: Dict[str, Any]) -> Dict[int, str]:
    mapping = {}
    pattern = re.compile(r"Character\.(\d+)\.\d+")
    
    if not db_json: return mapping

    count = 0
    for key, val in db_json.items():
        if not isinstance(val, str): continue # 안전장치

        match = pattern.search(key)
        if match:
            mapping[int(match.group(1))] = val
            count += 1
        elif key.isdigit():
            mapping[int(key)] = val
            count += 1
            
    log_msg(f"매핑 테이블 생성 완료: {count}개 로드됨.")
    return mapping

# =========================================================
# 메인 로직 수정: output_path(전체경로) -> save_dir(폴더)
# =========================================================
def save_build_to_json(url: str, save_dir: str) -> (bool, str):
    log_msg(f"=== 작업 시작 (대상 폴더: {save_dir}) ===")

    # 1. DB 로드
    char_db = fetch_db(CHAR_NAME_DB_URL, "Character Name DB")
    if not char_db: return False, "DB 다운로드 실패"

    char_map = build_id_mapping(char_db)
    
    # 2. 디코딩
    decoded = decoder.decode_url_raw(url)
    if "error" in decoded:
        return False, f"디코딩 오류: {decoded['error']}"

    # 3. 파일명 결정 [핵심 수정]
    build_name = decoded.get("build_name", "Unknown Build")
    file_name = f"{sanitize_filename(build_name)}.json"
    output_path = os.path.join(save_dir, file_name)

    log_msg(f"빌드 이름 감지: '{build_name}' -> 파일명: '{file_name}'")

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
        sstoy_id = data['mapped_char_idx']
        
        char_name_raw = char_map.get(sstoy_id)
        
        if not char_name_raw or not isinstance(char_name_raw, str):
            log_msg(f"[{pos}] 매핑 실패: ID {sstoy_id}", "warning")
            continue

        char_key = char_name_raw.lower().replace(" ", "_")
        log_msg(f"[{pos}] 매핑: {sstoy_id} -> {char_key}")
        
        potentials_dict = {}
        for mapped_pot_idx in data['mapped_potentials']:
            priority = data['marks'].get(mapped_pot_idx, 2) 
            potentials_dict[str(mapped_pot_idx)] = priority
            
        result_json["characters"][char_key] = potentials_dict

    # 5. 저장
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, indent=4, ensure_ascii=False)
        
        # 성공 시 저장된 파일 경로를 반환
        return True, output_path 
        
    except Exception as e:
        log_msg(f"저장 실패: {e}", "error")
        return False, f"저장 실패: {e}"

# 구버전 호환용 (사용 안 함)
def run(url: str, output_path: str):
    return save_build_to_json(url, os.path.dirname(output_path))