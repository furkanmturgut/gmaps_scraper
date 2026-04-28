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
        
        print("[+] Liste aşağı kaydırılıyor (Maksimum 50 öğe için ayarlandı)...")
        previously_counted = 0
        while True:
            # Sayfanın biraz veri yüklemesini bekle
            page.wait_for_timeout(2000)
            
            elements = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
            
            if len(elements) > 0:
                # Son elemana gidip aşağı kaydırmasını sağla
                elements[-1].scroll_into_view_if_needed()
                
            # Listenin sonuna indik mi kontrol et, veya eleman sayısı değişmedi mi
            end_warning = page.locator("text=Listenin sonuna ulaştınız")
            if end_warning.count() > 0 or len(elements) == previously_counted:
                page.wait_for_timeout(3000) # Son bir yüklenme şansı
                new_elements = page.locator('a[href*="https://www.google.com/maps/place/"]').all()
                if len(new_elements) == previously_counted:
                    break
            
            previously_counted = len(elements)
            # Kısa sürmesi için ilk 50 sonucu alacağız, istenirse burası arttırılabilir.
            if previously_counted >= 50:
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
