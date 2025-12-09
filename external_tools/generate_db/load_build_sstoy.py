import json
import os
import zlib
from urllib.parse import unquote

# =============================================================================
# [설정] 우선순위 정수 매핑 (SSToy Raw Value -> User Defined Value)
# =============================================================================
# SSToy Raw: 1=필수, 2=후순위, 3=다다익선, 4=명함만
# User Req : 1=필수, 2=다다익선, 3=명함만, 4=후순위
PRIORITY_MAP = {
    1: 1,  # 필수 -> 필수
    2: 4,  # 후순위 -> 후순위
    3: 2,  # 다다익선 -> 다다익선
    4: 3   # 명함만 -> 명함만
}
DEFAULT_PRIORITY = 0 # 마크가 없지만 찍혀있는 잠재력의 기본값

# =============================================================================
# [PART 1] SSToy URL 해석 로직 (Decoder)
# =============================================================================

BASE91_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{|}~"'
SHARE_PREFIX_DEFLATE = 'v2d-'

def base91_decode(encoded_str):
    if not encoded_str: return b''
    b, n, v = 0, 0, -1
    output = bytearray()
    for char in encoded_str:
        p = BASE91_CHARS.find(char)
        if p == -1: continue
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

def read_varint(data, offset):
    result, shift, pos = 0, 0, offset
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0: return result, pos
        shift += 7
    raise ValueError("Invalid varint")

def extract_character_info(hash_str):
    """URL에서 압축된 빌드 정보를 추출 (마크 정보 포함)"""
    
    # [수정됨] 전체 URL이 입력되었을 경우 'build=' 뒷부분만 추출
    if 'build=' in hash_str:
        hash_str = hash_str.split('build=')[-1]
    
    decoded_str = unquote(hash_str)
    
    # 접두사 확인
    if not decoded_str.startswith(SHARE_PREFIX_DEFLATE):
        return {"error": f"올바른 v2d 형식이 아닙니다. (입력값 시작: {decoded_str[:10]}...)"}
    
    encoded_payload = decoded_str[len(SHARE_PREFIX_DEFLATE):]
    try:
        compressed_bytes = base91_decode(encoded_payload)
        try:
            data = zlib.decompress(compressed_bytes, -15)
        except:
            data = zlib.decompress(compressed_bytes)
    except Exception as e:
        return {"error": f"디코딩 실패: {e}"}

    offset = 0
    version, offset = read_varint(data, offset)
    name_len, offset = read_varint(data, offset)
    build_name = data[offset:offset+name_len].decode('utf-8')
    offset += name_len
    slot_mask = data[offset]
    offset += 1
    
    characters_info = {}
    positions = ['master', 'assist1', 'assist2']
    
    for i, pos_key in enumerate(positions):
        if (slot_mask & (1 << i)) == 0: continue
        
        char_idx, offset = read_varint(data, offset)
        
        # 선택된 잠재력 리스트
        pot_count, offset = read_varint(data, offset)
        potentials = []
        for _ in range(pot_count):
            pot_idx, offset = read_varint(data, offset)
            potentials.append(pot_idx)
            
        # 잠재력 레벨 (스킵)
        level_count, offset = read_varint(data, offset)
        prev_key = 0
        for _ in range(level_count):
            key_delta, offset = read_varint(data, offset)
            key = prev_key + key_delta
            _, offset = read_varint(data, offset) # 값 읽고 버림
            prev_key = key
            
        # 잠재력 마크 정보 추출
        mark_count, offset = read_varint(data, offset)
        marks = {}
        prev_mark = 0
        for _ in range(mark_count):
            delta, offset = read_varint(data, offset)
            pot_idx = prev_mark + delta
            code = data[offset]
            offset += 1
            marks[pot_idx] = code
            prev_mark = pot_idx

        characters_info[pos_key] = {
            "char_idx": char_idx,
            "potentials": potentials,
            "marks": marks
        }
        
    return {
        "build_name": build_name,
        "characters": characters_info
    }

# =============================================================================
# [PART 2] 사용자 포맷 변환 로직 (Converter)
# =============================================================================

def convert_url_to_my_format(url):
    # 1. mapping_db.json 로드
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'mapping_db.json')
    
    if not os.path.exists(db_path):
        print("❌ 'mapping_db.json' 파일이 없습니다. generate_mapping_db.py를 먼저 실행해주세요.")
        return None

    with open(db_path, 'r', encoding='utf-8') as f:
        mapping_db = json.load(f)

    # 2. URL 해석
    raw_data = extract_character_info(url)
    if "error" in raw_data:
        print(f"❌ 파싱 에러: {raw_data['error']}")
        return None

    print(f"✅ 빌드명: {raw_data['build_name']}")

    # 3. 데이터 변환
    final_output = {
        "build_name": raw_data['build_name'],
        "characters": {}
    }
    
    sstoy_id_map = mapping_db["sstoy_index_map"]
    sstoy_pot_map = mapping_db["sstoy_pot_map"]

    for pos_key, char_info in raw_data['characters'].items():
        # 캐릭터 ID 변환
        idx = char_info['char_idx']
        if idx < 1 or idx > len(sstoy_id_map): continue
        real_char_id = str(sstoy_id_map[idx - 1])
        
        if real_char_id not in mapping_db["characters"]: continue
        
        char_db = mapping_db["characters"][real_char_id]
        char_name = char_db["name"]
        pot_key_map = char_db["potentials"]

        if char_name not in final_output["characters"]:
            final_output["characters"][char_name] = {}
        
        target_role = "main" if pos_key == "master" else "sub"
        
        # 마크 정보 (인덱스 -> 코드)
        marks_by_idx = char_info.get('marks', {})
        
        for pot_idx in char_info['potentials']:
            # 잠재력 ID 변환
            if pot_idx < 1 or pot_idx > len(sstoy_pot_map): continue
            real_pot_id = str(sstoy_pot_map[pot_idx - 1])
            
            if real_pot_id in pot_key_map:
                key_info = pot_key_map[real_pot_id]
                if target_role in key_info:
                    user_key = key_info[target_role]
                    
                    # 마크 코드 확인 (없으면 None)
                    sstoy_code = marks_by_idx.get(pot_idx)
                    
                    # 사용자 정의 정수로 변환 (매핑 없으면 기본값 0)
                    user_priority = PRIORITY_MAP.get(sstoy_code, DEFAULT_PRIORITY)
                    
                    final_output["characters"][char_name][user_key] = user_priority

    return final_output

if __name__ == "__main__":
    # 테스트용 전체 URL
    input_url = "https://jforplay.github.io/sstoy/app.html#build=v2d-XiUyou%2BB_%7CSk%2CQ%2CGWi%5EW2Odyx4No%3FvD*%2FHFPzdYQ%22yW!6CjXEM)%2BV%26EH%2Cw%3Ajoi%60RX~%5D%3Ac!_r%3DUylP(Gp.Uv)i%3C%3B9vF896%3B2pz%252o%7DWgd%4074Q9Xuz%2BZl*DHCI(2V0%2CR6%7D%24WX%7BFF4Mz)vo%5EVQzFXO(%26S~wJ%2B%24H%3F47RC%2BJO_UFJ%3BPw%2CZ.khEf%3B%5B~JNE6Y~fyD!A"
    
    result = convert_url_to_my_format(input_url)
    
    if result:
        print("\n=== 변환 결과 (JSON) ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))