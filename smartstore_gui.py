import sys
import os

# =================================================================
# [경로 고정] exe 실행 시 브라우저 설치 경로를 'browsers' 폴더로 지정
# =================================================================
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

browser_folder = os.path.join(base_path, "browsers")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_folder
# =================================================================

import time
import pandas as pd
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ============================================================
# [NEW] 사람처럼 스크롤 내리는 함수 (API 코드에서 가져옴)
# ============================================================
def smooth_scroll(target_frame, steps=10, delay=0.3):
    """
    페이지 끝까지 천천히 스크롤을 내려서
    지연 로딩(Lazy Loading)된 이미지와 리뷰 텍스트를 활성화함
    """
    try:
        for _ in range(steps):
            # 800픽셀씩 아래로 스크롤
            target_frame.evaluate("window.scrollBy(0, 800)")
            time.sleep(delay)
    except Exception:
        pass

# ============================================================
# GUI 클래스
# ============================================================
class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 스마트스토어 리뷰 수집기 (개선판)")
        self.root.geometry("600x550")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.configure("TLabel", font=("Malgun Gothic", 10))
        style.configure("TButton", font=("Malgun Gothic", 10, "bold"))

        # 입력 프레임
        input_frame = ttk.LabelFrame(root, text="수집 설정", padding=(10, 10))
        input_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(input_frame, text="상품 URL:").grid(row=0, column=0, sticky="w", pady=5)
        self.url_entry = ttk.Entry(input_frame, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="수집 페이지 수:").grid(row=1, column=0, sticky="w", pady=5)
        self.limit_entry = ttk.Entry(input_frame, width=10)
        self.limit_entry.insert(0, "13") 
        self.limit_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.start_btn = ttk.Button(input_frame, text="수집 시작", command=self.start_thread)
        self.start_btn.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        # 로그 프레임
        log_frame = ttk.LabelFrame(root, text="진행 상황", padding=(10, 10))
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='disabled', font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        self.log("프로그램이 준비되었습니다.")
        self.log(f"브라우저 저장 위치: {browser_folder}")
        self.log("URL을 입력하고 시작을 누르세요.")

    def log(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def start_thread(self):
        url = self.url_entry.get().strip()
        limit = self.limit_entry.get().strip()

        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요!")
            return
        if not limit.isdigit():
            messagebox.showwarning("경고", "페이지 수는 숫자만 입력해주세요!")
            return

        self.start_btn.config(state="disabled")
        self.log("\n[작업 시작] --------------------------------")
        
        t = threading.Thread(target=self.run_scraper, args=(url, int(limit)))
        t.daemon = True
        t.start()

    def run_scraper(self, url, limit_pages):
        try:
            self.install_browser_if_needed()
            # 클래스 함수가 아닌 외부 함수 호출 시 self(gui)를 전달
            extract_reviews_to_csv(self, url, limit_pages)
            messagebox.showinfo("완료", "수집이 완료되었습니다!\nreviews.csv 파일을 확인하세요.")
        except Exception as e:
            self.log(f"❌ 에러 발생: {e}")
            messagebox.showerror("에러", f"오류가 발생했습니다.\n{e}")
        finally:
            self.start_btn.config(state="normal")

    def install_browser_if_needed(self):
        self.log("⚙️ 브라우저 엔진 상태 확인 중...")
        try:
            with sync_playwright() as p:
                p.chromium.launch(headless=True).close()
            self.log("✅ 브라우저 엔진 정상.")
        except Exception:
            self.log("🚀 브라우저 엔진 설치 시작 (1~2분 소요)...")
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


# ============================================================
# 스크래핑 로직 (parse, load_frame, extract)
# ============================================================

def parse_review_card(card):
    # 기존 코드와 100% 동일
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
    gui.log("🔎 리뷰탭 탐색 중…")
    
    # [수정] 스크롤을 좀 더 적극적으로 하며 찾기
    for _ in range(40):
        btn = page.locator('[data-name="REVIEW"]').first
        if btn.is_visible():
            btn.scroll_into_view_if_needed()
            # 클릭 전 약간 대기
            time.sleep(0.5)
            btn.click()
            gui.log("✔ 리뷰탭 클릭 성공")
            break
        page.mouse.wheel(0, 600)
        time.sleep(0.2)
    else:
        gui.log("❌ 리뷰탭 못 찾음. (기본 페이지 탐색)")
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
    next_page_num = current_page_num + 1
    next_btn = target_frame.locator(f'.LiT9lKOVbw a:has-text("{next_page_num}")').first

    if next_btn.count() > 0:
        gui.log(f"➡ 페이지 {next_page_num} 이동")
        next_btn.click()
        time.sleep(2) # 이동 후 기본 대기
        return True
    else:
        return False

def extract_reviews_to_csv(gui, url, limit_pages=13):
    reviews = []
    seen = set()

    with sync_playwright() as p:
        # headless=False: 사용자가 보는 앞에서 브라우저가 움직임
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        gui.log(f"⏳ 페이지 접속 중: {url}")
        page.goto(url, timeout=60000)
        time.sleep(3)

        target_frame = load_review_frame(gui, page)
        
        if target_frame is page and target_frame.url == url and page.locator(".IwcuBUIAKf").count() == 0:
            gui.log("❌ 리뷰 섹션 로드 실패 또는 리뷰 없음.")
            browser.close()
            return
            
        for n in range(1, limit_pages + 1):
            gui.log(f"📌 페이지 {n} 수집 중…")
            
            # [핵심] 페이지 로드 후, 스크롤을 훑어서 데이터 로딩 (API 로직 적용)
            gui.log("   (스크롤 내리는 중...)")
            smooth_scroll(target_frame, steps=10, delay=0.2)

            soup = BeautifulSoup(target_frame.content(), "lxml")
            review_cards = soup.select(".IwcuBUIAKf")
            
            current_page_reviews = 0
            for card in review_cards:
                info = parse_review_card(card)
                if not info: continue
                
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

    df = pd.DataFrame(reviews)
    df.to_csv("reviews.csv", index=False, encoding="utf-8-sig")
    gui.log("====================================")
    gui.log(f"✅ 총 {len(reviews)}건 수집 완료")
    gui.log("📁 reviews.csv 저장됨")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()