# imfinity – Aplikacija za zakazivanje termina

Jednostavna web aplikacija za vlasnika kozmetičkog centra za vođenje termina:
mesečni kalendar, pregled dana sa slobodnim/zauzetim terminima, istorija
klijenata i zakazivanje narednih tretmana. Tamno-zlatni dizajn, prilagođen
prvenstveno telefonu, na srpskom jeziku.

---

## Tehnologije

- **Python + Flask** — web server
- **SQLite** — baza podataka (jedan fajl `reservations.db`)
- **HTML + CSS (bez frameworka)** — tamno-zlatna tema, Cormorant Garamond + Inter fontovi
- **PWA** — dodavanje na početni ekran telefona kao "prava" aplikacija

---

## Struktura projekta

```
reservation_tracker/
├── app.py                 # Flask rute (login, kalendar, dan, zakazivanje...)
├── database.py            # SQLite: kreiranje tabele i upiti
├── requirements.txt       # Python biblioteke (Flask, gunicorn)
├── Procfile               # za hosting koji koristi gunicorn
├── pythonanywhere_wsgi_example.py  # primer WSGI konfiguracije za PythonAnywhere
├── templates/             # HTML stranice
│   ├── base.html          # zajednički okvir (header, PWA tagovi)
│   ├── login.html         # prijava
│   ├── calendar.html      # mesečni kalendar
│   ├── day.html           # pregled jednog dana + zakazivanje
│   ├── client.html        # istorija termina jednog klijenta
│   └── form.html          # forma za dodavanje/izmenu termina
└── static/
    ├── style.css          # kompletan dizajn
    ├── manifest.json      # PWA manifest
    └── icon-*.png         # ikonice aplikacije
```

---

## Pokretanje lokalno (na svom računaru)

```bash
cd reservation_tracker
pip install flask
python app.py
```
Zatim otvori `http://localhost:5050` u browseru.

Prijava (lokalno, podrazumevano): korisnik `admin`, lozinka `imfinity2025`.

---

## Hosting (PythonAnywhere)

Aplikacija je hostovana na PythonAnywhere (besplatan plan ima trajni disk, pa
SQLite baza preživljava restartove).

**Ažuriranje nakon izmena u kodu:**
```bash
cd ~/Crypto_sentiment_tracker
git pull
```
Pa na **Web** tabu klikni **Reload**.

`git pull` ne dira bazu `reservations.db` (namerno je izvan git-a), pa termini
ostaju netaknuti pri svakom ažuriranju.

**Lozinka i tajni ključ** se na hostingu postavljaju kroz environment
varijable u WSGI fajlu (vidi `pythonanywhere_wsgi_example.py`):
`APP_USERNAME`, `APP_PASSWORD`, `SECRET_KEY`. Tako prave vrednosti ne stoje u
kodu na GitHub-u.

---

## Gde se menjaju česta podešavanja (u `app.py`)

| Šta | Promenljiva | Trenutno |
|-----|-------------|----------|
| Radno vreme radnim danima | `WEEKDAY_HOURS` | 16:00–21:00 |
| Radno vreme vikendom | `WEEKEND_HOURS` | 11:00–21:00 |
| Ponuđene usluge | `SERVICES` | Kontrola, Botox, Usta, Kolagen, Konsultacije |
| Boje usluga | `SERVICE_COLORS` | po usluzi |

Forma uvek nudi i opciju "Ostalo" za ručni unos usluge.

---

## Nastavak rada u budućnosti

Sav kod živi na GitHub-u (`Gruyanidas/Crypto_sentiment_tracker`, grana `main`).
Za nove izmene: otvori novu Claude sesiju, navedi repozitorijum i folder
`reservation_tracker`, i opiši šta želiš da se promeni.
