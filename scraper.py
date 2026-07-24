import time
import urllib.parse
import pandas as pd
from playwright.sync_api import sync_playwright

def scrape_gmaps(city: str, sector: str):
    search_query = f"{city} {sector}"
    query_encoded = urllib.parse.quote(search_query)
    search_url = f"https://www.google.com/maps/search/{query_encoded}"
    results = []
    
    print(f"[+] '{search_query}' araması başlatılıyor...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="tr-TR")  # Türkçe sonuçlar için
        page = context.new_page()
        
        print("[+] Google Maps açılıyor...")
        page.goto(search_url, timeout=60000)
        
        # Çerez/kabul ekranı gelirse tıkla geç (Farklı dil ihtimalleri)
        try:
            page.locator("button", has_text="Tümünü kabul et").click(timeout=3000)
        except:
            pass
        try:
            page.locator("button", has_text="Kabul et").last.click(timeout=3000)
        except:
            pass
        try:
            page.locator("button", has_text="Accept all").click(timeout=3000)
        except:
            pass
            
        print("[+] Listeleme bekleniyor...")
        try:
            page.wait_for_selector('a[href*="https://www.google.com/maps/place/"]', timeout=20000)
        except Exception as e:
            print(f"[-] Arama sonucu bulunamadı veya sayfa yüklenemedi: {e}")
            browser.close()
            return
        
        print("[+] Liste aşağı kaydırılıyor (Maksimum 400 öğe için ayarlandı)...")
        previously_counted = 0
        scroll_attempts = 0
        
        while True:
            # Sayfanın biraz veri yüklemesini bekle
            page.wait_for_timeout(2000)
            
            # Kaydırma işlemi için feed elementini bul
            feed = page.locator('div[role="feed"]')
            if feed.count() > 0:
                feed.evaluate("el => el.scrollTop = el.scrollHeight")
            else:
                # Yedek kaydırma yöntemi
                elements = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
                if len(elements) > 0:
                    elements[-1].scroll_into_view_if_needed()
                    
            elements = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
            
            # Listenin sonuna indik mi kontrol et
            end_warning = page.locator("text=Listenin sonuna ulaştınız")
            if end_warning.count() > 0:
                break
                
            if len(elements) == previously_counted:
                scroll_attempts += 1
                page.wait_for_timeout(2000) # Bekleyip tekrar dene
                if scroll_attempts >= 3:
                    break
            else:
                scroll_attempts = 0
            
            previously_counted = len(elements)
            # En az 20 sayfa demek ortalama 400 sonuca denk gelir
            if previously_counted >= 400:
                break
        
        # Tüm linkleri topla
        print("[+] Linkler toplanıyor...")
        urls = page.eval_on_selector_all('a[href*="https://www.google.com/maps/place/"]', "elements => elements.map(e => e.href)")
        
        # Tekrarlayan URL'leri çıkart
        urls = list(dict.fromkeys(urls))
        print(f"[!] Toplam {len(urls)} adet yer bulundu. Veriler Çekiliyor...")
        
        # Her bir linke gidip detayları al
        for idx, url in enumerate(urls, 1):
            try:
                page.goto(url, timeout=30000)
                page.wait_for_selector("h1", timeout=10000)
                
                # İsim
                name_elem = page.locator("h1")
                name = name_elem.inner_text() if name_elem.count() > 0 else "Bilinmiyor"
                
                # Adres (Genellikle data-item-id="address" icindedir)
                address_elem = page.locator('button[data-item-id="address"]')
                address = address_elem.inner_text() if address_elem.count() > 0 else "Bilinmiyor"
                
                # Telefon (Genellikle data-item-id="phone:tel:..." icindedir)
                phone_elem = page.locator('button[data-item-id^="phone:tel:"]')
                phone = phone_elem.inner_text() if phone_elem.count() > 0 else "Bilinmiyor"
                
                # Website (Genellikle data-item-id="authority" icindedir)
                website_elem = page.locator('a[data-item-id="authority"]')
                website = website_elem.get_attribute("href") if website_elem.count() > 0 else "Bilinmiyor"
                
                # Temizlik yap
                clean_address = address.replace("Kopyala", "").replace("Adres :", "").strip()
                clean_phone = phone.replace("Numarayı kopyala", "").replace("Kopyala", "").strip()
                
                results.append({
                    "İsim": name.strip(),
                    "Adres": clean_address,
                    "Telefon": clean_phone,
                    "Web Sitesi": website.strip()
                })
                print(f"   [{idx}/{len(urls)}] Eklendi: {name.strip()}")
                
            except Exception as e:
                print(f"   [{idx}/{len(urls)}] Hata, atlanıyor. URL: {url}")
                continue
                
        browser.close()
        
    if results:
        df = pd.DataFrame(results)
        filename = f"{city}_{sector}_firmalar.xlsx".replace(" ", "_").lower()
        df.to_excel(filename, index=False)
        print(f"\n[Başarılı] İşlem tamamlandı! {len(results)} adet veri '{filename}' dosyasına kaydedildi.")
    else:
        print("\n[Hata] Hiç veri çekilemedi.")
