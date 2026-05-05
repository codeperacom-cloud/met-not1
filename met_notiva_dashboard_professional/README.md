# Notiva Dashboard Professional

Flask tabanli Notiva/Logo ERP dashboard uygulamasinin daha duzenli, guvenli ve bakimi kolay hale getirilmis surumudur.

## Ozellikler

- App factory mimarisi
- Blueprint bazli modul ayrimi
- `.env` tabanli gizli bilgi yonetimi
- Ortak veritabani baglanti katmani
- Login korumasi ve hash destekli sifre kontrolu
- Firma/donem whitelist dogrulamasi
- Standart JSON API cevaplari
- Ayrilmis template/static yapisi

## Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` dosyasindaki SQL Server, kullanici, sifre ve `SECRET_KEY` degerlerini doldurun.

## Calistirma

```powershell
python run.py
```

Uygulama varsayilan olarak `http://127.0.0.1:5000` adresinde acilir.

## Production Notu

Development icin `python run.py` yeterlidir. Production icin debug kapali calistirin ve `waitress` gibi bir WSGI sunucusu kullanin.

```powershell
waitress-serve --listen=0.0.0.0:5000 "app:create_app()"
```
