---
title: "PriceLens"
subtitle: "Guida tecnica e funzionale — come funziona l'app"
author: "Pricing Intelligence · clone migliorato di Minderest"
date: "Novembre 2025"
lang: it
---

# 1. Panoramica

**PriceLens** è un'applicazione web di *pricing intelligence* per l'e-commerce.
Monitora i prezzi dei competitor su retailer e marketplace, li confronta con il tuo
prezzo, genera alert automatici e — soprattutto — **suggerisce il prezzo da applicare**
con margini protetti.

A differenza di un semplice osservatore di prezzi, PriceLens chiude il ciclo:
*osserva → analizza → consiglia → applica*. Il passaggio finale è un pulsante.

## A chi serve

- **Retailer online** che vogliono restare competitivi senza erodere il margine.
- **Brand / manufacturer** che devono controllare la compliance **MAP/MSRP**
  (prezzo minimo pubblicizzato) dei propri rivenditori.
- **Team pricing** che hanno bisogno di storico, indicatori e automazioni.

## Cosa risolve

| Problema | Come lo risolve PriceLens |
| --- | --- |
| I competitor cambiano prezzo ogni giorno | Raccolta automatica periodica (scheduler) + storico |
| Non sai se sei caro o economico | Posizione (1° = più economico) e **indice di competitività 0–100** |
| Ribassare il prezzo erode il margine | Motore di repricing con **floor di margine** e **ceiling MSRP** |
| Scopri le violazioni MAP troppo tardi | Alert **critici** immediati ad ogni raccolta |
| I dati restano chiusi in un foglio Excel | Export **CSV / Excel**, API REST, multi-utente |

\newpage

# 2. Architettura

PriceLens è un monolite modulare a due strati: un backend **FastAPI** (API REST + serve
il frontend compilato) e un frontend **React/TypeScript** (SPA). Il database è **SQLite**
(zero configurazione, adatto a demo e piccoli deployment).

```
┌──────────────────────────────┐         ┌───────────────────────────────────┐
│  Browser — SPA React         │  HTTP   │  FastAPI (uvicorn)                │
│  Vite build → frontend/dist  │ ──────► │  /api/*  (JWT Bearer)             │
│  Tailwind + Recharts         │ ◄────── │  app.frontend("/") serve la SPA   │
└──────────────────────────────┘         └───────────────┬───────────────────┘
                                                         │ SQLModel
                                         ┌───────────────▼───────────────────┐
                                         │  SQLite  pricelens.db             │
                                         │  User · Product · Competitor      │
                                         │  PricePoint · Alert               │
                                         └───────────────┬───────────────────┘
                                                         │
                              ┌──────────────────────────▼──────────────────┐
                              │  Collector (thread)                         │
                              │  simulato | JSON-LD | CSS selector | regex  │
                              └──────────────────────────┬──────────────────┘
                                                         │
                              ┌──────────────────────────▼──────────────────┐
                              │  Scheduler asyncio (ogni N secondi)         │
                              └─────────────────────────────────────────────┘
```

## Stack tecnologico

| Livello | Tecnologie |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLModel, SQLite, Uvicorn |
| Sicurezza | PyJWT (HS256), PBKDF2-HMAC-SHA256, header HTTP |
| Raccolta | HTTPX, BeautifulSoup4, regex, simulatore deterministico |
| Export | `csv` (stdlib), openpyxl |
| Frontend | React 18, TypeScript, Vite 6, Tailwind CSS 4, Recharts, React Router 6 |
| Test | pytest, FastAPI TestClient |

## Flusso di una richiesta

1. Il browser carica la SPA da `http://host:8000/`.
2. La SPA chiama le API con `Authorization: Bearer <JWT>`.
3. FastAPI risolve l'utente dal token e filtra **tutti** i dati per `user_id`.
4. Il router calcola statistiche di mercato e restituisce JSON.
5. Il frontend disegna tabelle, grafici e card.

\newpage

# 3. Modello dati

Le entità principali sono legate al **team** tramite `team_id` (multi-tenancy a livello di riga).

```
User 1───N TeamMember N───1 Team
                             │
          ┌──────────────────┼──────────────────┬─────────────┐
          │                  │                  │             │
      Product 1─N PricePoint N─1 Competitor   Alert      AuditLog
```

## Entità

| Entità | Campi principali | Ruolo |
| --- | --- | --- |
| **User** | id, email (unique), password_hash | Account di accesso |
| **Team** | id, name | Workspace che possiede i dati |
| **TeamMember** | team_id, user_id, role | Appartenenza con ruolo **owner/admin/member** |
| **Product** | team_id, sku, name, brand, category, cost_price, current_price, msrp, map_price, strategy, min_margin_pct | Il prodotto che vendi |
| **Competitor** | team_id, name, domain, type, price_source_type, price_source_config | Chi monitori |
| **PricePoint** | team_id, product_id, competitor_id, price, stock_status, captured_at | Una rilevazione di prezzo nel tempo |
| **Alert** | team_id, product_id, competitor_id, type, severity, message, read | Evento da leggere |
| **AuditLog** | team_id, user_id, action, entity, entity_id, detail, ip | Registro append-only delle azioni |

## Vincoli e indici

- `UniqueConstraint(team_id, sku)` — lo SKU è unico **per team**.
- `UniqueConstraint(team_id, user_id)` su `TeamMember` — un utente entra una volta sola.
- Indice composito `(product_id, competitor_id, captured_at)` sui `PricePoint`:
  rende veloce l'ultimo prezzo per competitor.
- Indice su `captured_at` per le query "di oggi" della dashboard.

## Perché `team_id` anche su PricePoint e Alert

Anche se tecnicamente derivabili dal prodotto, tenerli denormalizzati permette di
filtrare con una sola condizione (`WHERE team_id = ?`) le query più frequenti
(conteggio alert, punti di oggi) senza join — e con un solo indice.

\newpage

# 4. Autenticazione e multi-utenza

## Registrazione e login

```
POST /api/auth/register   → crea utente, restituisce JWT
POST /api/auth/login      → verifica credenziali, restituisce JWT
GET  /api/auth/me         → profilo corrente
```

La password non è mai salvata in chiaro:

```python
salt = secrets.token_hex(16)
dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600_000)
hash = f"pbkdf2_sha256$600000${salt}${dk.hex()}"
```

Il confronto usa `hmac.compare_digest` (tempo costante, niente timing attack).

## Token e chiave di firma

- **JWT HS256**, payload `{sub, iat, exp}`.
- Scadenza di default **7 giorni** (`PRICELENS_TOKEN_EXPIRE_MINUTES`).
- La chiave viene da `PRICELENS_SECRET_KEY`; se assente viene **persistita** in
  `backend/.secret_key` (permessi `0600`) e riusata ai riavvii. Così le sessioni non
  decadono ad ogni restart e più worker condividono la stessa chiave.
- In produzione si può impostare `PRICELENS_SECRET_KEY` da un secret manager.

## Team e isolamento

Ogni utente appartiene a uno o più **team**. Il team attivo si sceglie con l'header
`X-Team-Id` (se assente, si usa il primo team dell'utente). Ogni endpoint applicativo ha
la dipendenza `CurrentTeamDep` e le query includono `WHERE team_id = <team>`.
Le letture per ID verificano la proprietà:

```python
def _get_owned(session, team_id, product_id) -> Product:
    product = session.get(Product, product_id)
    if product is None or product.team_id != team_id:
        raise HTTPException(404, "Prodotto non trovato")
    return product
```

Restituire **404** (invece di 403) evita di rivelare l'esistenza di risorse altrui
(anti-IDOR).

\newpage

# 5. Il ciclo del prezzo: la raccolta

Il `collector` è il cuore pulsante. Ad ogni "giro" crea un `PricePoint` per ogni
combinazione **prodotto attivo × competitor attivo** del team.

## Fonte simulata (default)

Pensata per demo e test: ogni competitor ha un prezzo "di riferimento"
`base = current_price × base_ratio` e si muove con un **random walk mean-reverting**:

- `base_ratio` — posizione tipica (0.96 = 4% più economico, 1.06 = 6% più caro);
- `volatility` — ampiezza del rumore giornaliero;
- `promo_prob` — probabilità di una promozione temporanea (−6%…−20%);
- `stockout_prob` — probabilità di esaurimento stock.

```
nuovo_prezzo = ultimo + (base − ultimo) × 0.3 + base × rumore(−vol, +vol)
```

Il fattore `0.3` è la *forza di richiamo*: se il prezzo si allontana troppo dalla base,
tende a tornare. Ne risultano serie storiche realistiche senza dipendere dalla rete.

## Fonte live (URL)

Con `price_source_type = "url"` il collector scarica la pagina (HTTPX) ed estrae il
prezzo con **tre strategie** configurabili:

| `selector_type` | Configurazione | Esempio |
| --- | --- | --- |
| `jsonld` (default) | — | `schema.org/Product` → `offers.price` |
| `css` | `selector`, `attribute` | `meta[itemprop=price]` + `content` |
| `regex` | `pattern` (gruppo `price`) | `"price"\s*:\s*"?([0-9.]+)` |

Il parsing degli importi normalizza i formati italiani e internazionali:
`1.234,56` → `1234.56`, `99.99` → `99.99`, `€ 1 234,56` → `1234.56`.

> **Nota.** Lo scraping live va usato solo su siti di cui hai il permesso di leggere i
> dati, rispettando ToS e `robots.txt`. In caso di errore il collector incrementa
> `errors` e non blocca il giro.

## Giro di raccolta

```
per ogni prodotto attivo:
  per ogni competitor attivo:
     prev = ultimo PricePoint
     prezzo, stock = simula oppure fetch_url
     inserisci nuovo PricePoint
     genera alert confrontando con prev
commit
```

\newpage

# 6. Analisi di mercato

Per ogni prodotto vengono calcolate, al volo, tre grandezze.

## Min / max / media

Si considerano solo i competitor **in stock** con prezzo valorizzato: un prezzo di un
prodotto esaurito non è un prezzo realmente acquistabile.

## Posizione

Il rango del tuo prezzo tra i prezzi dei competitor:

```
posizione = (numero di competitor più economici di te) + 1
```

`1` = sei il più economico. `N+1` = sei il più caro.

## Indice di competitività (0–100)

Un punteggio normalizzato, indipendente dal numero di competitor:

```
indice = 100 × (N − posizione + 1) / N
```

- più economico → **100**
- più caro → **100/N** (tende a 0 con molti competitor)

La dashboard media questo indice per dare un colpo d'occhio sulla salute del listino.

\newpage

# 7. Motore di repricing

Il repricing trasforma l'analisi in un'azione. Per ogni prodotto calcola:

1. **Floor** (pavimento) — sotto cui non si scende mai:
   `max(MAP, costo × (1 + margine_minimo))`
2. **Ceiling** (tetto) — sopra cui non si sale:
   `MSRP`, oppure `max competitor × 1.05` se manca l'MSRP.
3. **Target** secondo la strategia, poi `clamp(floor, target, ceiling)`.

## Le quattro strategie

| Strategia | Formula (indicativa) | Quando usarla |
| --- | --- | --- |
| **Allinea al minimo** (`match_min`) | `min − max(0.01, min×1%)` | Presidio del prezzo più basso |
| **Sottoquotazione** (`undercut`) | `min × 0.98` | Aggressiva, −2% sul minimo |
| **Margine protetto** (`margin_protected`) | `max(floor, min)` | Default: competitivi senza perdere margine |
| **Premium** (`premium`) | `ceiling` (MSRP o max×1.03) | Posizionamento alto di gamma |

## Esempio numerico

Prodotto: costo **650 €**, margine minimo **15%**, MAP **799 €**, MSRP **899 €**.

- Floor = `max(799, 650 × 1.15)` = `max(799, 747.5)` = **799 €**
- Competitor più economico = **780 €**
- Strategia `margin_protected` → target = `max(799, 780)` = **799 €**
- Ceiling = 899 € → il prezzo resta **799 €**
- Margine = `(799−650)/799` = **18,6 %**

Se invece il competitor scendesse a **760 €**, il floor (799) vince ancora: PriceLens
ti dice *"non scendere sotto 799"* — protegge il margine.

## Cosa restituisce

Ogni raccomandazione contiene: prezzo suggerito, margine stimato, delta % rispetto a
oggi, nuova posizione prevista, floor, ceiling e una **spiegazione in chiaro** del
perché. L'applicazione è un `POST /api/repricing/apply` che aggiorna `current_price`.

\newpage

# 8. Sistema di alert

Ogni osservazione viene confrontata con la precedente. Se scatta una condizione, viene
creato un `Alert` con severità e messaggio.

| Tipo | Quando | Severità |
| --- | --- | --- |
| `map_violation` | prezzo competitor < MAP del prodotto | **critico** |
| `price_drop` | calo ≥ **3 %** | avviso |
| `price_rise` | rialzo ≥ **3 %** | info |
| `out_of_stock` | stock passa a esaurito | avviso |
| `back_in_stock` | rientro in stock | info |

Gli alert sono per-utente, filtrabili per stato (letti/da leggere) e severità, e
possono essere esportati. La dashboard mostra gli ultimi e il conteggio degli aperti.

\newpage

# 9. Scheduler periodico

Un task **asyncio** avviato nel `lifespan` dell'app esegue la raccolta in background:

- intervallo: `PRICELENS_COLLECT_INTERVAL_SECONDS` (default **300 s**);
- interruttore: `PRICELENS_SCHEDULER_ENABLED=0` per disattivarlo;
- per ogni utente, esegue `collect_round` in un thread (`asyncio.to_thread`),
  così il calcolo bloccante non ferma il loop degli eventi.

Lo stato è consultabile su `GET /api/scheduler/status`
(`enabled`, `interval_seconds`, `running`, `last_run`, `last_error`, `last_result`).

> Con più processi uvicorn ogni processo avrebbe il proprio scheduler: in produzione
> conviene un solo worker, oppure spostare la raccolta in un job esterno.

\newpage

# 10. Export CSV ed Excel

Tre endpoint, tutti filtrati per utente:

```
GET /api/export/products?format=csv|xlsx
GET /api/export/alerts?format=csv|xlsx
GET /api/export/history/{product_id}?format=csv|xlsx&days=60
```

- **CSV**: generato con la stdlib `csv`, `text/csv; charset=utf-8`.
- **Excel**: generato con `openpyxl`, `application/vnd.openxmlformats-…sheet`.
- Il file arriva con `Content-Disposition: attachment` e nome parlante
  (`pricelens-prodotti.csv`, `pricelens-storico-<SKU>.xlsx`).

Nel frontend i pulsanti **CSV / Excel** scaricano il file via `fetch` con il token,
creano un `Blob` e avviano il download.

\newpage

# 11. Riferimento API

Tutti gli endpoint (tranne `health`, `register`, `login`) richiedono
`Authorization: Bearer <token>`.

| Metodo | Percorso | Descrizione |
| --- | --- | --- |
| GET | `/api/health` | Stato servizio (pubblico) |
| POST | `/api/auth/register` | Crea account |
| POST | `/api/auth/login` | Autentica |
| GET | `/api/auth/me` | Profilo corrente |
| GET | `/api/dashboard` | KPI, movers, distribuzione, alert recenti |
| GET | `/api/products` | Catalogo con statistiche (`search`, `category`, `active`) |
| GET | `/api/products/{id}` | Dettaglio + competitor + raccomandazione |
| GET | `/api/products/{id}/history` | Storico prezzi (`days`) |
| GET | `/api/products/categories` | Categorie distinte |
| POST | `/api/products` | Crea prodotto |
| PATCH | `/api/products/{id}` | Aggiorna prodotto |
| DELETE | `/api/products/{id}` | Elimina prodotto |
| GET | `/api/products/{id}/recommendation` | Solo raccomandazione |
| GET | `/api/competitors` | Elenco competitor |
| POST | `/api/competitors` | Crea competitor |
| PATCH | `/api/competitors/{id}` | Aggiorna competitor |
| DELETE | `/api/competitors/{id}` | Elimina competitor |
| GET | `/api/alerts` | Alert (`unread`, `severity`, `limit`) |
| GET | `/api/alerts/counts` | Conteggi totali/da leggere/critici |
| POST | `/api/alerts/{id}/read` | Segna letto |
| POST | `/api/alerts/read-all` | Segna tutti letti |
| GET | `/api/repricing/preview` | Raccomandazioni per tutti i prodotti |
| POST | `/api/repricing/apply` | Applica un prezzo suggerito |
| POST | `/api/collect` | Raccolta immediata (utente corrente) |
| GET | `/api/scheduler/status` | Stato scheduler |
| GET | `/api/export/...` | Export CSV/Excel |

La documentazione interattiva (OpenAPI/Swagger) è su **`/docs`**.

\newpage

# 12. Il frontend

SPA React in TypeScript, con routing client-side e un design system minimale
(Tailwind). Otto schermate:

| Pagina | Cosa mostra |
| --- | --- |
| **Login** | Accesso/registrazione; token salvato in `localStorage` |
| **Dashboard** | 4 KPI, indice di competitività per prodotto, top movers, alert recenti |
| **Prodotti** | Tabella con prezzo, min/max competitor, posizione, indice, alert; creazione, export |
| **Dettaglio** | Grafico storico 7/30/60 giorni, KPI, card repricing, tabella competitor, modifica |
| **Repricing** | Tabella delle raccomandazioni con applicazione one-click |
| **Competitor** | Card con tipo, fonte (simulata/live), prodotti tracciati; creazione |
| **Alert** | Lista filtrabile, segna-letto, export |
| **Attività** | Audit log del team: chi ha fatto cosa, quando, da quale IP |

Nella sidebar il **team switcher** cambia il workspace attivo (header `X-Team-Id`).

## Struttura del codice

```
frontend/src/
├── App.tsx            # routing + auth gate
├── pages/             # le 7 schermate
├── components/        # Layout, PriceChart, Modal, Badge, StatCard, …
├── lib/
│   ├── api.ts         # client tipizzato + gestione token/401
│   ├── auth.ts        # salvataggio token
│   ├── hooks.tsx      # AppProvider + useFetch con refresh globale
│   └── format.ts      # EUR, percentuali, date, "x min fa"
└── types.ts           # tipi allineati agli schemi backend
```

## Pattern di caricamento

`useFetch(fn, deps)` incapsula caricamento/errore e si ri-esegue quando cambia un
"token di refresh" globale. Il pulsante **Raccogli prezzi** chiama `/api/collect` e poi
`refresh()`: tutte le viste montate si aggiornano senza ricaricare la pagina.

\newpage

# 13. Sicurezza

| Misura | Implementazione |
| --- | --- |
| Password | PBKDF2-HMAC-SHA256, 600.000 iterazioni, salt casuale per utente |
| Token | JWT HS256 firmato, scadenza configurabile |
| Chiave | Persistita in `backend/.secret_key` (0600) se `PRICELENS_SECRET_KEY` manca |
| Isolamento dati | `WHERE team_id = …` su ogni query; 404 su risorse altrui |
| Ruoli team | owner/admin/member: solo owner/admin invitano o rimuovono membri |
| Rate limiting | 10 richieste/min per IP su `/api/auth`, 300/min sulle altre API |
| Audit log | Registro append-only per team (azione, entità, dettaglio, IP) |
| Header | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` |
| CORS | Solo origini di sviluppo esplicite (`localhost:5173`, `127.0.0.1:5173`, `localhost:3000`) |
| Input | Validazione Pydantic (email, prezzi > 0, lunghezze, enumerazioni) |
| Query | ORM parametrizzato (niente SQL concatenato) |

> **Nota.** In un deployment multi-istanza imposta `PRICELENS_SECRET_KEY` (o condividi
> lo stesso `.secret_key`): il rate limiter è in-process, quindi per più worker serve un
> limiter condiviso (Redis) se vuoi un limite globale.

\newpage

# 14. Avvio e configurazione

## Comandi

```bash
make setup     # crea backend/.venv, installa pip + npm
make serve     # build frontend + uvicorn su :8000
# oppure in sviluppo:
make backend   # uvicorn :8000 con reload
make frontend  # Vite :5173 (proxy /api → :8000)
make test      # suite pytest
```

Al primo avvio vengono creati il database e i dati demo:

```
demo@pricelens.it   / demo1234   (owner)
collega@pricelens.it / demo1234   (member)
Team: PriceLens HQ · 12 prodotti · 6 competitor · 60 giorni di storico
```

## Variabili d'ambiente

| Variabile | Default | Significato |
| --- | --- | --- |
| `PRICELENS_DATABASE_URL` | `sqlite:///./pricelens.db` | Database (SQLite o Postgres) |
| `PRICELENS_SECRET_KEY` | persistita su file | Chiave firma JWT |
| `PRICELENS_SECRET_KEY_FILE` | `backend/.secret_key` | File dove persistere la chiave |
| `PRICELENS_TOKEN_EXPIRE_MINUTES` | `10080` | Durata token |
| `PRICELENS_COLLECT_INTERVAL_SECONDS` | `300` | Intervallo scheduler |
| `PRICELENS_SCHEDULER_ENABLED` | `1` | `0` per disattivare |
| `PRICELENS_RATE_LIMIT_ENABLED` | `1` | `0` per disattivare il rate limiting |
| `PRICELENS_RATE_LIMIT_PER_MINUTE` | `300` | Limite API per IP al minuto |
| `PRICELENS_AUTH_RATE_LIMIT_PER_MINUTE` | `10` | Limite auth per IP al minuto |

\newpage

# 15. Test

Due suite, entrambe eseguite in CI.

**Backend** (`backend/tests`, **36 test**) con `TestClient` e database temporaneo:

| Area | Cosa verifica |
| --- | --- |
| Health | endpoint pubblico |
| Auth | login, `/me`, password errata, 401 senza token, registrazione duplicata |
| Team | lista/creazione, invito e rimozione membri, isolamento tra team, ruoli |
| Isolamento | un nuovo utente non vede i dati altrui |
| Dashboard | presenza KPI e sezioni |
| Prodotti | lista, dettaglio, storico, categorie, creazione/eliminazione, SKU duplicato |
| Competitor | lista e CRUD |
| Alert | lista, segna letto, segna tutti |
| Repricing | preview e applicazione |
| Raccolta | `POST /api/collect` |
| Export | CSV e XLSX |
| Audit | registrazione azioni e isolamento tra team |
| Unit | hashing, parsing importi/JSON-LD/regex, math repricing, rate limiter |

**Frontend** (`frontend/src`, **16 test** con Vitest + Testing Library):
formattazione valute/percentuali, storage token/team, componenti `Badge` e `PriceDelta`.

```bash
make test                 # backend → 36 passed
cd frontend && npm test   # frontend → 16 passed
```

\newpage

# 16. Note operative

## iCloud Drive e disco pieno

Se il progetto vive in una cartella sincronizzata con iCloud Drive e il disco è quasi
pieno, macOS può rendere i file "dataless" (contenuto evicted). Sintomi:
`Operation timed out` in lettura, venv/node_modules lentissimi.

Soluzioni:

1. Liberare spazio su disco.
2. Spostare il progetto fuori da `~/Documents` (es. `~/Projects/pricelens`).
3. Tenere il virtualenv fuori da iCloud:
   `python3 -m venv /tmp/pricelens-venv`.

## Troubleshooting rapido

| Sintomo | Causa probabile | Rimedio |
| --- | --- | --- |
| 401 su tutte le API | token assente/scaduto | rifare login |
| Dashboard vuota su un nuovo utente | corretto: i dati sono per-utente | creare prodotti/competitor |
| `Attribute "app" not found` all'avvio | file `main.py` illeggibile (eviction) | riscrivere/ripristinare il file |
| Porta 8000 occupata | vecchio uvicorn | `pkill -f "uvicorn app.main"` |

\newpage

# 17. Glossario

| Termine | Significato |
| --- | --- |
| **MAP** | *Minimum Advertised Price* — prezzo minimo pubblicizzabile |
| **MSRP** | *Manufacturer's Suggested Retail Price* — prezzo consigliato |
| **Floor** | Prezzo minimo applicabile (MAP o costo + margine) |
| **Ceiling** | Prezzo massimo applicabile (MSRP o max competitor) |
| **Price index** | Indice 0–100 di competitività del prezzo |
| **PricePoint** | Singola rilevazione di prezzo di un competitor |
| **Repricing** | Adeguamento del prezzo sulla base dei dati di mercato |
| **JWT** | JSON Web Token, usato per l'autenticazione stateless |
| **SPA** | Single Page Application (frontend React) |

::: finalnote
**PriceLens** — guida tecnica e funzionale.
Clone migliorato di Minderest, ispirato alla metodologia REA.
:::
