# CropLink - AI-Powered Agriculture Mobile App (Expo React Native)

Developed for **AgriSphere FairMarket / CropLink**.
Directly connected to the live Render backend: `https://agrisphere-backend-sv5x.onrender.com`

---

## ⚡ Key Highlights
1. **Background Instant Wake-Up:**
   - App ওপেন হওয়ার সাথে সাথেই ব্যাকগ্রাউন্ডে Render সার্ভারকে পিং (`GET /health`) করে জাগিয়ে তোলে।
   - ইউজার লগইন স্ক্রিনে ফোন নম্বর ও পাসওয়ার্ড টাইপ করতে করতে ৩০-৪০ সেকেন্ডের মধ্যে ব্যাকএন্ড সম্পূর্ণ রেডি ও অ্যাক্টিভ হয়ে যায়!
   - লাইভ সার্ভার স্ট্যাটাস পিল: 🟢 Server Active / 🟡 Waking up... / 🔴 Offline.

2. **Ultra-Premium Dark Neon UI:**
   - Sleek dark space background (`#070B14`), electric cyan & neon green glowing borders, glassmorphic cards, and modern typography.

3. **Bilingual (বাংলা & English) Switcher:**
   - হেডার থেকে যেকোনো সময় ১-ক্লিকে বাংলা ও ইংরেজি মোড পরিবর্তন করা যায়।
   - ব্যাকএন্ডের AI উত্তর, লাভ-ক্ষতির বিশ্লেষণ এবং নোটিফিকেশন স্বয়ংক্রিয়ভাবে নির্বাচিত ভাষায় আসে (`Accept-Language: bn / en`)।

4. **1-Click Demo Login:**
   - ডেমো অ্যাকাউন্ট দিয়ে তাৎক্ষণিক টেস্ট করার সুবিধা:
     - 🌾 **Farmer:** `01700000001` / `demo1234`
     - 🏢 **Buyer:** `01700000002` / `demo1234`

---

## 📱 How to Run on Your Phone with Expo Go

1. আপনার ফোনে Google Play Store থেকে **Expo Go** অ্যাপটি ইনস্টল করুন।
2. পিসির টার্মিনালে এই ফোল্ডারে যান:
   ```bash
   cd croplink-mobile
   npx expo start
   ```
3. টার্মিনালে একটি **QR Code** দেখতে পাবেন।
4. Expo Go অ্যাপ দিয়ে QR কোডটি স্ক্যান করলেই লাইভ অ্যাপটি আপনার ফোনে ওপেন হয়ে যাবে!

---

## 📦 How to Build Distributable Android APK

### Option A: EAS Cloud Build (সহজতম পদ্ধতি - কোনো Android Studio লাগে না)
1. টার্মিনালে EAS CLI ইনস্টল করুন:
   ```bash
   npm install -g eas-cli
   eas login
   ```
2. EAS কনফিগারেশন করুন:
   ```bash
   eas build:configure
   ```
3. সরাসরি APK ফাইল জেনারেট করুন:
   ```bash
   eas build --platform android --profile preview
   ```
   *বিল্ড শেষ হলে ক্লাউড থেকে সরাসরি ডাউনলোড করার লিঙ্ক ও APK পাওয়া যাবে।*

### Option B: Local Android Build
```bash
npx expo prebuild --platform android
cd android
./gradlew assembleRelease
```
APK ফাইলটি তৈরি হবে: `android/app/build/outputs/apk/release/app-release.apk`

---

## 🛠️ Implemented Features
- **Net-Profit Selling Decision Engine (`POST /decision/net-profit`):** ফসল এখনই বিক্রি করবেন না অপেক্ষা করবেন? পরিবহন, গুদাম, কমিশন ও পচনের ঝুঁকি বাদ দিয়ে নিট লাভের রেঞ্জ হিসাব।
- **Computer Vision Photo Grading (`POST /batches/from-photo`):** ক্যামেরা বা গ্যালারি থেকে ফসলের ছবি দিয়ে Grade A/B/C ও কনফিডেন্স স্কোর।
- **Digital QR Batch Passport (`GET /batches/{id}/passport`):** প্রতিটি লটের ট্যাম্পার-প্রুফ হ্যাশ ও কোয়ালিটি পাসপোর্ট।
- **Live Wholesale Prices & 7/14-Day ML Forecast (`GET /prices/today`, `GET /forecast`):** পাইকারি রেট এবং এআই প্রেডিকশন।
- **Cooperative Supply Pooling (`POST /pool/plan`):** একাধিক কৃষকের ফসল একত্রিত করে বড় পাইকারদের চাহিদা পূরণ ও সাশ্রয়ী লজিস্টিকস।
- **Bangla AI Chat & Negotiation Assistant (`POST /assistant/chat`, `POST /negotiation/counter-offer`):** বাংলায় কৃষি পরামর্শ এবং বায়ারের সাথে দর-কষাকষির জন্য তৈরি ড্রাফট বার্তা।
- **Orders & Delivery Quality Dispute Evidence (`GET /orders`, `GET /orders/{id}/evidence`):** সরবরাহকৃত মালের তুলনামূলক প্রমাণ ও নিরপেক্ষ মীমাংসা।
