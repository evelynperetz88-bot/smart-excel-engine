# Smart Excel Engine — v4 (Commercial Premium)

מוצר לחיצה-אחת להפקת דוחות מקצועיים מאקסל. בנוי לעבוד גם כשימוש אישי וגם כמוצר מסחרי שאנשים משלמים עליו.

> 🚀 **התפיסה**: גרור קובץ → לחץ "הפק דוח מושלם" → קבל PDF מקצועי תוך 2 שניות. אין הגדרות, אין החלטות.

## למה זה מוצר ולא רק כלי

- **One-Click Smart Export** — כפתור ענק יחיד שעושה הכול. אין עוד 7 צעדים, אין עוד תבטות.
- **Smart Detection** — מזהה אוטומטית: דוח כספי / משפטי / מלאי / כללי, עם אחוז ביטחון.
- **Onboarding** — בהפעלה ראשונה: כרטיס מודרך עם 3 צעדים. אחרי לחיצה ראשונה — מוסתר לעד.
- **Success Panel** — אחרי כל יצירת דוח: באדג' "Professional Output" + הסבר ספציפי לסוג הדוח.
- **Output Modes** — Draft / Official / Court-ready. כל מצב טוען קונפיגורציה שלמה (watermark, PDF/A, header style).
- **PDF/A תקני אמיתי** — דרך Ghostscript post-processing (לא רק metadata). אם gs לא מותקן — fallback ברור עם הסבר למשתמש.
- **Trust Indicators** — checklist קבוע של תקני המוצר: הדפסה מקצועית, עברית מלאה, פיצול חכם, פרטיות, PDF/A.
- **Upgrade Prompt** — אחרי כל יצירה ב-Free: כרטיס שדרוג מוצק עם 5 פיצ'רים מובהקים.

## הזרימה ב-v4

```
[Onboarding (פעם אחת)] → [Drag & Drop קובץ]
    → [🚀 הפק דוח מושלם — 2 שניות]
    → [Detection Badge: "זוהה כדוח משפטי · ביטחון 100%"]
    → [📄 PDF Preview אמיתי ב-iframe]
    → [Output Mode: Draft / Official / Court-ready]
    → [✔ Success Panel + Professional Output Badge]
    → [Trust Indicators]
    → [⭐ Upgrade Prompt (Free) או "Pro פעיל" (Pro)]
    → [התאמה ידנית — collapsed לחלוטין כברירת מחדל]
```

## פיצ'רים חדשים ב-v4

| יכולת | טכני | UX |
|-------|------|----|
| **PDF/A אמיתי** | [services/pdfa.py](backend/services/pdfa.py) — מנסה `gswin64c` → `gs`. רץ עם `-dPDFA=1 -sPDFACompatibilityPolicy=1 -dCompatibilityLevel=1.4` | סטטוס מוחזר ב-headers: `X-PDFA-Status: verified|best_effort|failed`. UI מציג ✔/⚠/✗ |
| **Output Mode** | enum `draft|official|court_ready` ב-`AutoExportRequest`. `output_mode_defaults()` מפעיל preset שלם | 3 כרטיסים גדולים בכותרת ה-AutoExportPanel; Pro-only מסומן בתג זהב |
| **Onboarding** | localStorage key `sxe.onboarding.dismissed.v1` | כרטיס gradient כחול בהפעלה ראשונה — 3 צעדים + "הבנתי, בואו נתחיל" |
| **Success Panel** | מציג אחרי `generatedOnce && !working` | gradient ירוק + "Professional Output" badge + הסברים ספציפיים לסוג הדוח |
| **Upgrade Prompt** | localStorage key `sxe.upgrade_dismissed.v1`. נעלם בלחיצה. חוזר אם משתמש חוזר ל-Free | כרטיס gradient זהב עם 5 פיצ'רים מובהקים + CTA זהב מאיר |
| **Trust Indicators** | בודק `/api/capabilities` כדי לדעת אם gs מותקן | רשימת ✓/⚠ של 5 תקנים, צבע ירוק/כתום לפי סטטוס |
| **PDF/A Status Toast** | `X-PDFA-Message` (URL-encoded) | toast עם הודעה ברורה למשתמש: "המסמך עומד בתקן PDF/A-1b" / "best-effort בלבד" |
| **Branding** | `app.title = "Smart Excel Engine"` | watermark Free = "Smart Excel Engine" (forced); כותרת `<title>` של ה-PDF |

## התקנת Ghostscript (לתמיכת PDF/A מלאה)

על Windows:
```
1. הורידו את Ghostscript: https://ghostscript.com/releases/gsdnld.html
2. התקינו (gswin64c.exe ייווצר אוטומטית).
3. וודאו שהוא ב-PATH או ב-C:\Program Files\gs\<ver>\bin\
4. רעננו את השרת: GET /api/capabilities → "pdfa_real": true
```

ה-UI יציג אוטומטית: "✔ Ghostscript מותקן — PDF/A תקני זמין"

ללא Ghostscript — המערכת ממשיכה לעבוד, ה-PDF נוצר עם metadata best-effort, וה-UI מציג "⚠ Ghostscript לא מותקן".

## API חדש ב-v4

| Method | Path | חדש? | תיאור |
|--------|------|------|-------|
| GET    | `/api/health`            | 🔄 | מחזיר גם `pdfa_available` |
| GET    | `/api/capabilities`      | 🆕 | `{ocr, pdfa_real}` — UI משתמש כדי להציג Trust Indicators |
| POST   | `/api/auto/plan`         | 🔄 | מחזיר גם `capabilities.pdfa_available` |
| POST   | `/api/auto/preview/pdf`  | 🔄 | headers: `X-PDFA-Requested`, `X-PDFA-Available` |
| POST   | `/api/auto/export/pdf`   | 🔄 | מבצע PDF/A דרך Ghostscript אם זמין; headers: `X-PDFA-Status`, `X-PDFA-Message` |

ב-payload של `AutoExportRequest`:
```json
{
  "file_id": "...",
  "tier": "pro",
  "output_mode": "court_ready",
  "watermark": {"preset": "official"},
  "pdf_a": true
}
```

## Output Modes — מטריצה

| מצב | Free | Pro | Watermark | PDF/A | Header |
|-----|------|-----|-----------|-------|--------|
| **Draft** | ✅ | ✅ | "טיוטה" / "DRAFT" | ❌ | standard |
| **Official** | ❌ | ✅ | ללא | ✅ אמיתי | standard |
| **Court-ready** | ❌ | ✅ | ללא | ✅ אמיתי | formal |

ב-Free, המערכת מאלצת `output_mode=draft` ומוסיפה Watermark "Smart Excel Engine".

## בדיקות (12+12 = 24 בדיקות, כולן עוברות)

**Library smoke test (12/12)**:
```
[1] Sample built [2] Sheet detection [3] Extraction [4] Filters
[5a] Single layout [5b] Split layout [6/6b] PDF render [7] DOCX
[8] 5 templates [9] Detection: legal/100% [10] Watermark+PDF/A markers
[11] Ghostscript graceful degrade [12] Output mode mapping
```

**HTTP smoke test (12/12)**:
```
[health v4.0.0] [templates] [upload] [preview/data] [preview/pdf]
[export/pdf] [export/word] [auto/plan: legal] [auto/preview/pdf]
[auto/preview/pdf pro+pdfa] [auto/export/pdf: X-PDFA-Status=best_effort]
[court_ready] [draft+free imprints watermark] [capabilities]
```

## מבנה תיקיות (v4)

```
backend/
├── app.py                          # /api/health, /api/capabilities
├── routers/
│   ├── auto.py                     # 🔄 + _apply_output_mode() + _maybe_pdfa() + headers
│   ├── export.py
│   ├── files.py
│   └── templates.py
├── services/
│   ├── pdfa.py                     # 🆕 Ghostscript post-processing + locator + status
│   ├── auto_export.py
│   ├── detector.py
│   ├── analyzer.py
│   ├── layout_engine.py
│   ├── pdf_renderer.py
│   ├── word_renderer.py
│   ├── filters.py
│   ├── templates.py
│   ├── cleanup.py
│   └── ocr.py
├── models/schemas.py               # 🔄 + OutputMode enum + output_mode_defaults()
├── builtin_templates/              # 5 templates: financial, legal, inventory, general, clean
└── packaging/

frontend/
├── src/
│   ├── App.jsx                     # 🔄 + onboarding, output mode, capabilities, upgrade flow
│   ├── api.js                      # 🔄 + fetchCapabilities, X-PDFA-* headers
│   ├── components/
│   │   ├── OnboardingHint.jsx      # 🆕 First-time user card
│   │   ├── OutputMode.jsx          # 🆕 3-card segmented control
│   │   ├── SuccessPanel.jsx        # 🆕 Post-generation success state
│   │   ├── UpgradePrompt.jsx       # 🆕 Pro CTA card
│   │   ├── TrustIndicators.jsx     # 🆕 Standards checklist
│   │   ├── AutoExportPanel.jsx     # 🔄 + integrates SuccessPanel + Upgrade + OutputMode
│   │   ├── WatermarkPanel.jsx
│   │   ├── TierToggle.jsx
│   │   ├── LangSwitcher.jsx
│   │   └── (manual-mode components)
│   ├── i18n/{he,en}.json           # 🔄 +50 strings (onboarding, output_mode, success, trust, upgrade, pdfa)
│   └── styles.css                  # 🔄 + .onboarding-card, .output-mode-grid, .success-panel, .upgrade-card, .trust-indicators
```

## הפעלה

```powershell
# Backend
cd C:\Users\Mitchashvim\ExcelConverter\backend
.\.venv\Scripts\Activate.ps1
python app.py            # http://127.0.0.1:8765

# Frontend (עם HMR — שינויים נטענים אוטומטית)
cd C:\Users\Mitchashvim\ExcelConverter\frontend
npm run dev              # http://localhost:5174
```

## Pro vs Free — מטריצת מכירה

| יכולת | Free | Pro |
|------|------|-----|
| Smart Detection + Auto-Export | ✅ | ✅ |
| כל התבניות המובנות | ✅ | ✅ |
| Smart Layout Engine | ✅ | ✅ |
| תצוגה מקדימה PDF אמיתית | ✅ | ✅ |
| Watermark "Smart Excel Engine" | תמיד (forced) | ניתן לכבות |
| Output Mode Draft | ✅ | ✅ |
| Output Mode Official | ❌ | ✅ |
| Output Mode Court-ready | ❌ | ✅ |
| Watermark מותאם / "טיוטה" / "רשמי" | ❌ | ✅ |
| בקרת opacity + color | ❌ | ✅ |
| **PDF/A תקני אמיתי (Ghostscript)** | ❌ | ✅ |
| OCR מ-PDF סרוק | ❌ | ✅ |
| תבניות משתמש (localStorage) | עד 3 | ∞ |

המעבר Free → Pro היום מתבצע ב-localStorage. למוצר SaaS אמיתי הוסיפו `routers/auth.py` עם JWT, והעבירו את `_enforce_tier` ל-FastAPI dependency שמזהה user → tier מ-DB.

## מה הופך את זה למוצר מסחרי

1. **Trust** — UI מציג בבירור את התקנים שהמערכת עומדת בהם, כולל "✔ Ghostscript מותקן — PDF/A תקני זמין".
2. **First impression** — מסך הראשי ריק כמעט: רק upload, וכפתור גדול. אין overwhelm.
3. **Confidence** — באדג' זיהוי ("זוהה כדוח משפטי · ביטחון 100%") נותן למשתמש ביטחון שהמערכת "הבינה" אותו.
4. **Success state** — אחרי לחיצה אחת, המשתמש מקבל אישור ויזואלי מובהק שהדבר באמת עבד.
5. **Upgrade nudge** — Free תמיד יודע מה הוא מקבל ב-Pro, אבל לא בצורה מטרידה (יש כפתור dismiss קבוע).
6. **Court-ready mode** — מסר ברור ללקוח: "המוצר הזה יכול להפיק לך מסמכים שאפשר להגיש לבית משפט".
7. **One-Click מסיים** — אין שלב התקנה, אין שלב טוטוריאל. גם משתמש שלא יודע מה זה עמודת priority יקבל פלט מקצועי.

## הצעד הבא לקראת SaaS

1. Auth (JWT/OAuth2) → `routers/auth.py`
2. SQLAlchemy עם טבלאות: `users`, `subscriptions`, `usage_events`, `templates`
3. החלפת tier מ-localStorage לטעינה מ-`Depends(current_user)`
4. Stripe webhook → upgrade event מעדכן `subscriptions.tier`
5. Quota — middleware על `routers/auto.py` סופר ייצואים בחודש לכל user
6. S3 storage backend (כבר interface-clean)
7. Cloudflare/CDN ל-static assets
