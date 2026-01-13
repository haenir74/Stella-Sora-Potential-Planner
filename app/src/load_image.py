import cv2
import numpy as np
import logging
import pickle
import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional, Any, Union

# ------------------------------------------------------
# 1. 설정 및 경로 처리
# ------------------------------------------------------
try:
    from config import get_resource_path, TEMPLATES_DIR
except ImportError:
    # src 폴더 내부에서 실행 시 상위 폴더 모듈을 못 찾을 경우 대비
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config import get_resource_path, TEMPLATES_DIR

# 로거 설정
logger = logging.getLogger("LoadImage")

# 타입 별칭 정의
FaceTemplateType = Dict[str, Tuple[np.ndarray, np.ndarray]] # {char_name: (img, mask)}
SkillTemplateType = Dict[str, Dict[str, np.ndarray]]        # {char_name: {filename: img}}

# ------------------------------------------------------
# 2. 유틸리티 함수
# ------------------------------------------------------
def create_mask(h: int, w: int) -> np.ndarray:
    """
    흰색 원, 검은 배경의 마스크를 생성합니다.
    OpenCV 템플릿 매칭 시 투명도 처리를 위해 사용됩니다.
    """
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    radius = min(w, h) // 2
    cv2.circle(mask, center, radius, 255, -1)
    return mask

def get_latest_mtime(folder_path: Union[str, Path]) -> float:
    """
    폴더 내 모든 이미지 파일 중 가장 최근 수정 시간을 반환합니다.
    재귀적으로 하위 폴더까지 검색합니다.
    """
    folder_path = Path(folder_path)
    latest_time = 0.0
    
    if not folder_path.exists():
        logger.warning(f"경로를 찾을 수 없음: {folder_path}")
        return 0.0

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    full_path = os.path.join(root, file)
                    mtime = os.path.getmtime(full_path)
                    if mtime > latest_time:
                        latest_time = mtime
                except OSError as e:
                    logger.warning(f"파일 시간 확인 실패 ({file}): {e}")
                    
    return latest_time

# ------------------------------------------------------
# 3. 캐시 관리 함수
# ------------------------------------------------------
def _load_from_cache(cache_path: Path) -> Optional[Dict[str, Any]]:
    """캐시 파일에서 데이터를 로드합니다."""
    try:
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
        
        # 데이터 무결성 검사 (키 확인)
        if not isinstance(data, dict) or 'face' not in data or 'skill' not in data:
            logger.warning("캐시 데이터 형식이 올바르지 않습니다.")
            return None
            
        logger.info("캐시된 데이터 로드 성공 (Fast Load)")
        return data
        
    except (pickle.UnpicklingError, EOFError) as e:
        logger.warning(f"캐시 파일 손상됨: {e}")
    except Exception as e:
        logger.warning(f"캐시 로드 중 예기치 않은 오류: {e}")
        
    return None

def _save_to_cache(cache_path: Path, data: Dict[str, Any]) -> None:
    """데이터를 캐시 파일로 저장합니다."""
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(data, f)
        logger.info(f"캐시 파일 생성 완료: {cache_path}")
    except (IOError, PermissionError) as e:
        logger.error(f"캐시 저장 실패: {e}")

# ------------------------------------------------------
# 4. 이미지 로딩 함수 (Core Logic)
# ------------------------------------------------------
def _load_face_icons(icons_path: Path) -> FaceTemplateType:
    """얼굴 아이콘 이미지를 로드하고 마스크를 생성합니다."""
    templates = {}
    
    if not icons_path.exists():
        logger.warning(f"Icons 폴더 없음: {icons_path}")
        return templates

    for entry in icons_path.iterdir():
        if not entry.is_file() or not entry.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            continue
            
        char_name = entry.stem
        
        try:
            img = cv2.imread(str(entry), cv2.IMREAD_GRAYSCALE)
            
            if img is None:
                logger.warning(f"이미지 로드 실패 (손상되었거나 경로 문제): {entry.name}")
                continue
            
            h, w = img.shape
            mask = create_mask(h, w)
            templates[char_name] = (img, mask)
            
        except cv2.error as e:
            logger.error(f"OpenCV 오류 ({entry.name}): {e}")
        except Exception as e:
            logger.error(f"알 수 없는 오류 ({entry.name}): {e}")
            
    return templates

def _load_skill_images(potentials_path: Path) -> SkillTemplateType:
    """잠재력(스킬) 이미지를 캐릭터별로 분류하여 로드합니다."""
    templates = {}
    
    if not potentials_path.exists():
        logger.warning(f"Potentials 폴더 없음: {potentials_path}")
        return templates

    for char_folder in potentials_path.iterdir():
        if not char_folder.is_dir():
            continue
            
        char_name = char_folder.name
        char_skills = {}

        loaded_files = []
        
        for entry in char_folder.iterdir():
            if not entry.is_file() or not entry.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                continue
                
            try:
                img = cv2.imread(str(entry), cv2.IMREAD_GRAYSCALE)
                
                if img is None:
                    logger.warning(f"스킬 이미지 로드 실패: {char_name}/{entry.name}")
                    continue
                    
                char_skills[entry.name] = img
                loaded_files.append(entry.name)
                
            except Exception as e:
                logger.error(f"스킬 로드 중 오류 ({char_name}/{entry.name}): {e}")
        
        if char_skills:
            templates[char_name] = char_skills
            logger.info(f"  ✅ [{char_name}] 로드됨 ({len(char_skills)}개): {loaded_files}")
        else:
            logger.warning(f"  ⚠️ [{char_name}] 폴더는 있지만 로드된 스킬 이미지가 없습니다.")
            
    return templates

# ------------------------------------------------------
# 5. 메인 로딩 함수
# ------------------------------------------------------
def load_templates(base_folder: Union[str, Path]) -> Tuple[FaceTemplateType, SkillTemplateType]:
    """
    이미지 리소스를 로드합니다. (캐시 우선 확인)
    
    Returns:
        (face_templates, skill_templates)
    """
    base_folder = Path(base_folder)
    cache_path = base_folder / "templates.cache"
    
    # 1. 캐시 유효성 검사
    use_cache = False
    if cache_path.exists():
        try:
            cache_mtime = cache_path.stat().st_mtime
            last_image_mtime = get_latest_mtime(base_folder)
            
            if cache_mtime > last_image_mtime:
                use_cache = True
            else:
                logger.info("변경사항 감지됨. 템플릿 재생성 중...")
        except OSError:
            logger.warning("파일 시간 확인 중 오류, 캐시 무시.")
            use_cache = False
            
    # 2. 캐시 로드 시도
    if use_cache:
        cached_data = _load_from_cache(cache_path)
        if cached_data:
            return cached_data['face'], cached_data['skill']

    # 3. 원본 이미지 로딩 수행 (Cache Miss or Invalid)
    logger.info("초기 리소스 로딩 및 캐시 생성 시작...")
    
    icons_path = base_folder / "icons"
    potentials_path = base_folder / "potentials"

    if not base_folder.exists():
        logger.error(f"리소스 베이스 폴더를 찾을 수 없습니다: {base_folder}")
        return {}, {}

    face_templates = _load_face_icons(icons_path)
    skill_templates = _load_skill_images(potentials_path)

    # 4. 캐시 저장
    if face_templates or skill_templates:
        _save_to_cache(cache_path, {'face': face_templates, 'skill': skill_templates})
    else:
        logger.warning("로드된 템플릿이 없어 캐시를 생성하지 않았습니다.")

    logger.info("로딩 완료.")
    return face_templates, skill_templates