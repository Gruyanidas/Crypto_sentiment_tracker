# ============================================================================
#  ПРИМЕР WSGI КОНФИГУРАЦИЈА ЗА PYTHONANYWHERE – DERMA PLUS
# ----------------------------------------------------------------------------
#  Ова НЕ е фајл кој апликацијата самата го користи. Содржината копирај ја
#  во WSGI конфигурациониот фајл кој PythonAnywhere го прави (Web tab ->
#  линкот "WSGI configuration file"). Избриши сè што е таму и залепи го ова.
#
#  Замени:
#    - KORISNIK            -> твое PythonAnywhere корисничко име
#    - tvoja-jaka-lozinka  -> лозинка за најава во апликацијата
#    - dugacak-nasumican.. -> било каков долг насумичен текст (40+ карактери)
# ============================================================================

import os
import sys

# --- Тајни вредности (остануваат само на серверот, не одат на GitHub) ---
os.environ["APP_USERNAME"] = "admin"
os.environ["APP_PASSWORD"] = "tvoja-jaka-lozinka"
os.environ["SECRET_KEY"]   = "dugacak-nasumican-string-bilo-sto-poveke-od-40-karakteri"

# --- Патека до апликацијата ---
path = "/home/KORISNIK/Crypto_sentiment_tracker/dermaplus_tracker"
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application  # noqa: E402
