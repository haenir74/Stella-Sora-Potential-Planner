import json
import os

class BuildLoader:
    def __init__(self, build_file_path="builds.json"):
        self.build_data = {}
        self.target_map = {} 
        self.load_build(build_file_path)

    def load_build(self, path):
        if not os.path.exists(path):
            print(f"[빌드 로더] 오류: '{path}' 파일을 찾을 수 없습니다.")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.build_data = json.load(f)
            
            if "characters" in self.build_data:
                self.target_map = self.build_data["characters"]
            
            build_name = self.build_data.get('build_name', 'Unknown')
            print(f"[빌드 로더] '{build_name}' 설정 로드 완료.")
            
        except Exception as e:
            print(f"[빌드 로더] JSON 파싱 오류: {e}")

    def get_priority(self, char_name, filename):
        """
        파일명에 해당하는 스킬의 우선순위(1~3)를 반환합니다.
        반환값:
         - 3: 필수 (Essential)
         - 2: 6레벨 권장 (Recommended Lv.6)
         - 1: 1레벨 권장 (Recommended Lv.1)
         - 0: 빌드 미포함
        """
        if char_name not in self.target_map:
            return 0

        # 확장자 제거 (예: main_06.png -> main_06)
        skill_key = os.path.splitext(filename)[0]
        
        # 설정된 값 반환 (없으면 0)
        return self.target_map[char_name].get(skill_key, 0)