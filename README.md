# Potential Planner

게임 화면을 실시간으로 분석하여 캐릭터를 인식하고, 사전에 설정된 빌드(Build) 우선순위에 따라 최적의 스킬 카드를 오버레이로 하이라이트 해줍니다.

---

## 주요 기능 (Key Features)

* **실시간 화면 인식 (Real-time Detection)**
    * `MSS`와 `OpenCV`를 활용하여 끊김 없는 고속 스캔을 지원합니다.
    * **2단계 인식 시스템:** 캐릭터 얼굴을 먼저 식별한 후 해당 캐릭터의 스킬만 대조하여 시스템 리소스를 절약합니다.

* **스마트 오버레이 (Smart Overlay)**
    * 게임 화면 위에 추천 등급(Essential, Lv.6, Lv.1)에 따라 색상별 테두리와 텍스트를 표시합니다.
    * **Click-through 지원:** 오버레이 창이 마우스 입력을 가로채지 않고 투과시키므로, 오버레이를 켠 상태에서도 자유로운 게임 플레이가 가능합니다.

* **해상도 자동 대응 (Resolution Aware)**
    * 게임 창의 크기가 변하거나 해상도가 달라져도, 상대 좌표 비율(Ratio) 계산을 통해 정확한 인식 위치를 자동으로 추적합니다.
    * 게임 창 위치 이동 시 자동으로 오버레이 위치가 동기화됩니다.

* **빌드 관리 시스템 (Build Management)**
    * `JSON` 파일을 통해 캐릭터별 스킬 우선순위를 손쉽게 관리하고 공유할 수 있습니다.
    * 프로그램 내에서 빌드 파일을 실시간으로 교체할 수 있습니다.

* **디버그 모드 (Debug Mode)**
    * 인식 범위(ROI)와 현재 인식된 이미지의 일치율(Score)을 실시간으로 시각화하여, 인식 문제를 쉽게 진단할 수 있습니다.

---

## 다운로드 및 실행 (For Users)

### 1. 설치 및 준비
1. 배포된 `PotentialPlanner_v1.0.0.zip` 파일을 다운로드합니다.
2. 압축을 풉니다.
    > **주의:** 폴더 내의 `templates/` (이미지 폴더)와 `presets/` (빌드 폴더)는 `PotentialPlanner.exe`와 **반드시 같은 폴더**에 있어야 합니다.

### 2. 실행 방법
1. **게임 실행:** 스텔라소라 게임 클라이언트를 먼저 실행합니다.
2. **프로그램 실행:** `PotentialPlanner.exe`를 실행합니다.
3. **빌드 선택:** 드롭다운 메뉴에서 원하는 빌드(예: `example_build.json`)를 선택합니다.
4. **시작:** `▶` 버튼을 누르면 감시가 시작됩니다.

---

## 개발 환경 설정 (For Developers)

이 섹션은 소스 코드를 직접 수정하거나 기능을 추가하려는 개발자를 위한 안내입니다.

### 1. 필수 요구 사항
* Python 3.8 이상
* Windows OS (WinAPI 사용으로 인해 타 OS 호환 불가)

### 2. 라이브러리 설치
`requirements.txt`가 `app` 폴더 내에 위치합니다. 아래 명령어로 `app` 폴더로 이동 후 패키지를 설치하세요.
pip install -r requirements.txt

### 3. 프로젝트 빌드
build.bat을 실행해서 exe 파일로 빌드합니다.

---

## 🛡️ 보안 및 프라이버시 (Security & Privacy)

본 프로그램은 게임 클라이언트의 메모리를 변조하거나 패킷을 가로채지 않습니다. 오직 `Windows API`와 `OpenCV`를 통해 화면에 송출되는 이미지를 캡처하여 분석하는 **비침해적(Non-invasive) 방식**으로 작동합니다.
모든 이미지 분석 및 연산 과정은 사용자의 PC 내에서 오프라인으로 수행됩니다. 게임 화면이나 개인 정보를 외부 서버로 전송하거나 수집하지 않습니다.

---

## ⚖️ 저작권 및 법적 고지 (Copyright & Legal Notice)

1. 본 소프트웨어는 게임 '스텔라 소라'의 팬 프로젝트인 **비공식 툴**이며, 퍼블리셔인 **Yostar Inc.** 또는 개발사와 어떠한 공식적인 제휴 관계도 없습니다.

2. 프로젝트 내에서 사용된 모든 게임 관련 자산(캐릭터 이미지, 아이콘, 게임 데이터, 고유 명사 등)의 저작권 및 지적 재산권은 전적으로 **Yostar Inc.** 및 해당 원작자에게 귀속됩니다.
   본 프로젝트는 해당 저작물을 침해할 의도가 없으며, 게임 플레이를 보조하기 위한 목적으로만 사용됩니다.

3. 이 프로그램은 무료로 배포되며, 어떠한 형태의 금전적 이득을 취하지 않습니다.

4. 본 소프트웨어의 사용으로 인해 발생하는 모든 결과(게임 계정 제재, 데이터 손실, 하드웨어 손상 등)에 대한 책임은 전적으로 **사용자 본인**에게 있습니다. 개발자는 어떠한 경우에도 본 소프트웨어 사용과 관련하여 발생한 손해에 대해 법적 책임을 지지 않습니다.

---

## ⚖️ Disclaimer

1. This software is an **unofficial fan project** and is not endorsed by, directly affiliated with, or sponsored by **Yostar Inc.**
2. All game assets, including but not limited to images, icons, data, and character names, are the intellectual property of **Yostar Inc.** and their respective owners.
3. This tool is created solely for gameplay assistance and educational purposes. No copyright infringement is intended.
4. This software is provided "AS-IS", without warranty of any kind. The developer is not responsible for any bans, data loss, or damages resulting from its use. **Use at your own risk.**