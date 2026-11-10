# 👗 Kiyim AI — Virtual Try-On & Fit Detection Ilovasi

"Kiyim AI" — sun'iy intellekt va kompyuter ko'rish (Computer Vision) texnologiyalari yordamida kiyimni virtual kiyib ko'rish (Virtual Try-On), tana o'lchamlarini tahlil qilish (Size & Fit Detection) va kiyish tarixini boshqarish uchun mo'ljallangan to'liq tizim.

---

## 📁 Loyiha Strukturasi

```
/home/xurshid/kiyim-ai/
├── run.sh                       # 🚀 Ilovani 1 ta buyruq bilan ishga tushirish skripti
├── app.py                       # ⚡ Asosiy Server (Flask + REST API + Static Server)
├── kiyim_ai.db                  # 🗄️ SQLite ma'lumotlar bazasi (Tarix, Garderob, Profil)
│
├── services/                    # 🧠 AI va Biznes-mantiq
│   ├── db.py                    # Ma'lumotlar bazasi operatsiyalari
│   ├── fit_engine.py            # Tana o'lchami va moslik tahlili (OpenCV / MediaPipe)
│   └── tryon_engine.py          # Kiyimni foydalanuvchiga kiydirish (Virtual Try-On)
│
├── static/                      # 🎨 Statik resurslar
│   ├── css/style.css            # Mobil dizayn uslublari
│   ├── js/app.js                # Mobil ilova mijoz mantiqi (Kamera, Yuklash, AI so'rovi)
│   ├── uploads/                 # Yuklangan va generatsiya qilingan rasmlar
│   └── garments/                # Kiyimlar rasmlari (Katalog)
│
├── templates/
│   └── index.html               # 📱 Native-uslubdagi zamonaviy Mobil UI (PWA)
│
└── mobile/                      # 📲 React Native (Expo) Mobil Ilova Kodi
    ├── package.json
    ├── App.tsx
    └── src/
        ├── components/FitScoreGauge.tsx
        ├── screens/TryOnScreen.tsx
        ├── screens/HistoryScreen.tsx
        ├── screens/ProfileScreen.tsx
        └── services/api.ts
```

---

## ⚡ 1. Ilovani Hoziroq Ishga Tushirish

Terminalda quyidagi buyruqni bering:

```bash
cd /home/xurshid/kiyim-ai
./run.sh
```

Yoki to'g'ridan-to'g'ri Python orqali:
```bash
/home/xurshid/venv/bin/python3 /home/xurshid/kiyim-ai/app.py
```

### Brauzerda ochish:
- Kompyuter brauzerida: [http://localhost:5000](http://localhost:5000)
- Telefon orqali bir xil Wi-Fi tarmog'ida: `http://<KOMPYUTER_IP>:5000` (ekranda chiqadi)

---

## ✨ 2. Ilovaning Asosiy Imkoniyatlari

1. **Virtual Try-On (Kiyib ko'rish):**
   - O'z rasmingizni yuklang yoki kameradan suratga oling.
   - Katalogdan xohlagan kiyimni tanlang yoki yangi kiyim suratini yuklang.
   - O'lchamni tanlang (`XS`, `S`, `M`, `L`, `XL`, `XXL`).
   - "Virtual Kiyib Ko'rish" tugmasini bosing — AI kiyimni sizga kiyintirib beradi.

2. **Size & Fit Detection (Moslik va Tavsiya):**
   - AI tanangizning yelka va ko'krak kengligini tahlil qiladi.
   - Moslik foizini hisoblaydi (masalan: `96.5%`).
   - Kiyim qomatingizga qanday tushishini aniqlaydi:
     - 🟢 **Ideal Moslik (Perfect)**
     - 🔴 **Biroz Tor (Tight)**
     - 🟡 **Katta / Oversized (Loose)**
   - Shaxsiy maslahat va tavsiya etilgan o'lchamni matn shaklida beradi.

3. **Jonli Kamera (Live Video):**
   - Brauzer yoki telefon kamerangizdan real-vaqt rejimida qomatingizni ko'rib turib suratga olish.

4. **Kiyimlar Garderobi (Wardrobe Catalog):**
   - Mavjud kiyimlar ro'yxati.
   - Kameradan kiyimni skanerlab yangi kiyim qo'shish.

5. **Tarix va Xotira (History):**
   - Oldin kiyib ko'rilgan barcha natijalar saqlanadi.
   - Har bir natijani birma-bir o'chirish (`X` tugmasi) yoki butunlay tozalash ("Tozalash" tugmasi).

---

## 📲 3. React Native (Expo) Ilovasi haqida

`mobile/` papkasida React Native (Expo) uchun to'liq TypeScript kodi tayyorlangan:
- Agar kompyuteringizga Node.js o'rnatilsa, `cd mobile && npm install && npx expo start` orqali iOS va Android qurilmalarga build qilib olishingiz mumkin.
- Hozir esa `app.py` orqali to'laqonli mobil veb-ilova (PWA) sifatida telefoningizda ham, kompyuteringizda ham darhol foydalanishingiz mumkin!
