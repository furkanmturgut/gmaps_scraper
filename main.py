from scraper import scrape_gmaps

def main():
    print("="*40)
    print("   Google Maps İl/Sektör Botu   ")
    print("="*40)
    print("Çıkmak için CTRL+C yapabilirsiniz.\n")
    
    city = input("Hangi İl/İlçe? (Örn: Kadıköy): ").strip()
    sector = input("Hangi Sektör? (Örn: Kahveci): ").strip()
    
    if not city or not sector:
        print("İl ve sektör alanı boş bırakılamaz.")
        return
        
    scrape_gmaps(city, sector)

if __name__ == "__main__":
    main()
