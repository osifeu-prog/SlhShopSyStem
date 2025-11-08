
# SLH Shop Core - Deploy Pack (Prototype)

תשתית ליבה מבוססת חנויות (Shop-First) עבור האקוסיסטם של SLH/SELA/NIFTII.

כרגע החבילה הזו כוללת:

- `api/`
  - `main.py` – FastAPI עם מודלים של User/Shop/Item/Order + endpoints בסיסיים
  - `requirements.txt` – חבילות Python הנדרשות

הכל רץ **in-memory** (ללא DB) לצורך בדיקות מהירות וחיבור עתידי לבוט טלגרם ול-WebApp.

---

## 1. מה החבילה הזאת עושה כרגע

- מספקת API קטן שמאפשר:
  - יצירת/סנכרון משתמש מטלגרם (`POST /users/telegram-sync`)
  - יצירת חנות למשתמש (`POST /shops`)
  - יצירת כרטיסים/מוצרים לחנות (`POST /shops/{shop_id}/items`)
  - יצירת הזמנות (`POST /orders`)
- כל המידע נשמר בזיכרון בלבד ונעלם כשעוצרים את השרת – זה **Prototype** למודל עסקי/דאטה.

זהו שלב **1A** במפת הדרכים הכוללת:

1. **שלב 1A – Core Prototype (in-memory)** ← אתה נמצא כאן
2. שלב 1B – חיבור ל-DB (Postgres / SQLite)
3. שלב 2 – חיבור בוט טלגרם ל-API
4. שלב 3 – Web Wallet / Mini App
5. שלב 4 – פריסה מלאה ל-Railway + Mainnet + ניהול חנויות/כרטיסים/Referrals

---

## 2. איך מפעילים את ה-API מקומית (שלב אחרי שלב)

### 2.1. חילוץ הקובץ למחשב

1. הורד את קובץ ה-ZIP שקיבלת מהצ'אט.
2. חלץ אותו לתיקייה נוחה, למשל:
   - `D:\SLH_SHOP_CORE` (רצוי בלי רווחים בעברית בשם הנתיב).

אחרי החילוץ תראה מבנה כזה:

```text
D:\SLH_SHOP_CORE
└── api
    ├── main.py
    └── requirements.txt
```

### 2.2. פתיחת PowerShell בתיקיית הפרויקט

1. פתח PowerShell.
2. הרץ:

```powershell
cd "D:\SLH_SHOP_CORE\api"
```

ודא שאתה נמצא בתיקיית `api` (בדוק את ה-Prompt שלך).

### 2.3. יצירת venv והתקנת חבילות

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

אם הכל תקין – לא אמורות להופיע שגיאות.

### 2.4. הרצת השרת

```powershell
uvicorn main:app --reload --port 8080
```

עכשיו ה-API מאזין בכתובת:

- `http://127.0.0.1:8080`
- דף דוקומנטציה אוטומטי: `http://127.0.0.1:8080/docs`

### 2.5. בדיקות ראשוניות

בחלון PowerShell אחר (או ב-Postman / דפדפן):

```powershell
Invoke-RestMethod http://127.0.0.1:8080/healthz
Invoke-RestMethod http://127.0.0.1:8080/meta
```

אתה אמור לקבל משהו כמו:

```json
{ "ok": true }
```

ו-`/meta` יראה את המידע על המערכת (שם, גרסה, chain_id וכו').

---

## 3. איך זה מתחבר למפת הדרכים שלנו

### סטטוס נוכחי (בזמן שאתה קורא README זה)

- ✅ הגדרת ישויות בסיסיות: User, Shop, Item, Order.
- ✅ יצירת API Prototype in-memory.
- ⏳ עדיין אין DB אמיתי (Postgres).
- ⏳ עדיין אין חיבור לבוט טלגרם.
- ⏳ עדיין אין Web Wallet.

### היעד הבא (כשזה רץ אצלך מקומית)

1. לוודא שאתה מצליח להריץ את הפקודות:
   - `uvicorn main:app --reload --port 8080`
   - לגשת ל-`/docs` ולשחק עם:
     - `POST /users/telegram-sync`
     - `POST /shops`
     - `POST /shops/{shop_id}/items`
     - `POST /orders`

2. אחרי שזה עובד אצלך חלק – נתקדם לשלב הבא:
   - להוסיף תמיכה ב-DB אמיתי (למשל SQLite מקומית ו-Postgres ב-Railway).
   - ליצור חיבור נקי לבוט טלגרם שיקרא ל-API הזה.

---

## 4. מה להגיד לעוזר (ChatGPT) אחרי שסיימת את השלב הזה

כשתראה שה-API עולה בהצלחה ושיחקת קצת עם `/docs`, כתוב לעוזר:

> "הרצתי את SLH Shop Core API מקומית והוא עובד.  
> עכשיו בוא נוסיף DB (עדיף SQLite/Postgres) ונכין חיבור נקי לבוט טלגרם עבור /start ו-/start shop_XXXX."

משם נמשיך לבנות יחד את שאר השכבות (DB → Bot → WebApp → Railway).
