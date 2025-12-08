import os
import cv2
import numpy as np
import pickle

def create_mask(h, w):
    """흰색 원, 검은 배경의 마스크 생성"""
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    radius = min(w, h) // 2
    cv2.circle(mask, center, radius, 255, -1)
    return mask

def get_latest_mtime(folder_path):
    """폴더 내 모든 파일 중 가장 최근 수정 시간을 반환"""
    latest_time = 0
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.png', '.jpg')):
                full_path = os.path.join(root, file)
                mtime = os.path.getmtime(full_path)
                if mtime > latest_time:
                    latest_time = mtime
    return latest_time

def load_templates(base_folder):
    """
    이미지를 로드하되, pickle 캐시를 우선적으로 확인합니다.
    """
    face_templates = {} 
    skill_templates = {}
    
    cache_path = os.path.join(base_folder, "templates.cache")
    
    # 1. 캐시 유효성 검사
    # 캐시 파일이 존재하고, 이미지 폴더보다 나중에 만들어졌다면 캐시를 씁니다.
    if os.path.exists(cache_path):
        cache_mtime = os.path.getmtime(cache_path)
        last_image_mtime = get_latest_mtime(base_folder)
        
        if cache_mtime > last_image_mtime:
            print(">>> [시스템] 캐시된 데이터 로드 중... (Fast Load)")
            try:
                with open(cache_path, 'rb') as f:
                    data = pickle.load(f)
                print(">>> 로딩 완료 (Cached).\n")
                return data['face'], data['skill']
            except Exception as e:
                print(f"[경고] 캐시 로드 실패 (손상됨): {e}")
                # 실패하면 아래 로직(새로 로딩)으로 넘어감
        else:
            print(">>> [시스템] 변경사항 감지됨. 템플릿 재생성 중...")
    else:
        print(">>> [시스템] 초기 리소스 로딩 및 캐시 생성 중...")

    # ----------------------------------------------------
    # 2. 원본 이미지 로딩 수행
    # ----------------------------------------------------
    icons_path = os.path.join(base_folder, "icons")
    potentials_path = os.path.join(base_folder, "potentials")

    if not os.path.exists(base_folder):
        return {}, {}

    # (A) 얼굴 아이콘 로딩 + 마스크 생성
    if os.path.exists(icons_path):
        for filename in os.listdir(icons_path):
            if not filename.lower().endswith(('.png', '.jpg')): continue
            
            char_name = os.path.splitext(filename)[0]
            full_path = os.path.join(icons_path, filename)
            
            img = cv2.imread(full_path, 0)
            if img is None: continue
            
            h, w = img.shape
            mask = create_mask(h, w)
            face_templates[char_name] = (img, mask)
    
    # (B) 잠재력(스킬) 로딩
    if os.path.exists(potentials_path):
        for char_folder in os.listdir(potentials_path):
            char_path = os.path.join(potentials_path, char_folder)
            if not os.path.isdir(char_path): continue
            
            char_name = char_folder
            if char_name not in skill_templates:
                skill_templates[char_name] = {}

            for filename in os.listdir(char_path):
                if not filename.lower().endswith(('.png', '.jpg')): continue
                full_path = os.path.join(char_path, filename)
                img = cv2.imread(full_path, 0)
                if img is None: continue
                skill_templates[char_name][filename] = img

    # ----------------------------------------------------
    # 3. 캐시 파일 저장 (Pickle Dump)
    # ----------------------------------------------------
    try:
        with open(cache_path, 'wb') as f:
            # 딕셔너리로 묶어서 저장
            pickle.dump({'face': face_templates, 'skill': skill_templates}, f)
        print(f">>> [시스템] 캐시 파일 생성 완료: {cache_path}")
    except Exception as e:
        print(f"[오류] 캐시 저장 실패: {e}")

    print(f">>> 로딩 완료.\n")
    return face_templates, skill_templates