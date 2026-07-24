"""
Script à lancer UNE FOIS en local pour préparer des données de démo.

Ce script télécharge quelques sessions F1 (depuis ton ordinateur, là où le
réseau fonctionne bien) et prépare un dossier `demo_cache/` contenant ces
données déjà téléchargées. En incluant ce dossier dans ton dépôt GitHub, le
dashboard déployé en ligne pourra utiliser ces sessions sans avoir besoin de
recontacter les serveurs F1 (qui bloquent parfois les requêtes venant de
serveurs cloud).

Lancement :
    python3 prepare_demo_data.py
"""

import fastf1
import os
import shutil

EXPORT_DIR = "demo_cache"

# Sessions à préparer pour la démo en ligne — modifie cette liste si tu veux
# d'autres Grand Prix / saisons garantis disponibles.
SESSIONS = [
    (2024, "Monza", "R"),
    (2024, "Bahrain", "R"),
]

if os.path.exists(EXPORT_DIR):
    shutil.rmtree(EXPORT_DIR)
os.makedirs(EXPORT_DIR)

fastf1.Cache.enable_cache(EXPORT_DIR)

for year, gp, session_type in SESSIONS:
    print(f"Téléchargement : {year} {gp} {session_type} ...")
    session = fastf1.get_session(year, gp, session_type)
    session.load(laps=True, telemetry=True, weather=False, messages=False)
    print(f"  -> OK, {len(session.laps)} tours chargés.")

print()
print("Terminé ! Le dossier 'demo_cache/' est prêt.")
print("Prochaine étape : upload ce dossier sur GitHub, à la racine du projet,")
print("à côté de app.py.")
