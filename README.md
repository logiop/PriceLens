# PriceLens — Competitive Pricing Intelligence

**PriceLens** è un'app di *pricing intelligence* end-to-end: un clone **migliorato** di
[Minderest](https://www.minderest.com/it/), costruito seguendo la metodologia
[REA](https://github.com/morluto/rea) ("*vedi una feature → capisci come funziona →
ricostruiscila meglio per il tuo progetto*").

Monitora prezzi, promozioni, catalogo e disponibilità dei competitor su retailer e
marketplace, e non si limita a mostrare dati: **suggerisce il prezzo da applicare**.

> ⚠️ **Nota di trasparenza.** REA serve per analizzare software di cui hai diritto di
> accesso. Minderest è un SaaS commerciale chiuso dietro login, quindi questa app è stata
> ricostruita partendo dalle feature **documentate pubblicamente** (monitoraggio prezzi,
> storico, compliance MAP/MSRP, repricing dinamico, dashboard), non dal suo codice
> proprietario. Le fonti live sono supportate ma disattivate di default (simulazione).

> 📄 **Guida completa:** [`docs/GUIDA-PriceLens.pdf`](docs/GUIDA-PriceLens.pdf) — 17 pagine
> su architettura, modello dati, repricing, alert, API e deploy.

---

## Cosa fa (e cosa ha in più rispetto a Minderest)

| Area | Funzionalità |
| --- | --- |
| **Multi-utente** | Registrazione/login con JWT (PBKDF2 + token firmati), dati isolati per account. |
| **Monitoraggio** | Catalogo prodotti (SKU, costo, prezzo, MSRP, MAP), competitor multipli, storico prezzi. |
| **Analisi** | Min/max/medio dei competitor, **posizione** (1° = più economico) e **indice di competitività 0–100**. |
| **Repricing** | Motore con 4 strategie (`allinea al minimo`, `sottoquotazione`, `margine protetto`, `premium`), floor di margine e ceiling MSRP, applicazione one-click. |
| **Alert** | Violazioni **MAP**, cali/rialzi prezzo, esaurimento/rientro stock, con severità critico/avviso/info. |
| **Scheduler** | Raccolta prezzi automatica in background ogni N secondi (configurabile). |
| **Export** | Esportazione **CSV** e **Excel (.xlsx)** di prodotti, alert e storico. |
| **Fonti dati** | Sorgenti **simulate** (out-of-the-box) o **URL live** (JSON-LD / CSS selector / regex configurabili). |
| **Dashboard** | KPI, distribuzione indice di competitività, top movers, feed alert. |

Migliorie rispetto a Minderest: repricing **azionabile** (non solo osservazione),
posizionamento numerico per prodotto, alert MAP immediati, export e multi-utenza integrati,
e zero lock-in — self-hosted, open source, FastAPI + React/TypeScript.

---

## Avvio rapido

Requisiti: Python ≥ 3.11, Node.js ≥ 20, npm.

```bash
# 1. Setup una tantum (venv + dipendenze backend e frontend)
make setup

# 2. Build del frontend e avvio in produzione (un solo server su :8000)
make serve
# → apri http://127.0.0.1:8000

# Oppure, in sviluppo (backend :8000 + Vite :5173 con hot reload):
make backend    # terminale 1
make frontend   # terminale 2
# → apri http://localhost:5173
```

### Credenziali demo

Al primo avvio il database viene popolato con dati demo:

```
Email:    demo@pricelens.it
Password: demo1234
```

12 prodotti, 6 competitor, 60 giorni di storico prezzi e alert realistici.

> ⚠️ **iCloud Drive.** Se il progetto vive dentro una cartella sincronizzata con
> iCloud Drive (es. `~/Documents`), macOS può "scaricare" i file del virtualenv su iCloud e
> rendere l'installazione lentissima o bloccata. Metti il progetto (o almeno il `.venv` e
> `node_modules`) fuori da iCloud, oppure crea il venv altrove:
> `python3 -m venv /tmp/pricelens-venv && /tmp/pricelens-venv/bin/pip install -r backend/requirements.txt`.

Per ricominciare da zero: elimina `backend/pricelens.db` e riavvia.

---

## Autenticazione

- `POST /api/auth/register` — crea account, restituisce JWT.
- `POST /api/auth/login` — autentica, restituisce JWT.
- `GET /api/auth/me` — profilo dell'utente corrente.

Ogni endpoint applicativo richiede l'header `Authorization: Bearer <token>`.
Le password sono hashatte con **PBKDF2-HMAC-SHA256** (600.000 iterazioni, salt per utente)
e i token sono **JWT HS256** con scadenza configurabile (`PRICELENS_TOKEN_EXPIRE_MINUTES`).

Variabili d'ambiente principali:

| Variabile | Default | Descrizione |
| --- | --- | --- |
| `PRICELENS_DATABASE_URL` | `sqlite:///./pricelens.db` | URL database (SQLite o SQLAlchemy). |
| `PRICELENS_SECRET_KEY` | random | Chiave firma JWT (impostala in produzione). |
| `PRICELENS_TOKEN_EXPIRE_MINUTES` | `10080` | Durata token (7 giorni). |
| `PRICELENS_COLLECT_INTERVAL_SECONDS` | `300` | Intervallo raccolta automatica. |
| `PRICELENS_SCHEDULER_ENABLED` | `1` | `0` per disattivare lo scheduler. |

---

## API principali

```
POST /api/auth/register · /api/auth/login      Autenticazione
GET  /api/auth/me

GET  /api/dashboard                            KPI + movers + distribuzione + alert recenti
GET  /api/products?search=&category=           Catalogo con statistiche calcolate
GET  /api/products/{id}                        Dettaglio + prezzi competitor + raccomandazione
GET  /api/products/{id}/history?days=30        Storico prezzi per grafico
POST /api/products · PATCH/DELETE /api/products/{id}

GET  /api/competitors · POST/PATCH/DELETE /api/competitors[/{id}]

GET  /api/alerts?unread=&severity=             Alert filtrati
POST /api/alerts/{id}/read · /api/alerts/read-all

GET  /api/repricing/preview                    Raccomandazioni per tutti i prodotti
POST /api/repricing/apply                      Applica un prezzo suggerito

GET  /api/export/products?format=csv|xlsx      Export catalogo
GET  /api/export/alerts?format=csv|xlsx        Export alert
GET  /api/export/history/{id}?format=csv|xlsx  Export storico prodotto

POST /api/collect                              Raccoglie subito i prezzi (utente corrente)
GET  /api/scheduler/status                     Stato dello scheduler periodico
GET  /api/health                               Stato del servizio (pubblico)
```

---

## Come funziona la raccolta prezzi

- **Simulata** (default): ogni competitor ha un `base_ratio` (es. 0.96 = 4% più economico)
  e segue un *random walk mean-reverting* con promozioni occasionali → serie storiche
  realistiche senza dipendere da rete esterna.
- **URL live**: con `price_source_type: "url"` e un `url`, il collector recupera la pagina
  (HTTPX) ed estrae il prezzo con tre strategie configurabili:
  - `jsonld` (default): parse di `schema.org/Product`/`Offer`;
  - `css`: `selector` CSS + `attribute` (es. `meta[itemprop=price]` → `content`);
  - `regex`: `pattern` con gruppo `price`.
  Usa il live solo su siti di cui hai il permesso di leggere i dati (rispetta ToS/robots).

## Come funziona il motore di repricing

Per ogni prodotto, PriceLens calcola:

1. **Floor** = `max(MAP, costo × (1 + margine_minimo))` — mai sotto il margine.
2. **Ceiling** = `MSRP` (o `max competitor × 1.05`) — mai sopra il tetto.
3. **Target** secondo la strategia scelta, poi `clamp(floor, target, ceiling)`.

---

## Test

```bash
make test
```

La suite (20 test) copre: health, autenticazione (login/register/401), isolamento tra
utenti, dashboard, catalogo, dettaglio prodotto, storico, competitor, alert, repricing
(preview + apply), raccolta prezzi, export CSV/Excel e stato dello scheduler.

---

## Architettura

```
backend/          FastAPI + SQLModel + SQLite
  app/
    models.py       User, Product, Competitor, PricePoint, Alert (multi-tenant)
    schemas.py      Modelli Pydantic input/output
    security.py     JWT + hashing password (PBKDF2)
    analytics.py    Statistiche di mercato + motore di repricing
    collector.py    Raccolta prezzi (simulata / JSON-LD / CSS / regex) + alert
    scheduler.py    Loop asyncio di raccolta periodica
    seed.py         Dati demo (utente, 12 prodotti, 6 competitor, 60 giorni)
    routers/        auth, products, competitors, alerts, dashboard, repricing, export, system
    main.py         App + lifespan + header di sicurezza + servizio frontend
  tests/            Suite pytest end-to-end (TestClient)

frontend/         React 18 + TypeScript + Vite + Tailwind v4 + Recharts
  src/pages/        Login, Dashboard, Prodotti, Dettaglio, Repricing, Competitor, Alert
  src/components/   Layout, chart, form, badge, KPI card, ecc.
```

---

## Licenza

Codice originale distribuito con licenza MIT. Minderest e REA sono marchi/progetti dei
rispettivi proprietari; questa è una reimplementazione indipendente delle sole feature
pubbliche.
