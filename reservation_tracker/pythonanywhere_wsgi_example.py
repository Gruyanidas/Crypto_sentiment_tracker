# ============================================================================
#  PRIMER WSGI KONFIGURACIJE ZA PYTHONANYWHERE
# ----------------------------------------------------------------------------
#  Ovo NIJE fajl koji aplikacija sama koristi. Sadržaj iskopiraj u WSGI
#  konfiguracioni fajl koji ti PythonAnywhere napravi (Web tab -> link
#  "WSGI configuration file"). Obriši sve što je tamo i nalepi ovo.
#
#  Zameni:
#    - KORISNIK            -> tvoje PythonAnywhere korisničko ime
#    - tvoja-jaka-lozinka  -> lozinka za prijavu u aplikaciju
#    - dugacak-nasumican.. -> bilo kakav dug nasumičan tekst (40+ karaktera)
# ============================================================================

import os
import sys

# --- Tajne vrednosti (ostaju samo na serveru, ne idu na GitHub) ---
os.environ["APP_USERNAME"] = "admin"
os.environ["APP_PASSWORD"] = "tvoja-jaka-lozinka"
os.environ["SECRET_KEY"]   = "dugacak-nasumican-string-bilo-sta-vise-od-40-karaktera"

# --- Putanja do aplikacije ---
path = "/home/KORISNIK/Crypto_sentiment_tracker/reservation_tracker"
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application  # noqa: E402
