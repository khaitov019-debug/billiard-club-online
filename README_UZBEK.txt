BILLIARD CLUB ONLINE — DEPLOYMENT

Render uchun:
1. Shu papkani GitHub repo qiling.
2. Render -> New -> Web Service -> GitHub repo ni tanlang.
3. Runtime: Python 3
4. Build Command: pip install -r requirements.txt
5. Start Command: gunicorn app:app
6. Environment Variables: SECRET_KEY = uzun tasodifiy maxfiy kalit
7. Deploy.

Saytning asosiy manzili internet orqali ochiladi.
Google uchun / sahifa ochiq va SEO meta ma'lumotlari qo'shilgan.
Boshqaruv paneli /dashboard va /login orqali himoyalangan.

MUHIM: Hozirgi dastur SQLite ishlatadi. Render free servisida doimiy biznes ma'lumotlari uchun keyin PostgreSQL yoki persistent disk ulash kerak.
