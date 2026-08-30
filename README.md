# 🛡️ TRONGL — Bezpečnostní Chodecká Navigace & AI Asistent

**TRONGL** je moderní navigační systém navržený speciálně pro chodce. Na rozdíl od běžných navigací optimalizuje trasy nejen podle vzdálenosti a času, ale především podle **bezpečnostního skóre** (osvětlení, historická a komunitní data o incidentech, denní/noční doba).

---

## 🚀 Hlavní Funkce

* **🛡️ Bezpečnostní Routing:** Výpočet nejbezpečnější trasy vs. nejrychlejší trasy na základě geografických dat (PostGIS).
* **⚠️ Komunitní Hlášení:** Možnost okamžitě nahlásit neosvětlený úsek, rušení klidu nebo nebezpečí přímo z mobilní aplikace.
* **🤖 AI Bezpečnostní Asistent:** Inteligentní vyhodnocení rizik na trase, které uživateli přirozenou řečí vysvětlí, na co si dát pozor.
* **🐳 Dockerized Architecture:** Snadné spuštění celé infrastruktury (backend + databáze) jedním příkazem.

---

## 🛠️ Tech Stack

### **Backend**
* **Python 3.11** & **FastAPI** — Bleskové REST API.
* **PostgreSQL + PostGIS** — Prostorová databáze pro výpočty vzdáleností a geofencing incidentů.
* **SQLAlchemy & GeoAlchemy2** — ORM pro práci s geodata.

### **Frontend**
* **React Native (Expo)** — Cross-platform mobilní aplikace (Android / iOS).
* **React Native Maps** — Interaktivní mapa s vykreslováním tras a bodů zájmu.

### **Infrastruktura**
* **Docker & Docker Compose** — Kontajnerizace backendu a databáze.

---

## 📂 Struktura Projektu

```text
trongl-app/
├── backend/
│   ├── src/
│   │   ├── main.py           # Hlavní FastAPI aplikace (endpoints)
│   │   ├── assistant.py      # Logika AI bezpečnostního asistenta
│   │   ├── database.py       # Připojení k PostgreSQL / PostGIS
│   │   ├── models.py         # Databázové modely
│   │   └── schemas.py        # Pydantic schémata
│   ├── Dockerfile            # Konfigurace Dockeru pro backend
│   └── requirements.txt      # Python závislosti
├── frontend/
│   ├── App.js                # Hlavní mobilní obrazovka v React Native
│   └── package.json          # Node.js závislosti aplikace
└── docker-compose.yml        # Orchestrace služeb (DB + API)
