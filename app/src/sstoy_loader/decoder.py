import zlib
import logging
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
    """Base91 인코딩된 문자열을 바이트로 디코딩합니다."""
    if not encoded_str: return b''
    b, n, v = 0, 0, -1
    output = bytearray()
    decode_table = {c: i for i, c in enumerate(BASE91_CHARS)}
    
    for char in encoded_str:
        if char not in decode_table: continue
        p = decode_table[char]
        if v < 0: v = p
        else:
            v += p * 91
            b |= v << n
            n += 13 if (v & 8191) > 88 else 14
            while n > 7:
                output.append(b & 255)
                b >>= 8
                n -= 8
            v = -1
    if v >= 0: output.append((b | (v << n)) & 255)
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
    
    Returns:
        성공 시: {"build_name": str, "raw_characters": dict}
        실패 시: {"error": str}
    """
    if "build=" in url:
        url = url.split("build=")[1]
    url = unquote(url)
    
    is_deflated = False
    if url.startswith("v2d-"):
        url = url[4:]
        is_deflated = True
    elif url.startswith("v2r-"):
        return {"error": "지원하지 않는 형식 (v2r - 압축되지 않은 데이터)"}
    
    try:
        # Base91 디코딩 및 Zlib 압축 해제
        compressed = base91_decode(url)
        if is_deflated:
            data = zlib.decompress(compressed, -15)
        else:
            data = compressed
    except Exception as e:
        logger.error(f"디코딩/압축해제 실패: {e}")
        return {"error": f"디코딩 실패: {e}"}

    try:
        offset = 0
        version, offset = read_varint(data, offset)
        name_len, offset = read_varint(data, offset)
        
        # 빌드 이름 추출
        build_name = data[offset:offset+name_len].decode('utf-8')
        offset += name_len
        
        slot_mask = data[offset]
        offset += 1
        
        parsed_characters = {}
        
        for i, pos_name in enumerate(POSITIONS):
            if (slot_mask & (1 << i)) == 0: continue
                
            # 1. 캐릭터 매핑 인덱스
            char_map_idx, offset = read_varint(data, offset)
            
            # 2. 잠재력 매핑 인덱스 리스트
            pot_count, offset = read_varint(data, offset)
            potentials = []
            for _ in range(pot_count):
                p_idx, offset = read_varint(data, offset)
                potentials.append(p_idx)
                
            # 3. 잠재력 레벨 (사용하지 않더라도 포맷상 읽어야 함)
            level_count, offset = read_varint(data, offset)
            pot_levels = {}
            prev_key = 0
            for _ in range(level_count):
                key_delta, offset = read_varint(data, offset)
                val, offset = read_varint(data, offset)
                real_key = prev_key + key_delta
                pot_levels[real_key] = val + 1
                prev_key = real_key
                
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
                
            parsed_characters[pos_name] = {
                "mapped_char_idx": char_map_idx,
                "mapped_potentials": potentials,
                "potential_levels": pot_levels,
                "marks": marks
            }

        return {
            "build_name": build_name,
            "raw_characters": parsed_characters
        }

    except Exception as e:
        logger.error(f"파싱 중 오류 발생: {e}")
        return {"error": f"파싱 오류: {e}"}