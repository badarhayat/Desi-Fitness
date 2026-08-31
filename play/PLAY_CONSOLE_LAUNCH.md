# Launch Desi Fitness on Google Play

This is the first-app path for **Muhammad Badar Hayat** (`yasmeenaziz016@gmail.com`, Play developer account `8157582832429796630`).

The Android app is a native wrapper around the live Desi Fitness site:
`https://badarniazi.pythonanywhere.com`

Package name (do not change after the first upload): `com.desifitness.app`

## 1. Deploy this website update first

Play review will open your privacy policy URL. That page must already be live.

On PythonAnywhere, pull this branch (or merge it to `master` and pull), then **Reload** the web app.

Confirm these URLs open without logging in:

- https://badarniazi.pythonanywhere.com/privacy
- https://badarniazi.pythonanywhere.com/terms
- https://badarniazi.pythonanywhere.com/support

## 2. Create the app in Play Console

1. Open [Google Play Console](https://play.google.com/console) and sign in as Muhammad Badar Hayat.
2. Finish identity verification if Play still shows it as incomplete.
3. Click **Create app**.
4. Fill:
   - App name: `Desi Fitness`
   - Default language: English (United States) — you can add Urdu later
   - App or game: **App**
   - Free or paid: **Free**
   - Declarations: accept Play policies and US export laws

## 3. Store listing copy (paste these)

**Short description (max 80 characters):**

```
Track desi meals, calories, weight and fasting in Urdu.
```

**Full description:**

```
Desi Fitness helps you track everyday Pakistani and desi meals, calories, weight, steps, and fasting in one place.

Log dishes such as biryani, karahi, qeema, daal chawal, and your own home recipes. See estimated calories, protein, carbs, and fat. Switch the app between Roman Urdu and Urdu (اردو).

What you can do:
• Analyze desi dishes and save custom recipes
• Track daily calories, protein, weight, and steps
• Set a calorie target and watch progress
• Log fasting sessions
• Use the app in Roman Urdu or Urdu

Desi Fitness is a personal tracker. It is not medical advice and does not diagnose or treat any condition.

Developer: Muhammad Badar Hayat
Support: yasmeenaziz016@gmail.com
Privacy: https://badarniazi.pythonanywhere.com/privacy
```

**Graphics** (already generated in `play/assets/`):

- App icon: `play/assets/icon_512.png` (512 × 512)
- Feature graphic: `play/assets/feature_graphic_1024x500.png` (1024 × 500)
- Phone screenshots: capture at least 2 screens from a phone (login, dashboard, meals, track). Play requires 16:9 or 9:16 JPEG/PNG.

**Category:** Health & Fitness  
**Tags:** nutrition, calorie counter, fasting, urdu  
**Contact email:** yasmeenaziz016@gmail.com  
**Privacy policy URL:** https://badarniazi.pythonanywhere.com/privacy

## 4. App content declarations

Use these answers unless you later add ads, payments, or extra data collection.

| Question | Answer |
| --- | --- |
| Ads | No |
| In-app purchases / subscriptions | No |
| News app | No |
| COVID-19 contact tracing | No |
| Data safety: does the app collect data? | Yes |
| Data collected | Personal info (name, user IDs), Health info (weight, height, nutrition, fasting) that the user types in |
| Data shared with other companies | No |
| Encrypted in transit | Yes (HTTPS) |
| Users can request deletion | Yes, by emailing yasmeenaziz016@gmail.com |
| Advertising ID | No |
| Target audience | 18 and over (fitness tracker; not for children) |
| Store presence | This app is not primarily appealing to children |
| Health | Fitness/nutrition tracking only; not a medical device; no clinical claims |
| Government apps | No |
| Financial features | No |

Content rating questionnaire: select **Utility, Productivity, Communication, or Other**. No violence, no user-generated public chat, no location sharing.

## 5. Build the Android App Bundle (.aab)

You need Java 17+ and Android Studio (or the Android SDK) on your computer.

```bash
cd android
chmod +x create-upload-keystore.sh gradlew
./create-upload-keystore.sh
./gradlew bundleRelease
```

The signed bundle is:

`android/app/build/outputs/bundle/release/app-release.aab`

Keep `android/desifitness-upload.jks` and `android/keystore.properties` **off GitHub** and backed up. If you lose the upload key, updating the app on Play becomes much harder.

To install a test copy on your own phone:

```bash
cd android
./gradlew assembleDebug
```

Then copy `android/app/build/outputs/apk/debug/app-debug.apk` to the phone. The debug package id is `com.desifitness.app.debug` (different from the Play Store app).

## 6. Closed testing (required for your first production release)

Personal Play accounts created after 13 November 2023 cannot go straight to production.

1. In Play Console go to **Test and release → Testing → Closed testing**.
2. Create a closed test (default track is enough).
3. Upload `app-release.aab`, name the release `1.0.0`, and roll it out to the closed track.
4. Turn on **Play App Signing** when asked (accept Google’s signing key).
5. Add at least **12 testers** by Gmail address (family and friends with Android phones).
6. Each tester must tap the opt-in link, install from Play, and stay opted in.
7. Keep 12 testers opted in for **14 continuous days**.
8. Then click **Apply for production** on the Dashboard and answer the questionnaire.

Until those 14 days finish, the app will only be visible to your testers, not the whole Play Store.

## 7. Countries and pricing

- Pricing: Free
- Start with Pakistan, then add other countries if you want
- No ads and no in-app products for version 1.0.0

## 8. After Play approves testers

When 14-day testing is done and production access is granted:

1. Create a **Production** release with the same `.aab` (or a newer versionCode).
2. Review the Publishing overview checklist until every item is green.
3. Send for review.

Later website-only improvements on PythonAnywhere appear in the Android app automatically. You only need a new Play upload when you change the Android wrapper (icon, package, permissions, or the website URL).

## 9. Version numbers

| Field | First release |
| --- | --- |
| versionName | 1.0.0 |
| versionCode | 1 |
| applicationId | com.desifitness.app |
| targetSdk | 36 (Android 16, required for new apps from 31 August 2026) |
| minSdk | 24 (Android 7) |
