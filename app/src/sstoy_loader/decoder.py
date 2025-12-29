import zlib
from urllib.parse import unquote

# === 설정: 사용자 입력 URL ===
TARGET_URL = "https://jforplay.github.io/sstoy/app.html#build=v2d-hcWyouZY~47~%7C%23k%2300ruyGeb)H3GU4%5EX9pnZ%5D(tY4LkS%23Q6IA%3Ch*%3D6L3.(upfE%5D%24yFx%2C%2F)U%3A~%7Di!NWy1v%246h8%40j%3C%3CUcjWS%26%2C(_Q35%3E%2FJctFl3Wq%24aLgS%7Bh%40bf8BW50g6(kL6%40O%23LV0F%23Btvlly%5DGGNK%2CQI!0!O(yxN%60c6%7D%40F_7RH6%5BBy0%3AFT.CA"

# === 해독 로직 (Base91 + Zlib + VarInt) ===
BASE91_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{|}~"'

def base91_decode(encoded_str):
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

def read_varint(data, offset):
    result, shift = 0, 0
    while True:
        if offset >= len(data): raise EOFError
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        if (byte & 0x80) == 0: return result, offset
        shift += 7

def decode_sstoy(url):
    # 1. URL 파싱 및 전처리
    if "build=" in url: url = url.split("build=")[1]
    decoded_str = unquote(url)
    if decoded_str.startswith("v2d-"): decoded_str = decoded_str[4:]
    
    # 2. 압축 해제
    try:
        compressed = base91_decode(decoded_str)
        try:
            data = zlib.decompress(compressed, -15)
        except:
            data = zlib.decompress(compressed)
    except Exception as e:
        return f"디코딩 실패: {e}"

    # 3. 바이너리 데이터 읽기
    offset = 0
    try:
        version, offset = read_varint(data, offset)
        
        # 빌드 이름 길이 및 문자열
        name_len, offset = read_varint(data, offset)
        build_name = data[offset:offset+name_len].decode('utf-8')
        offset += name_len
        
        slot_mask = data[offset]
        offset += 1
        
        result = {"build_name": build_name, "characters": []}
        positions = ["Master", "Assist1", "Assist2"]
        
        for i, pos in enumerate(positions):
            if (slot_mask & (1 << i)) == 0: continue
            
            # 캐릭터 ID (이 숫자가 DB의 인덱스입니다)
            char_idx, offset = read_varint(data, offset)
            
            # 잠재력 목록
            pot_count, offset = read_varint(data, offset)
            potentials = []
            for _ in range(pot_count):
                p_idx, offset = read_varint(data, offset)
                potentials.append(p_idx)
                
            # 잠재력 레벨 (스킵)
            level_count, offset = read_varint(data, offset)
            for _ in range(level_count):
                _, offset = read_varint(data, offset) # key_delta
                _, offset = read_varint(data, offset) # val
                
            # 마크 정보
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

            result["characters"].append({
                "position": pos,
                "char_idx": char_idx,  # ★ DB 파일에서 찾아야 할 핵심 인덱스
                "potentials": potentials,
                "marks": marks
            })
            
        return result
    except Exception as e:
        return f"파싱 중 에러: {e}"

# 실행 및 출력
data = decode_sstoy(TARGET_URL)
import json
print(json.dumps(data, indent=2, ensure_ascii=False))