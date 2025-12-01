import sys
import os
import platform
import time
import pandas as pd
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# =================================================================
# [핵심] OS별 브라우저 설치 경로 자동 설정 (맥북 호환성 해결)
# =================================================================
def get_browser_path():
    """OS에 따라 안전한 브라우저 설치 경로를 반환합니다."""
    system_os = platform.system()
    
    if system_os == 'Darwin':  # Mac OS
        # 맥북은 앱 내부가 아닌, 사용자 라이브러리 폴더('Application Support')에 저장해야 안전함
        user_home = os.path.expanduser("~")
        base_path = os.path.join(user_home, "Library", "Application Support", "SmartStoreScraper")
    else:  # Windows / Linux
        # 윈도우는 실행 파일(exe)이 있는 폴더에 'browsers' 폴더 생성
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

    # 최종 브라우저 폴더 경로
    browser_folder = os.path.join(base_path, "browsers")
    
    # 폴더가 없으면 생성 (권한 에러 방지)
    try:
        os.makedirs(browser_folder, exist_ok=True)
    except Exception as e:
        print(f"❌ 폴더 생성 실패: {e}")
        
    return browser_folder

# 환경 변수 강제 지정 (Playwright가 이 경로를 바라보게 함)
BROWSER_FOLDER = get_browser_path()
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_FOLDER

# =================================================================
# [기능] 사람처럼 스크롤 내리기 (지연 로딩 데이터 수집용)
# =================================================================
def smooth_scroll(target_frame, steps=10, delay=0.2):
    """페이지를 조금씩 아래로 스크롤하여 이미지와 리뷰를 로딩시킴"""
    try:
        for _ in range(steps):
            target_frame.evaluate("window.scrollBy(0, 800)")
            time.sleep(delay)
    except Exception:
        pass

# =================================================================
# [GUI] 메인 화면 클래스
# =================================================================
class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 스마트스토어 리뷰 수집기 (Mac/Win 호환)")
        self.root.geometry("600x550")
        self.root.resizable(False, False)

        # 스타일 설정
        style = ttk.Style()
        style.configure("TLabel", font=("Malgun Gothic", 10))
        style.configure("TButton", font=("Malgun Gothic", 10, "bold"))

        # 1. 입력 프레임
        input_frame = ttk.LabelFrame(root, text="수집 설정", padding=(10, 10))
        input_frame.pack(fill="x", padx=10, pady=10)

        # URL 입력
        ttk.Label(input_frame, text="상품 URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        # 페이지 수 입력
        ttk.Label(input_frame, text="수집 페이지 수:").grid(row=1, column=0, sticky="w", pady=5)
        self.limit_entry = ttk.Entry(input_frame, width=10)
        self.limit_entry.insert(0, "13") 
        self.limit_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # 시작 버튼
        self.start_btn = ttk.Button(input_frame, text="수집 시작", command=self.start_thread)
        self.start_btn.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        # 2. 로그 프레임
        log_frame = ttk.LabelFrame(root, text="진행 상황", padding=(10, 10))
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        # 초기 안내 메시지
        self.log("프로그램이 준비되었습니다.")
        self.log(f"📂 브라우저 저장 경로: {BROWSER_FOLDER}")
        self.log("👉 URL을 입력하고 [수집 시작]을 누르세요.")

    def log(self, message):
        """로그 창에 텍스트 출력"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def start_thread(self):
        """버튼 클릭 시 작업 쓰레드 시작"""
        url = self.url_entry.get().strip()
        limit = self.limit_entry.get().strip()

        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요!")
            return
        if not limit.isdigit():
            messagebox.showwarning("경고", "페이지 수는 숫자만 입력해주세요!")
            return

        self.start_btn.config(state="disabled") # 버튼 잠금
        self.log("\n[작업 시작] --------------------------------")
        
        # UI 멈춤 방지를 위해 별도 쓰레드에서 실행
        t = threading.Thread(target=self.run_scraper, args=(url, int(limit)))
        t.daemon = True
        t.start()

    def run_scraper(self, url, limit_pages):
        try:
            # 브라우저 설치 확인
            self.install_browser_if_needed()
            
            # 크롤링 시작
            extract_reviews_to_csv(self, url, limit_pages)
            
            messagebox.showinfo("완료", "수집이 완료되었습니다!\nreviews.csv 파일을 확인하세요.")
        except Exception as e:
            self.log(f"❌ 에러 발생: {e}")
            messagebox.showerror("에러", f"오류가 발생했습니다.\n{e}")
        finally:
            self.start_btn.config(state="normal") # 버튼 잠금 해제

    def install_browser_if_needed(self):
        self.log("⚙️ 브라우저 엔진 상태 확인 중...")
        try:
            # 설치된 브라우저가 있는지 테스트
            with sync_playwright() as p:
                p.chromium.launch(headless=True).close()
            self.log("✅ 브라우저 엔진 정상.")
        except Exception:
            self.log("🚀 브라우저 엔진이 없습니다. 자동 설치를 시작합니다...")
            self.log("   (약 1~2분 소요됩니다. 끄지 말고 기다려주세요!)")
            try:
                from playwright.__main__ import main
                old_argv = sys.argv
                sys.argv = ["playwright", "install", "chromium"]
                try:
                    main()
                except SystemExit:
                    pass
                finally:
                    sys.argv = old_argv
                self.log("✅ 브라우저 설치 완료!")
            except Exception as e:
                self.log(f"❌ 설치 실패: {e}")
                raise e


# =================================================================
# [로직] 웹 스크래핑 함수들
# =================================================================

def parse_review_card(card):
    """HTML 요소에서 리뷰 데이터 추출"""
    nickname_el = card.select_one(".Db9Dtnf7gY strong")
    nickname = nickname_el.get_text(strip=True) if nickname_el else ""

    date_el = card.select_one(".Db9Dtnf7gY span:nth-of-type(1)")
    date = date_el.get_text(strip=True) if date_el else ""

    rating_el = card.select_one("em.n6zq2yy0KA")
    rating = rating_el.get_text(strip=True) if rating_el else ""

    option = ""
    option_box = card.select_one(".b_caIle8kC")
    if option_box:
        all_texts = list(option_box.stripped_strings)
        option = all_texts[0] if all_texts else ""

    buyer_el = card.select_one(".eWRrdDdSzW")
    buyer_info = buyer_el.get_text(" ", strip=True) if buyer_el else ""
    label_el = card.select_one(".h8uqAeqIe7")
    label_info = label_el.get_text(" ", strip=True) if label_el else ""
    auto_label = " | ".join(x for x in [buyer_info, label_info] if x)

    content = ""
    content_box = card.select_one(".KqJ8Qqw082")
    if content_box:
        spans = content_box.select("span")
        if len(spans) >= 2:
            tags = [s.get_text(strip=True) for s in spans[:-1]]
            body = spans[-1].get_text(" ", strip=True)
            content = " ".join(tags + [body])
        elif len(spans) == 1:
            content = spans[0].get_text(" ", strip=True)

    image_count = 0
    img_box = card.select_one(".s30AvhHfb0")
    if img_box:
        count_span = img_box.select_one(".lOzR1kO8jf")
        if count_span:
            number = "".join(c for c in count_span.get_text(strip=True) if c.isdigit())
            if number:
                image_count = int(number)
        else:
            imgs = img_box.select("img")
            if len(imgs) >= 1:
                image_count = 1

    return {
        "nickname": nickname,
        "date": date,
        "rating": rating,
        "option": option,
        "auto_label": auto_label,
        "content": content,
        "image_count": image_count,
    }

def load_review_frame(gui, page):
    """리뷰 탭을 찾아서 클릭하고 iframe 로딩 대기"""
    gui.log("🔎 리뷰탭 탐색 중…")
    
    # 탭 찾기 및 클릭
    for _ in range(40):
        btn = page.locator('[data-name="REVIEW"]').first
        if btn.is_visible():
            btn.scroll_into_view_if_needed()
            time.sleep(0.5)
            btn.click()
            gui.log("✔ 리뷰탭 클릭 성공")
            break
        page.mouse.wheel(0, 600)
        time.sleep(0.2)
    else:
        gui.log("❌ 리뷰탭 못 찾음. (기본 페이지에서 계속 탐색)")
        return page

    gui.log("⌛ 리뷰 iframe 로딩 대기…")
    for _ in range(80):
        for f in page.frames:
            lower = f.url.lower()
            if ("review" in lower) or ("reviews" in lower) or ("pstatic" in lower):
                gui.log(f"✔ iframe 감지됨")
                return f
        time.sleep(0.25)
    return page

def load_next_page(gui, target_frame, current_page_num):
    """다음 페이지 버튼 클릭"""
    next_page_num = current_page_num + 1
    next_btn = target_frame.locator(f'.LiT9lKOVbw a:has-text("{next_page_num}")').first

    if next_btn.count() > 0:
        gui.log(f"➡ 페이지 {next_page_num} 이동")
        next_btn.click()
        time.sleep(2) # 페이지 로딩 대기
        return True
    else:
        return False

def extract_reviews_to_csv(gui, url, limit_pages=13):
    """전체 리뷰 수집 프로세스"""
    reviews = []
    seen = set()

    with sync_playwright() as p:
        # headless=False: 사용자가 보는 앞에서 브라우저가 움직임
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        gui.log(f"⏳ 페이지 접속 중: {url}")
        
        try:
            page.goto(url, timeout=60000)
        except Exception:
            gui.log("⚠️ 접속 시간이 오래 걸리거나 타임아웃 되었습니다. 계속 시도합니다.")

        time.sleep(3)

        target_frame = load_review_frame(gui, page)
        
        # iframe 로드 실패 확인
        if target_frame is page and target_frame.url == url and page.locator(".IwcuBUIAKf").count() == 0:
            gui.log("❌ 리뷰 섹션을 찾을 수 없습니다.")
            browser.close()
            return
            
        for n in range(1, limit_pages + 1):
            gui.log(f"📌 페이지 {n} 수집 중…")
            
            # [중요] 스크롤을 내려서 지연 로딩된 데이터(이미지, 텍스트) 활성화
            gui.log("   (스크롤 내리는 중...)")
            smooth_scroll(target_frame, steps=10, delay=0.2)

            soup = BeautifulSoup(target_frame.content(), "lxml")
            review_cards = soup.select(".IwcuBUIAKf")
            
            current_page_reviews = 0
            for card in review_cards:
                info = parse_review_card(card)
                if not info: continue
                
                # 중복 방지 키 생성
                key = f"{info['nickname']}|{info['date']}|{info['content'][:10]}"
                if key not in seen:
                    seen.add(key)
                    reviews.append(info)
                    current_page_reviews += 1

            gui.log(f"   └ 신규: {current_page_reviews}건 (누적: {len(reviews)}건)")
            
            # 다음 페이지 이동
            if not load_next_page(gui, target_frame, n):
                gui.log("⛔ 다음 페이지 없음")
                break

        browser.close()

    # CSV 저장
    df = pd.DataFrame(reviews)
    df.to_csv("reviews.csv", index=False, encoding="utf-8-sig")
    gui.log("====================================")
    gui.log(f"✅ 총 {len(reviews)}건 수집 완료")
    gui.log("📁 reviews.csv 저장됨")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()
