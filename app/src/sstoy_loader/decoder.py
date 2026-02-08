import zlib
import logging
import re
from urllib.parse import unquote
from typing import Dict, Any, List, Tuple

# 로거 설정
logger = logging.getLogger("SSToyDecoder")

# === 상수 설정 ===
BASE91_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{|}~"'
POSITIONS = ['master', 'assist1', 'assist2']

# === 마크 우선순위 매핑 ===
MARK_PRIORITY_MAP = {
    1: 5,  # 필수 (Essential)
    3: 4,  # 다다익선 (Recommended)
    4: 3,  # 명함 필수
    0: 2,  # 명함만 (Minimum)
    2: 1   # 후순위 (Low)
}

def base91_decode(encoded_str: str) -> bytes:
    if not encoded_str: return b''
    b, n, v = 0, 0, -1
    output = bytearray()
    decode_table = {c: i for i, c in enumerate(BASE91_CHARS)}
    
    for char in encoded_str:
        if char not in decode_table: continue
        p = decode_table[char]
        if v < 0:
            v = p
        else:
            v += p * 91
            b |= v << n
            n += 13
            while n >= 8:
                output.append(b & 255)
                b >>= 8
                n -= 8
            v = -1
    if v > -1:
        output.append((b | v << n) & 255)
        
    return bytes(output)

def read_varint(data: bytes, offset: int) -> Tuple[int, int]:
    """Varint 형식의 정수를 읽어냅니다."""
    result, shift = 0, 0
    pos = offset
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0:
            return result, pos
        shift += 7
    raise EOFError("Varint 읽기 실패 (데이터 끝 도달)")

def decode_url_raw(url: str) -> Dict[str, Any]:
    """
    SSToy URL을 해독하여 Raw Data를 반환합니다.
    (v3d 포맷 지원 및 상세 로깅 추가)
    """
    logger.info(f"=== Decoding Start: {url[:30]}... ===")

    if "build=" in url:
        url = url.split("build=")[1]
    url = unquote(url)
    
    # [수정] 정규표현식으로 버전 및 타입(압축여부) 파싱 (예: v3d, v2d)
    match = re.match(r"^v(\d+)([dr])-(.+)$", url)
    
    if match:
        version = int(match.group(1))
        data_type = match.group(2)
        payload = match.group(3)
        is_deflated = (data_type == 'd')
        logger.info(f"Header Parsed - Version: {version}, Type: {data_type} (Deflated: {is_deflated})")
    else:
        # 기존 하위 호환성 유지 (혹시 모를 구형 URL)
        if url.startswith("v2d-"):
            version = 2
            is_deflated = True
            payload = url[4:]
        elif url.startswith("v2r-"):
            return {"error": "지원하지 않는 형식 (v2r - 압축되지 않은 데이터)"}
        else:
            logger.error(f"URL 형식 불일치: {url}")
            return {"error": "URL 형식 불일치"}
    
    try:
        # Base91 디코딩
        compressed = base91_decode(payload)
        
        # Zlib 압축 해제
        if is_deflated:
            try:
                # wbits=-15: 헤더 없는 Raw Deflate 처리
                data = zlib.decompress(compressed, -15)
            except zlib.error:
                # 실패 시 표준 zlib 포맷 시도
                data = zlib.decompress(compressed)
        else:
            data = compressed
            
        # [DEBUG] 디코딩된 Raw Data Hex 덤프 기록
        logger.info(f"Raw Data Length: {len(data)} bytes")
        logger.info(f"Raw Data (Hex): {data.hex().upper()}")
            
    except Exception as e:
        logger.error(f"디코딩/압축해제 실패: {e}")
        return {"error": f"디코딩 실패: {e}"}

    try:
        offset = 0
        
        # 스트림 내부 버전 읽기
        stream_version, offset = read_varint(data, offset)
        
        # 이름 길이 및 이름 읽기
        name_len, offset = read_varint(data, offset)
        build_name = data[offset:offset+name_len].decode('utf-8')
        offset += name_len
        
        logger.info(f"Parsed Info - StreamVer: {stream_version}, Name: '{build_name}'")
        
        # 슬롯 마스크 읽기
        slot_mask = data[offset]
        offset += 1
        logger.info(f"Slot Mask: {bin(slot_mask)}")
        
        parsed_characters = {}
        
        for i, pos_name in enumerate(POSITIONS):
            if (slot_mask & (1 << i)) == 0: continue
            
            logger.info(f"--- Parsing Position: {pos_name} ---")
                
            # 1. 캐릭터 매핑 인덱스
            char_map_idx, offset = read_varint(data, offset)
            logger.info(f"[{pos_name}] Char Map Index: {char_map_idx}")
            
            # 2. 잠재력 매핑 인덱스 리스트
            pot_count, offset = read_varint(data, offset)
            potentials = []
            for _ in range(pot_count):
                p_idx, offset = read_varint(data, offset)
                potentials.append(p_idx)
            logger.info(f"[{pos_name}] Potentials ({pot_count}): {potentials}")
                
            # 3. 잠재력 레벨
            level_count, offset = read_varint(data, offset)
            pot_levels = {}
            prev_key = 0
            for _ in range(level_count):
                key_delta, offset = read_varint(data, offset)
                val, offset = read_varint(data, offset)
                real_key = prev_key + key_delta
                pot_levels[real_key] = val + 1
                prev_key = real_key
            logger.info(f"[{pos_name}] Levels: {pot_levels}")
                
            # 4. 마크 (우선순위)
            mark_count, offset = read_varint(data, offset)
            marks = {}
            prev_mark = 0
            for _ in range(mark_count):
                delta, offset = read_varint(data, offset)
                code = data[offset]
                offset += 1
                pot_idx = prev_mark + delta
                priority = MARK_PRIORITY_MAP.get(code, 0) 
                marks[pot_idx] = priority
                prev_mark = pot_idx
            logger.info(f"[{pos_name}] Marks: {marks}")
                
            parsed_characters[pos_name] = {
                "mapped_char_idx": char_map_idx,
                "mapped_potentials": potentials,
                "potential_levels": pot_levels,
                "marks": marks
            }

        result_data = {
            "build_name": build_name,
            "raw_characters": parsed_characters,
            "version": version # 디버깅용 버전 정보 포함
        }
        logger.info(f"Final Parsed Result: {result_data}")        
        return result_data

    except Exception as e:
        logger.error(f"파싱 중 오류 발생 (Offset: {offset}): {e}", exc_info=True)
        return {"error": f"파싱 오류: {e}"}