import json
import requests

# 1. GitHub 설정 정보
# 레포지토리: https://github.com/JforPlay/sstoy
OWNER = "JforPlay"
REPO = "sstoy"
BRANCH = "main"  # 혹시 파일을 못 찾으면 'master'로 변경해서 시도해보세요.
BASE_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/public/data"

# 데이터 파일들의 Raw URL 정의
URLS = {
    "character": f"{BASE_URL}/Character.json",
    "potential": f"{BASE_URL}/CharPotential.json",
    "language": f"{BASE_URL}/EN/Character.json" # 영어 이름 파일 경로
}

# 2. 입력 데이터 (커뮤니티 사이트 JSON 예시)
input_json_str = """
{
  "build_name": "클라루 후유카 거장용",
  "characters": [
    {
      "position": "Master",
      "char_idx": 25,
      "potentials": [612, 613, 638, 637, 622, 618, 636, 617],
      "marks": {
        "617": 4,
        "618": 3,
        "622": 1,
        "636": 2,
        "637": 1,
        "638": 1
      }
    }
  ]
}
"""

def fetch_json_from_github(url):
    """GitHub Raw URL에서 JSON 데이터를 가져옵니다."""
    try:
        response = requests.get(url)
        response.raise_for_status() # 200 OK가 아니면 에러 발생
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    print("GitHub에서 데이터를 다운로드 중입니다...")
    
    # 3. 데이터 다운로드
    char_db = fetch_json_from_github(URLS["character"])
    pot_db = fetch_json_from_github(URLS["potential"])
    lang_db = fetch_json_from_github(URLS["language"])

    if not (char_db and pot_db and lang_db):
        print("데이터 다운로드에 실패하여 작업을 중단합니다.")
        return

    input_data = json.loads(input_json_str)
    result_characters = []

    # Character ID 리스트 정렬 (char_idx 매핑용)
    # Character.json의 키들을 숫자로 변환하여 정렬
    sorted_char_ids = sorted([int(k) for k in char_db.keys()])

    # 4. 데이터 매칭 및 변환 로직
    for char_entry in input_data['characters']:
        input_idx = char_entry['char_idx']
        
        # char_idx 매핑 (1-based index라고 가정)
        if 0 < input_idx <= len(sorted_char_ids):
            real_char_id = sorted_char_ids[input_idx - 1]
        else:
            real_char_id = None
            
        char_info = {}
        
        if real_char_id:
            str_id = str(real_char_id)
            
            # 영문 이름 찾기
            name_key = char_db[str_id].get("Name")
            english_name = lang_db.get(name_key, "Unknown")
            
            char_info['Name'] = english_name
            char_info['Id'] = real_char_id
            char_info['Position'] = char_entry['position']
            
            # 잠재력(Potential) 정보 매칭
            if str_id in pot_db:
                pot_data = pot_db[str_id]
                
                # Master 포지션 잠재력 추출
                char_info['Game_Potential_IDs'] = {
                    "Specific": pot_data.get("MasterSpecificPotentialIds", []),
                    "Common": pot_data.get("CommonPotentialIds", []),
                    "Normal": pot_data.get("MasterNormalPotentialIds", [])
                }
                
                char_info['Site_Potential_Indices'] = char_entry['potentials']
                char_info['Marks'] = char_entry['marks']
            else:
                char_info['Potentials'] = "Not Found in DB"
                
        else:
            char_info['Error'] = f"Character Index {input_idx} not found"

        result_characters.append(char_info)

    # 5. 결과 출력
    final_output = {
        "build_name": input_data['build_name'],
        "converted_characters": result_characters
    }

    print("-" * 30)
    print(json.dumps(final_output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()