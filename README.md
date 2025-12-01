🛍️ 네이버 스마트스토어 리뷰 수집기 (GUI Version)

네이버 스마트스토어 URL을 입력하면 리뷰 데이터를 자동으로 수집하여 reviews.csv 파일로 저장해 주는 프로그램입니다.

Windows와 Mac(macOS) 환경을 모두 지원하며, 복잡한 설치 없이 더블 클릭으로 실행할 수 있도록 GUI(윈도우 창)를 제공합니다.

✨ 주요 기능

GUI 인터페이스: 터미널 명령어를 몰라도 입력창을 통해 쉽게 사용 가능

지연 로딩 완벽 지원: 자동으로 스크롤을 내려 숨겨진 리뷰까지 모두 수집

Mac/Win 호환: OS에 맞춰 브라우저 설치 경로와 파일 저장 경로 자동 최적화

자동 브라우저 설치: 실행 시 크롬 브라우저가 없으면 자동으로 감지하여 설치

편의 기능: Mac 환경에서의 복사/붙여넣기(Command+V) 및 우클릭 메뉴 지원

🛠️ 개발 환경 설정 (For Developer)

1. 필수 라이브러리 설치

파이썬 가상환경(venv)에서 다음 패키지들을 설치해야 합니다.

Bash



pip install pandas beautifulsoup4 lxml playwright pyinstaller

playwright install chromium

2. 소스 코드 실행

Bash



python smartstore_gui.py

📦 실행 파일 빌드 방법 (Build)

소스를 수정했거나 배포용 실행 파일(.exe / .app)을 만들 때 사용합니다.

Playwright 브라우저 엔진 의존성을 포함하기 위해 아래 명령어를 반드시 그대로 입력해야 합니다.

🪟 Windows (.exe 만들기)

터미널(Git Bash 또는 CMD)에서 다음 명령어를 실행합니다.

Bash



pyinstaller --onefile --noconsole --name smartstore_scraper_gui --collect-all playwright smartstore_gui.py

빌드가 완료되면 dist 폴더 안에 smartstore_scraper_gui.exe 파일이 생성됩니다.

🍎 Mac (GitHub Actions 권장)

Mac 환경에서도 위 명령어로 빌드가 가능하지만, GitHub Actions를 사용하여 클라우드에서 빌드하는 것을 권장합니다. (Windows PC에서는 Mac용 앱을 빌드할 수 없습니다.)

📖 사용자 가이드 (For User)

🪟 Windows 사용자

smartstore_scraper_gui.exe 파일을 실행합니다.

상품 URL과 수집할 페이지 수를 입력합니다.

[수집 시작] 버튼을 누릅니다.

최초 실행 시 브라우저 설치로 인해 1~2분 정도 멈춘 것처럼 보일 수 있습니다.

완료되면 프로그램이 있는 폴더(또는 다운로드 폴더)에 reviews.csv가 생성됩니다.

🍎 Mac 사용자 (필독!)

Mac 보안 정책으로 인해 다음 단계를 반드시 지켜야 합니다.

앱 이동: 다운로드 받은 앱 압축을 푼 뒤, [응용 프로그램(Applications)] 폴더로 드래그해서 옮깁니다. (다운로드 폴더에서 실행 시 에러 발생)

첫 실행: 앱 아이콘에 **우클릭(또는 Control+클릭) > [열기]**를 선택합니다. 팝업창에서 **[열기]**를 눌러야 보안 경고를 통과할 수 있습니다.

결과 확인: 수집된 reviews.csv 파일은 [다운로드] 폴더에 저장됩니다.

⚠️ Mac 문제 해결 (Troubleshooting)

"앱이 손상되었기 때문에 열 수 없습니다"라고 뜰 때:

터미널(Terminal)을 열고 다음 명령어를 입력하세요.

Bash



xattr -cr /Applications/SmartStoreScraper.app

붙여넣기(Command+V)가 안 될 때:

입력창에 마우스 우클릭을 하면 [붙여넣기] 메뉴가 나옵니다.

📝 라이선스 및 주의사항

이 프로그램은 학습 및 개인적인 목적으로 제작되었습니다.

과도한 요청(페이지 수 과다 설정 등)은 네이버에 의해 차단될 수 있으니 적절한 딜레이와 페이지 수를 유지하세요.
