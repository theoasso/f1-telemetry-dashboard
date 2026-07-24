"""
F1 Telemetry & Performance Dashboard
------------------------------------
Dashboard d'analyse de données F1 basé sur FastF1 (données réelles officielles).

Fonctionnalités :
1. Chargement d'une session (essais, qualifs, course) pour une saison/GP donné
2. Comparaison de deux pilotes sur un tour (delta temps, vitesse, freinage)
3. Analyse de dégradation des pneus (temps au tour vs âge du train de pneus)
4. Analyse de rythme de course (race pace) par pilote / écurie

Lancement :
    streamlit run app.py

Prérequis :
    pip install fastf1 streamlit plotly pandas numpy
"""

import streamlit as st
import fastf1
import fastf1.plotting
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import tempfile
import shutil

# ---------------------------------------------------------------------------
# Configuration générale
# ---------------------------------------------------------------------------

st.set_page_config(page_title="F1 Telemetry Dashboard", layout="wide", page_icon="🏎️")

# Sur certains environnements cloud, un dossier relatif peut ne pas être
# accessible en écriture d'un run à l'autre : on utilise le dossier temporaire
# du système, garanti disponible en écriture.
CACHE_DIR = os.path.join(tempfile.gettempdir(), "f1_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# Si un dossier "demo_cache" a été inclus dans le projet (données pré-
# téléchargées via prepare_demo_data.py), on copie son contenu dans le cache
# actif : ces sessions précises seront alors disponibles instantanément, sans
# avoir besoin de contacter les serveurs F1 (utile si le réseau du serveur
# cloud est limité).
DEMO_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_cache")
if os.path.isdir(DEMO_CACHE_DIR):
    shutil.copytree(DEMO_CACHE_DIR, CACHE_DIR, dirs_exist_ok=True)

fastf1.Cache.enable_cache(CACHE_DIR)

TEAM_COLORS = {
    "Red Bull Racing": "#3671C6", "Ferrari": "#E8002D", "Mercedes": "#27F4D2",
    "McLaren": "#FF8000", "Aston Martin": "#229971", "Alpine": "#FF87BC",
    "Williams": "#64C4FF", "RB": "#6692FF", "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
}


# ---------------------------------------------------------------------------
# Chargement des données (avec cache Streamlit pour éviter les rechargements)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Chargement de la session FastF1...")
def load_session(year: int, gp: str, session_type: str):
    session = fastf1.get_session(year, gp, session_type)

    # 1. Chargement des tours/temps (léger, fiable) — indispensable.
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    if session.laps is None or session.laps.empty:
        raise RuntimeError(
            "Aucun tour n'a été chargé pour cette session — la session n'existe "
            "peut-être pas encore, ou les données ne sont pas disponibles côté FastF1."
        )

    # 2. Tentative de chargement de la télémétrie détaillée (plus lourd, peut
    # échouer sur certains environnements cloud à cause de limitations réseau
    # côté serveurs F1). Si ça échoue, on continue quand même : les onglets
    # dégradation pneus et rythme de course n'en ont pas besoin.
    try:
        session.load(laps=True, telemetry=True, weather=False, messages=False)
        session.telemetry_available = True
    except Exception:
        session.telemetry_available = False

    return session


def get_driver_list(session):
    return sorted(session.laps["Driver"].unique().tolist())


# ---------------------------------------------------------------------------
# Sidebar : sélection de la session
# ---------------------------------------------------------------------------

st.sidebar.title("🏎️ F1 Data Explorer")
st.sidebar.markdown("Basé sur [FastF1](https://docs.fastf1.dev/) — données télémétrie officielles.")

if os.path.isdir(DEMO_CACHE_DIR):
    st.sidebar.info(
        "💡 Sessions garanties en ligne (données pré-chargées) : "
        "**2024 Monza R**, **2024 Bahrain R**. D'autres sessions peuvent "
        "aussi fonctionner selon la disponibilité réseau du serveur."
    )

year = st.sidebar.selectbox("Saison", list(range(2026, 2017, -1)), index=1)
gp = st.sidebar.text_input("Grand Prix (nom ou round)", value="Monza")
session_type = st.sidebar.selectbox(
    "Session", ["FP1", "FP2", "FP3", "Q", "R", "Sprint"], index=4
)

load_btn = st.sidebar.button("Charger la session", type="primary")

if "session" not in st.session_state:
    st.session_state.session = None

if load_btn:
    try:
        st.session_state.session = load_session(year, gp, session_type)
        st.sidebar.success("Session chargée.")
    except Exception as e:
        st.sidebar.error(f"Erreur de chargement : {e}")

session = st.session_state.session

st.title("Analyse de performance F1")

if session is None:
    st.info(
        "Choisis une saison, un Grand Prix et un type de session dans le menu à "
        "gauche, puis clique sur **Charger la session** pour démarrer l'analyse.\n\n"
        "⚠️ Le premier chargement d'une session peut prendre 10 à 30 secondes "
        "(téléchargement + mise en cache local des données FastF1)."
    )
    st.stop()

drivers = get_driver_list(session)

if not getattr(session, "telemetry_available", True):
    st.warning(
        "⚠️ La télémétrie détaillée (vitesse, freinage) n'a pas pu être chargée pour "
        "cette session — probablement une limitation réseau temporaire côté serveur. "
        "Les onglets **Comparaison de tours** et **Carte du circuit** seront indisponibles, "
        "mais **Dégradation pneus** et **Rythme de course** fonctionnent normalement "
        "(ils n'ont besoin que des temps au tour)."
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔁 Comparaison de tours", "🛞 Dégradation pneus", "📊 Rythme de course", "🗺️ Carte du circuit"]
)

# ---------------------------------------------------------------------------
# Onglet 1 : Comparaison de deux pilotes sur leur meilleur tour
# ---------------------------------------------------------------------------

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        drv1 = st.selectbox("Pilote 1", drivers, index=0, key="drv1")
    with col2:
        drv2 = st.selectbox("Pilote 2", drivers, index=min(1, len(drivers) - 1), key="drv2")

    if st.button("Comparer les tours", key="compare_btn"):
        try:
            lap1 = session.laps.pick_driver(drv1).pick_fastest()
            lap2 = session.laps.pick_driver(drv2).pick_fastest()

            tel1 = lap1.get_car_data().add_distance()
            tel2 = lap2.get_car_data().add_distance()

            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                subplot_titles=("Vitesse (km/h)", "Delta temps (s)", "Freinage"),
                row_heights=[0.45, 0.25, 0.3], vertical_spacing=0.08,
            )

            fig.add_trace(go.Scatter(x=tel1["Distance"], y=tel1["Speed"], name=drv1), row=1, col=1)
            fig.add_trace(go.Scatter(x=tel2["Distance"], y=tel2["Speed"], name=drv2), row=1, col=1)

            # Delta temps interpolé sur distance commune
            ref_dist = np.linspace(0, min(tel1["Distance"].max(), tel2["Distance"].max()), 500)
            t1 = np.interp(ref_dist, tel1["Distance"], tel1["Time"].dt.total_seconds())
            t2 = np.interp(ref_dist, tel2["Distance"], tel2["Time"].dt.total_seconds())
            delta = t2 - t1
            fig.add_trace(go.Scatter(x=ref_dist, y=delta, name=f"{drv2} - {drv1}",
                                      line=dict(color="grey")), row=2, col=1)

            fig.add_trace(go.Scatter(x=tel1["Distance"], y=tel1["Brake"].astype(int),
                                      name=f"{drv1} frein"), row=3, col=1)
            fig.add_trace(go.Scatter(x=tel2["Distance"], y=tel2["Brake"].astype(int),
                                      name=f"{drv2} frein"), row=3, col=1)

            fig.update_layout(height=750, hovermode="x unified")
            fig.update_xaxes(title_text="Distance (m)", row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)

            c1, c2 = st.columns(2)
            c1.metric(f"Meilleur tour {drv1}", str(lap1["LapTime"]))
            c2.metric(f"Meilleur tour {drv2}", str(lap2["LapTime"]))

        except Exception as e:
            st.error(f"Impossible de comparer ces pilotes : {e}")

# ---------------------------------------------------------------------------
# Onglet 2 : Dégradation des pneus
# ---------------------------------------------------------------------------

with tab2:
    drv_deg = st.selectbox("Pilote", drivers, key="drv_deg")

    if st.button("Analyser la dégradation", key="deg_btn"):
        try:
            laps_drv = session.laps.pick_driver(drv_deg).pick_quicklaps()
            laps_drv = laps_drv[laps_drv["PitInTime"].isna()]  # exclure tours d'entrée aux stands
            laps_drv = laps_drv.copy()
            laps_drv["LapTimeSeconds"] = laps_drv["LapTime"].dt.total_seconds()

            fig = go.Figure()
            for compound in laps_drv["Compound"].dropna().unique():
                sub = laps_drv[laps_drv["Compound"] == compound]
                fig.add_trace(go.Scatter(
                    x=sub["TyreLife"], y=sub["LapTimeSeconds"],
                    mode="markers+lines", name=compound,
                ))

            fig.update_layout(
                title=f"Dégradation pneus — {drv_deg}",
                xaxis_title="Âge du train de pneus (tours)",
                yaxis_title="Temps au tour (s)",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Une pente positive marquée indique une dégradation forte : "
                "utile pour estimer la fenêtre optimale d'arrêt au stand."
            )
        except Exception as e:
            st.error(f"Impossible d'analyser la dégradation : {e}")

# ---------------------------------------------------------------------------
# Onglet 3 : Rythme de course global
# ---------------------------------------------------------------------------

with tab3:
    if st.button("Afficher le rythme de course", key="pace_btn"):
        try:
            laps = session.laps.pick_quicklaps().copy()
            laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()

            fig = go.Figure()
            for drv in drivers:
                sub = laps[laps["Driver"] == drv]
                if sub.empty:
                    continue
                fig.add_trace(go.Box(y=sub["LapTimeSeconds"], name=drv, boxpoints="outliers"))

            fig.update_layout(
                title="Distribution des temps au tour par pilote",
                yaxis_title="Temps au tour (s)",
                height=550,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Boîtes plus basses et plus resserrées = rythme plus rapide et plus régulier."
            )
        except Exception as e:
            st.error(f"Impossible d'afficher le rythme de course : {e}")

# ---------------------------------------------------------------------------
# Onglet 4 : Carte du circuit colorée par vitesse
# ---------------------------------------------------------------------------

with tab4:
    drv_map = st.selectbox("Pilote", drivers, key="drv_map")
    metric = st.radio(
        "Colorer par", ["Vitesse", "Freinage", "Accélérateur"],
        horizontal=True, key="metric_map",
    )

    if st.button("Afficher la carte", key="map_btn"):
        try:
            lap = session.laps.pick_driver(drv_map).pick_fastest()
            tel = lap.get_telemetry()

            x = tel["X"].to_numpy()
            y = tel["Y"].to_numpy()

            if metric == "Vitesse":
                color_val = tel["Speed"].to_numpy()
                colorbar_title = "km/h"
                colorscale = "Turbo"
            elif metric == "Freinage":
                color_val = tel["Brake"].astype(int).to_numpy()
                colorbar_title = "Frein (0/1)"
                colorscale = "Reds"
            else:
                color_val = tel["Throttle"].to_numpy()
                colorbar_title = "% accélérateur"
                colorscale = "Greens"

            # Construction de segments de ligne colorés (un segment entre chaque point)
            import plotly.colors as pc

            fig = go.Figure()
            n_segments = min(len(x) - 1, 400)  # limite pour rester fluide
            step = max(1, (len(x) - 1) // n_segments)

            vmin, vmax = float(np.min(color_val)), float(np.max(color_val))

            for i in range(0, len(x) - step, step):
                norm = 0.0 if vmax == vmin else (float(color_val[i]) - vmin) / (vmax - vmin)
                rgb_color = pc.sample_colorscale(colorscale, norm)[0]
                fig.add_trace(go.Scatter(
                    x=x[i:i + step + 1], y=y[i:i + step + 1],
                    mode="lines",
                    line=dict(
                        color=rgb_color,
                        width=5,
                    ),
                    showlegend=False,
                    hoverinfo="skip",
                ))

            # Overlay invisible pour afficher une colorbar correcte
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="markers",
                marker=dict(
                    size=0.1, color=color_val, colorscale=colorscale,
                    showscale=True, colorbar=dict(title=colorbar_title),
                ),
                showlegend=False,
                hovertext=[f"{v:.0f}" for v in color_val],
            ))


            fig.update_layout(
                title=f"Circuit — {drv_map} — coloré par {metric.lower()} (tour le plus rapide)",
                height=650,
                xaxis=dict(visible=False, scaleanchor="y", scaleratio=1),
                yaxis=dict(visible=False),
                plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Chaque segment du tracé est coloré selon la valeur locale de la "
                "métrique choisie — utile pour repérer visuellement freinages tardifs, "
                "zones de plein gaz, ou pertes de vitesse en courbe."
            )
        except Exception as e:
            st.error(f"Impossible d'afficher la carte du circuit : {e}")
