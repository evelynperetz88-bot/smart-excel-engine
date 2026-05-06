# Deployment — Frontend (Vercel) + Backend (Render)

מדריך פריסה צעד-אחר-צעד למערכת חיה ב-Production.

> ⏱ זמן ביצוע משוער: **15 דקות**.

---

## שלב 0 — push ל-GitHub (פעם אחת)

```powershell
cd C:\Users\Mitchashvim\ExcelConverter
git add .
git commit -m "Initial commit: Smart Excel Engine v4 ready for deploy"
# צור repo חדש ב-https://github.com/new (private או public — לא משנה)
# העתק את ה-URL שגיתהאב נותן (e.g. https://github.com/USER/smart-excel-engine.git)
git remote add origin https://github.com/USER/smart-excel-engine.git
git push -u origin main
```

---

## שלב 1 — Backend ב-Render (5 דקות)

1. **render.com → New + → Blueprint**
2. **Connect GitHub** → בחר את ה-repo שיצרת
3. Render יזהה אוטומטית את [render.yaml](render.yaml) ויציע לך service:
   - Name: `smart-excel-engine`
   - Plan: `Free`
   - Region: `Oregon`
4. **Apply** → Render יבנה את ה-Docker image (~2-3 דקות לבנייה ראשונה).
5. אחרי `Live`, סמן את ה-URL — יראה משהו כמו:
   ```
   https://smart-excel-engine.onrender.com
   ```
6. **בדיקה ראשונית**:
   ```powershell
   curl https://smart-excel-engine.onrender.com/api/health
   ```
   צריך לקבל:
   ```json
   {"ok":true,"version":"4.0.0","ocr_available":false,"pdfa_available":true,"storage_dir":"/tmp/sxe-storage"}
   ```
   חשוב: `pdfa_available: true` (Ghostscript מותקן ב-Docker image).

---

## שלב 2 — Frontend ב-Vercel (5 דקות)

1. **vercel.com → Add New → Project → Import Git Repository**
2. בחר את אותו ה-repo שיצרת ב-GitHub
3. **Framework Preset**: ייזהה אוטומטית כ-`Vite`
4. **Root Directory**: `frontend`
5. **Build Command** + **Output Directory** — להשאיר ברירת מחדל (קורא מ-[frontend/vercel.json](frontend/vercel.json))
6. **Environment Variables** — הוסף משתנה אחד:
   - Name: `VITE_API_BASE`
   - Value: `https://smart-excel-engine.onrender.com` (ה-URL מ-Render — בלי `/api` בסוף)
   - Environments: `Production`, `Preview`, `Development`
7. **Deploy** → Vercel יבנה ויעלה (~1 דקה)
8. אחרי `Ready`, תקבל URL:
   ```
   https://smart-excel-engine.vercel.app
   ```

---

## שלב 3 — סגירת CORS (קריטי לאבטחה)

עד עכשיו ה-backend פתוח ל-`*`. אחרי שיש לך URL מ-Vercel:

1. **Render → smart-excel-engine → Environment**
2. ערוך את `CORS_ORIGINS`:
   ```
   https://smart-excel-engine.vercel.app
   ```
   (אם יש שני URLs — production + preview — הפרד בפסיק)
3. Render יעלה service חדש אוטומטית.

---

## שלב 4 — בדיקות סופיות (Live)

עבור ל-`https://smart-excel-engine.vercel.app` ובדוק:

| ✓ | בדיקה |
|---|-------|
| ☐ | Onboarding card נטען בהפעלה ראשונה |
| ☐ | העלאת קובץ Excel — אין CORS errors ב-DevTools console |
| ☐ | "🚀 הפק דוח מושלם" עובד ומציג iframe של PDF |
| ☐ | Detection badge מציג סוג + ביטחון |
| ☐ | "הורד PDF" — מתחיל הורדה |
| ☐ | Watermark מופיע ב-PDF (Free tier) |
| ☐ | החלפת שפה he ↔ en עובדת ומחליפה את כיוון הדף |
| ☐ | Trust Indicators מציג "✔ Ghostscript מותקן" |
| ☐ | Pro toggle → Output Mode "Court-ready" → Download → PDF includes "PDF/A" string |

---

## הערות חשובות

### Render Free Tier — Cold start
- שירות חינמי **נרדם אחרי 15 דקות** של חוסר פעילות.
- בקריאה ראשונה אחרי שינה — תהיה השהייה של ~30 שניות.
- ב-DEMO ללקוח: **חמם את השרת מראש** עם `curl /api/health` 30 שניות לפני הפגישה.
- לתשלום $7/חודש (Render Starter) — אין שינה.

### Storage
- ב-free tier, `STORAGE_DIR=/tmp/sxe-storage` — קבצים נמחקים ברסטארט (ובכל deploy חדש).
- זה לא בעיה לזרימה הרגילה (upload→export בתוך אותו session), אבל אם משתמש לוקח הפסקה ארוכה — הוא יצטרך להעלות מחדש.
- לפתרון מלא: שדרוג ל-Render Starter + הסרת ההערה מהבלוק `disk:` ב-[render.yaml](render.yaml).

### OCR
- DocImageKit (`dik`) הוא Windows-only. בענן Render (Linux) — OCR לא זמין.
- ה-UI יציג: "OCR לא זמין — DocImageKit לא נמצא ב-PATH"
- זה לא breakage — קבצי Excel עובדים רגיל; רק העלאת PDF סרוק לא תעבוד.
- לתמיכה ב-OCR ב-Linux: שדרוג עתידי דרך Tesseract — `apt-get install tesseract-ocr tesseract-ocr-heb` ב-Dockerfile.

### Auto-deploy
- כל `git push origin main` → Render + Vercel יבנו אוטומטית.
- Vercel: PR נפתח → preview URL.
- Render: רק main מתעדכן.

---

## פתרון בעיות נפוצות

**CORS error בדפדפן**
> Access to fetch at 'https://...onrender.com/api/...' from origin 'https://...vercel.app' has been blocked by CORS policy

תיקון: ב-Render → Environment → `CORS_ORIGINS` חייב להכיל את ה-URL המדויק של Vercel (כולל https, בלי slash בסוף).

**`pdfa_available: false`**
- הריץ הריצה ראשונה? וודא שהשרת `Live` ושגלית את ה-Dockerfile עם `apt-get install ghostscript`.
- בדוק לוגים ב-Render: `Deploy → Logs`.

**הקובץ נטען אבל הייצוא נכשל**
- בדוק את לוגי הbackend ב-Render. סביר שכשל בגלל timeout (free tier limit).
- פתרון: הפחת את `row_limit` או שדרג ל-Starter.

**שינויים ב-CORS לא נכנסים לתוקף**
- Render דורש redeploy אחרי שינוי env var. בדוק שיש "Deploy succeeded" אחרי ה-edit.

---

## טאסקים אופציונליים

### דומיין מותאם
- Vercel: Settings → Domains → Add → `app.your-domain.com`
- Render: Settings → Custom Domain → `api.your-domain.com`
- עדכן את `CORS_ORIGINS` ו-`VITE_API_BASE` בהתאם.

### ניטור
- Render: לוגים מובנים, alerts על errors
- Vercel: Web Analytics + Speed Insights (חינם עד מגבלה)
- Sentry/Datadog לניטור שגיאות עומק

### CI/CD
- Render auto-deploys מ-main.
- אפשר להוסיף GitHub Action שמריץ `python smoke_test.py` לפני merge.
