import json
import os
import logging
from typing import Dict, Any, Union, Optional
from pathlib import Path

logger = logging.getLogger("BuildLoader")

class BuildLoader:
    def __init__(self, build_file_path: Union[str, Path] = "builds.json"):
        # 데이터 구조 정의: {char_name: {skill_key: priority}}
        self.build_data: Dict[str, Any] = {}
        self.target_map: Dict[str, Dict[str, int]] = {}
        
        # 초기화 시 바로 로드 시도
        if build_file_path:
            self.load_build(build_file_path)

    def load_build(self, path: Union[str, Path]) -> bool:
        """
        지정된 경로의 JSON 빌드 파일을 로드합니다.
        
        Returns:
            성공 시 True, 실패 시 False
        """
        path = Path(path)

        if not path.exists():
            logger.error(f"파일을 찾을 수 없습니다: {path}")
            return False

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.build_data = json.load(f)
            
            # 데이터 무결성 검사
            if "characters" in self.build_data:
                self.target_map = self.build_data["characters"]
            else:
                logger.warning(f"빌드 파일에 'characters' 키가 없습니다: {path}")
                self.target_map = {}
            
            build_name = self.build_data.get('build_name', 'Unknown')
            logger.info(f"빌드 설정 로드 완료: '{build_name}' ({path.name})")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류 (문법 확인 필요): {path}\n내용: {e}")
        except PermissionError:
            logger.error(f"파일 읽기 권한이 없습니다: {path}")
        except Exception as e:
            logger.error(f"빌드 로드 중 예기치 않은 오류: {e}")
            
        return False

    def get_priority(self, char_name: str, filename: str) -> int:
        """
        특정 캐릭터 스킬(파일명)의 우선순위를 반환합니다.
        
        Args:
            char_name: 캐릭터 이름 (폴더명/키값)
            filename: 스킬 이미지 파일명 (예: 510301.png)
            
        Returns:
            우선순위 정수값 (기본값 0)
             - 5: 6레벨 필수 (Essential Lv.6)
             - 4: 6레벨 권장 (Recommended Lv.6)
             - 3: 1레벨 필수 (Essential Lv.1)
             - 2: 1레벨 권장 (Recommended Lv.1)
             - 1: 후순위 (Wait/Later)
             - 0: 빌드 미포함
        """
        if not char_name or char_name not in self.target_map:
            return 0

        # 확장자 제거 및 안전한 키 변환 (예: "510301.png" -> "510301")
        skill_key = os.path.splitext(filename)[0]
        
        # 해당 캐릭터의 스킬 목록에서 우선순위 조회
        char_skills = self.target_map[char_name]
        priority = char_skills.get(skill_key, 0)
        
        return priority