# smartstore_review_api.py
import logging
import json
import asyncio
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("scraper")

app = FastAPI()

# CORS 설정: Vercel 등 외부 접근 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Playwright 관련 함수
# ---------------------------------------------------------
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def launch_browser(p) -> Browser:
    # 로컬이니까 headless=False로 해서 브라우저 뜨는 거 구경해도 됨 (속도는 True가 빠름)
    return await p.chromium.launch(
        headless=True, 
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            f"--user-agent={UA}"
        ]
    )

def normalize_cookie(c: dict) -> dict:
    raw_same = str(c.get("sameSite", "None")).lower()
    same_site = "None"
    if raw_same == "lax": same_site = "Lax"
    elif raw_same == "strict": same_site = "Strict"
    
    return {
        "name": c["name"],
        "value": c["value"],
        "domain": c["domain"],
        "path": c.get("path", "/"),
        "expires": c.get("expires", 0),
        "httpOnly": c.get("httpOnly", False),
        "secure": c.get("secure", True),
        "sameSite": same_site,
    }

async def create_page(browser: Browser, cookie_data: dict) -> Page:
    context = await browser.new_context(
        locale="ko-KR",
        user_agent=UA,
        viewport={"width": 1920, "height": 1080}
    )
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    if cookie_data and "cookies" in cookie_data:
        try:
            clean_cookies = [normalize_cookie(c) for c in cookie_data["cookies"]]
            await context.add_cookies(clean_cookies)
        except Exception as e:
            logger.error(f"쿠키 로드 실패: {e}")

    return await context.new_page()

def parse_review_card(card):
    try:
        nickname = card.select_one(".Db9Dtnf7gY strong").get_text(strip=True)
    except: nickname = "익명"

    try: date = card.select_one(".Db9Dtnf7gY span:nth-of-type(1)").get_text(strip=True)
    except: date = ""

    try: rating = int(card.select_one("em.n6zq2yy0KA").get_text(strip=True))
    except: rating = 5

    content = ""
    try:
        content_box = card.select_one(".KqJ8Qqw082")
        if content_box:
            spans = content_box.select("span")
            if len(spans) >= 2: content = spans[-1].get_text(" ", strip=True)
            elif len(spans) == 1: content = spans[0].get_text(" ", strip=True)
    except: pass

    return {"user": nickname, "date": date, "rating": rating, "content": content}

async def load_review_frame(page: Page):
    try:
        btn = page.locator("[data-name='REVIEW']").first
        if await btn.is_visible():
            await btn.click()
            await page.wait_for_timeout(2000)
    except: pass
    
    for _ in range(30):
        for frame in page.frames:
            if "review" in frame.url.lower(): return frame
        await page.wait_for_timeout(500)
    return page

async def scrape_reviews(url: str, limit_pages: int, cookie_data: dict):
    async with async_playwright() as p:
        browser = await launch_browser(p)
        page = await create_page(browser, cookie_data)

        try:
            await page.goto(url, timeout=90000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # 차단 체크
            if "서비스 접속이 불가합니다" in await page.content():
                raise HTTPException(503, "네이버가 접속을 차단했습니다.")

            iframe = await load_review_frame(page)
            results = []
            seen = set()

            for n in range(1, limit_pages + 1):
                await iframe.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(1000)

                soup = BeautifulSoup(await iframe.content(), "lxml")
                cards = soup.select(".IwcuBUIAKf")
                
                if not cards: break

                for card in cards:
                    info = parse_review_card(card)
                    if info:
                        key = f"{info['user']}|{info['content'][:15]}"
                        if key not in seen:
                            seen.add(key)
                            results.append(info)
                
                # 다음 페이지
                try:
                    next_btn = iframe.locator(f"a.U7Lsd_y9Gg:has-text('{n+1}')").first
                    if await next_btn.count() > 0:
                        await next_btn.click()
                        await page.wait_for_timeout(2000)
                    else: break
                except: break
            
            return results
        finally:
            await browser.close()

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.post("/scrape")
async def scrape_endpoint(
    url: str = Form(...),
    limit_pages: int = Form(3),
    cookie_file: Optional[UploadFile] = File(None)
):
    cookie_data = {}
    if cookie_file:
        content = await cookie_file.read()
        try: cookie_data = json.loads(content)
        except: pass

    try:
        data = await scrape_reviews(url, limit_pages, cookie_data)
        return {"status": "success", "count": len(data), "reviews": data}
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(500, f"Scraping Failed: {str(e)}")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Yonghwa's Local Scraper Ready"}