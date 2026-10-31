# Container Workbench

엑셀 파일의 컨테이너 번호와 운송 금액을 비교하는 데스크톱 앱입니다. 결과는 앱 화면에서 확인할 수 있습니다.

## 다운로드 및 설치

### Windows

[Windows 설치 파일 다운로드](https://github.com/jeus1998/excel-automation/releases/latest/download/Container-Workbench-Setup.exe)

1. `Container-Workbench-Setup.exe`를 내려받아 실행합니다.
2. 설치 안내에 따라 설치한 뒤 앱을 실행합니다.
3. **Python을 별도로 설치할 필요가 없습니다.**

앱 설치 파일은 현재 서명되지 않아 Windows SmartScreen 경고가 표시될 수 있습니다. GitHub의 이 저장소 Release에서 받은 파일인지 확인한 뒤 설치를 진행하세요.

### macOS

[Mac 설치 파일 다운로드](https://github.com/jeus1998/excel-automation/releases/latest/download/Container-Workbench-macOS.dmg)

DMG 파일을 열고 `Container Workbench.app`을 Applications 폴더로 옮긴 뒤 실행하세요. 앱 설치 파일은 현재 서명되지 않아 처음 실행할 때 macOS 보안 확인이 표시될 수 있습니다.

[모든 설치 파일 보기](https://github.com/jeus1998/excel-automation/releases/latest)

## 앱 사용 방법

1. 첫 화면에서 **금액 비교** 또는 **번호 대조**를 선택합니다.
2. 기준 파일과 비교 파일을 불러옵니다.
3. 각 파일의 시트를 고르고, 미리보기를 보며 헤더 행과 비교할 열을 선택합니다.
4. 금액 비교에서는 운송사와 금액 열도 선택합니다.
5. 설정을 확인한 뒤 비교를 시작하고, 결과 화면에서 상태별 결과를 확인합니다.

지원 파일 형식은 `.xlsx`, `.xlsm`, `.xls`입니다. 컨테이너 번호는 앞뒤 공백을 제거하고 대문자로 바꾼 뒤 영문 4자와 숫자 7자로 된 형식만 비교합니다. 내부 공백이나 하이픈이 포함된 번호는 결과에서 제외됩니다.
