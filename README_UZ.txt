BILYARD CLUB — KO'P AKKAUNTLI PWA

1) GitHub repository rootiga shu papkaning ICHIDAGI barcha fayl va papkalarni joylang.
2) Railway'da redeploy qiling.
3) Saytni ochib /register orqali email va parol bilan yangi akkaunt oching.
4) Ikkinchi telefon ham aynan shu akkaunt bilan kirsa, ma'lumotlar bir xil ko'rinadi.
5) Boshqa odam alohida ro'yxatdan o'tsa, uning stollari, mahsulotlari va hisobotlari alohida bo'ladi.
6) Stol qo'shish/o'chirish: Sozlamalar -> Stol qo'shish / Stolni o'chirish.

GOOGLE KIRISHI:
Google OAuth ishlashi uchun Railway Variables'da GOOGLE_CLIENT_ID va GOOGLE_CLIENT_SECRET berilishi kerak.
Google Cloud Console'da OAuth Web application yarating va Authorized redirect URI sifatida
https://SIZNING-RAILWAY-DOMENINGIZ/auth/google/callback
kiriting. Keyin shu Client ID va Client Secret'ni Railway Variables'ga kiriting.

XAVFSIZLIK:
Railway Variables'da uzoq tasodifiy SECRET_KEY kiriting.
Doimiy ma'lumot saqlanishi uchun Railway persistent volume yoki PostgreSQL/SQLite uchun doimiy disk kerak.
Bir nechta akkaunt bir serverdan foydalanadi, lekin ma'lumotlar user_id bilan ajratiladi.
