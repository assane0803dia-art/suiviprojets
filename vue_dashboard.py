import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from auth import require_login, logout_button, get_last_project
from ui_style import sidebar_brand, kpi_card_html, section_title, badge_html, style_plotly_chart, tip, wrap_label, hauteur_graphique_wrap, truncate_label
from i18n import t
from indicators_config import (
    load_all_indicators,
    load_visible_indicators,
    update_indicator,
    compute_kpi_value,
    format_kpi_value,
)
import db
import crud
import critical_path
import indicateurs_temporels

require_login()
sidebar_brand()
logout_button()

user = st.session_state.get("user", {})
is_admin = user.get("role") == "admin"

import datetime as _dt
if st.session_state.get("notifs_generees_le") != _dt.date.today().isoformat():
    try:
        crud.generer_notifications_activites_a_venir()
        st.session_state["notifs_generees_le"] = _dt.date.today().isoformat()
    except Exception:
        pass  # Si la table Notifications n'existe pas encore (migration non exécutée), on ignore silencieusement


@st.cache_data(ttl=300)
def load_vue_dashboard():
    return db.run_query("SELECT * FROM V_Dashboard_Projets")


col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.title(t("dashboard_title"))
    st.caption(t("dashboard_subtitle"))
with col_refresh:
    st.write("")
    if st.button("🔄 Actualiser", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()

if user.get("compte_restreint"):
    projets_df = crud.get_projets_restreints(user["id"])
else:
    projets_df = crud.get_projets()

if projets_df.empty:
    st.info("👋 Aucun projet pour l'instant. Rendez-vous dans **📁 Nouveau projet** pour créer votre premier projet.")
    st.stop()

# ----------------------------------------------------------------------------
# Sélection du projet
# ----------------------------------------------------------------------------
projet_options = {row["id"]: row["nom"] for _, row in projets_df.iterrows()}
dernier_projet_id = get_last_project(user.get("id"))
default_index = list(projet_options.keys()).index(dernier_projet_id) if dernier_projet_id in projet_options else 0

selected_projet_id = st.selectbox(
    "📌 Projet à afficher",
    options=list(projet_options.keys()),
    format_func=lambda x: projet_options[x],
    index=default_index,
)

projet_row = projets_df[projets_df["id"] == selected_projet_id].iloc[0]

# ----------------------------------------------------------------------------
# Détails du projet — en haut, lisible, un seul projet à la fois
# ----------------------------------------------------------------------------
statut_kind = {"En cours": "success", "Planifié": "muted", "Terminé": "success", "Suspendu": "warning"}.get(projet_row["statut"], "muted")

st.markdown(f"## {projet_row['nom']}")
st.markdown(badge_html(projet_row["statut"] or "Sans statut", statut_kind), unsafe_allow_html=True)
st.caption(projet_row["description"] or "Aucune description")

activites_df = crud.get_activites_by_projet(selected_projet_id)
taches_df = crud.get_taches_by_projet(selected_projet_id)
depenses_projet_dash = crud.get_depenses_by_projet(selected_projet_id)
depense_reelle_dash = float(depenses_projet_dash["montant"].sum()) if not depenses_projet_dash.empty else 0.0

lignes_budget_dash = crud.get_budget_lignes_by_projet(selected_projet_id)
total_hierarchique_dash = float(lignes_budget_dash["cout_total"].sum()) if not lignes_budget_dash.empty else 0.0
budget_active_dash = float(activites_df["budget"].fillna(0).sum()) if not activites_df.empty else 0.0
# Le budget hiérarchique détaillé (Rubriques/Sous-rubriques/Lignes) est la référence la
# plus précise s'il est renseigné — sinon on retombe sur l'ancien total par activité,
# exactement la même logique que dans la section Budget de "Mes projets".
reference_budget_dash = total_hierarchique_dash if total_hierarchique_dash > 0 else budget_active_dash
taux_execution_dash = (depense_reelle_dash / reference_budget_dash * 100) if reference_budget_dash else 0.0

detail_cols = st.columns(5)
detail_cols[0].metric("Budget", f"{(projet_row['budget'] or 0):,.0f} FCFA".replace(",", " "))
detail_cols[1].metric("Dépensé réellement", f"{depense_reelle_dash:,.0f} FCFA".replace(",", " "), delta=f"{taux_execution_dash:.0f}% exécuté")
detail_cols[2].metric("Début", str(projet_row["date_debut"] or "—"))
detail_cols[3].metric("Fin prévue", str(projet_row["date_fin"] or "—"))
detail_cols[4].metric("Responsable", projet_row["responsable"] or "—")

st.divider()

# ----------------------------------------------------------------------------
# Données du projet sélectionné
# ----------------------------------------------------------------------------
try:
    df_all = load_vue_dashboard()
except Exception as e:
    st.error(f"Impossible de se connecter à la base de données : {e}")
    st.stop()

df_projet = df_all[df_all["projet"] == projet_row["nom"]]
NOM_COLONNE_PROGRESSION = "progression_projet"

# ----------------------------------------------------------------------------
# Indicateurs clés — les VRAIS indicateurs définis dans ce projet (résultats +
# indicateurs supplémentaires), pas une liste générique identique pour tous les
# projets. Organisés en 4 niveaux : vue d'ensemble -> par objectif -> graphique
# global -> détails complets (repliés).
# ----------------------------------------------------------------------------
section_title("📊", "Indicateurs clés")

resultats_df_kpi = crud.get_resultats_by_projet(selected_projet_id)
indicateurs_suppl_kpi = crud.get_indicateurs_supplementaires_by_projet(selected_projet_id)

progression_moyenne_activites = float(activites_df["progression"].fillna(0).mean()) if not activites_df.empty else None


def _statut_indicateur(actuelle, cible):
    """Classification automatique — jamais définie manuellement, uniquement à
    partir du niveau de réalisation par rapport à la cible."""
    if not cible:
        return ("⚪", "muted", "Non défini", None)
    pct = (actuelle or 0) / cible * 100
    if pct >= 100:
        return ("🟢", "success", "Objectif atteint", pct)
    elif pct >= 60:
        return ("🔵", "muted", "Bonne progression", pct)
    elif pct >= 30:
        return ("🟠", "warning", "Attention", pct)
    else:
        return ("🔴", "danger", "Retard critique", pct)


indicateurs_liste = []
if not resultats_df_kpi.empty:
    for _, r in resultats_df_kpi.iterrows():
        if r["indicateur"]:
            indicateurs_liste.append({
                "nom": r["indicateur"], "baseline": r["baseline"], "actuelle": r["valeur_actuelle"],
                "cible": r["valeur_cible"], "unite": r["unite"] or "", "objectif": r["objectif_titre"],
            })
if not indicateurs_suppl_kpi.empty:
    for _, i in indicateurs_suppl_kpi.iterrows():
        indicateurs_liste.append({
            "nom": i["nom"], "baseline": i["baseline"], "actuelle": i["valeur_actuelle"],
            "cible": i["valeur_cible"], "unite": i["unite"] or "", "objectif": i["objectif_titre"],
        })

if not indicateurs_liste and progression_moyenne_activites is None:
    st.info("Aucun indicateur défini pour ce projet pour l'instant — ajoutez-en depuis la section Résultats de « Mes projets ».")
else:
    # ------------------------------------------------------------------------
    # 1. Vue d'ensemble
    # ------------------------------------------------------------------------
    for ind in indicateurs_liste:
        ind["statut"] = _statut_indicateur(ind["actuelle"], ind["cible"])

    avec_cible = [i for i in indicateurs_liste if i["statut"][3] is not None]
    nb_atteints = sum(1 for i in avec_cible if i["statut"][0] == "🟢")
    taux_global = (sum(i["statut"][3] for i in avec_cible) / len(avec_cible)) if avec_cible else 0

    vue_cols = st.columns(3)
    vue_cols[0].markdown(kpi_card_html("📈", "Progression moyenne", f"{progression_moyenne_activites:.0f}%" if progression_moyenne_activites is not None else "—", progress_percent=progression_moyenne_activites), unsafe_allow_html=True)
    vue_cols[1].markdown(kpi_card_html("🔢", "Indicateurs suivis", str(len(indicateurs_liste))), unsafe_allow_html=True)
    vue_cols[2].markdown(kpi_card_html("🟢", "Atteints", str(nb_atteints)), unsafe_allow_html=True)

    if avec_cible:
        st.write("")
        st.markdown(f"**Taux global de réalisation des indicateurs : {taux_global:.0f}%**")
        st.progress(min(int(taux_global), 100))

    # ------------------------------------------------------------------------
    # 2. Analyse par objectif
    # ------------------------------------------------------------------------
    if indicateurs_liste:
        st.write("")
        st.markdown("**🎯 Analyse par objectif**")
        objectifs_groupes = {}
        for ind in indicateurs_liste:
            objectifs_groupes.setdefault(ind["objectif"] or "Sans objectif", []).append(ind)

        for objectif_nom, inds in objectifs_groupes.items():
            inds_avec_cible = [i for i in inds if i["statut"][3] is not None]
            pct_objectif = (sum(i["statut"][3] for i in inds_avec_cible) / len(inds_avec_cible)) if inds_avec_cible else None
            icone_obj, kind_obj, label_obj, _ = _statut_indicateur(pct_objectif, 100) if pct_objectif is not None else ("⚪", "muted", "Non mesuré", None)

            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{objectif_nom}**")
                with c2:
                    if pct_objectif is not None:
                        st.markdown(badge_html(f"{icone_obj} {pct_objectif:.0f}%", kind_obj), unsafe_allow_html=True)
                for ind in inds:
                    icone, kind, label, pct = ind["statut"]
                    txt_pct = f"{pct:.0f}%" if pct is not None else "—"
                    st.caption(f"{icone} {ind['nom']} — {txt_pct}")

    # ------------------------------------------------------------------------
    # 3. Graphique global — progression normalisée en % de la cible, un seul
    # graphique, une seule barre par indicateur (comparable même quand les
    # échelles diffèrent énormément — tonnes/ha, alertes, FCFA/kg...)
    # ------------------------------------------------------------------------
    indicateurs_avec_donnees = [i for i in indicateurs_liste if i["cible"]]
    if indicateurs_avec_donnees:
        st.write("")
        st.markdown("**📐 Progression vers la cible**")
        st.caption("Chaque barre = l'avancement actuel en % de la cible (100% = cible atteinte). Le repère ⚪ indique le point de départ (baseline).")

        noms = [truncate_label(i["nom"]) for i in indicateurs_avec_donnees]
        noms_complets = [i["nom"] for i in indicateurs_avec_donnees]
        pct_actuel = [min((i["actuelle"] or 0) / i["cible"] * 100, 130) for i in indicateurs_avec_donnees]
        pct_baseline = [(i["baseline"] or 0) / i["cible"] * 100 for i in indicateurs_avec_donnees]
        couleurs = [i["statut"][1] for i in indicateurs_avec_donnees]
        couleur_map = {"success": "#10B981", "muted": "#2563EB", "warning": "#F59E0B", "danger": "#EF4444"}
        couleurs_hex = [couleur_map.get(c, "#2563EB") for c in couleurs]
        textes = [f"{i['actuelle'] or 0:,.0f}/{i['cible']:,.0f} {i['unite']}".replace(",", " ") for i in indicateurs_avec_donnees]

        fig_evolution = go.Figure()
        fig_evolution.add_trace(go.Bar(
            x=pct_actuel, y=noms, orientation="h",
            marker_color=couleurs_hex, text=textes, textposition="outside",
            showlegend=False,  # légende gérée séparément ci-dessous (couleurs multiples par statut)
            customdata=noms_complets, hovertemplate="<b>%{customdata}</b><br>%{x:.0f}% de la cible<extra></extra>",
        ))
        fig_evolution.add_trace(go.Scatter(
            x=pct_baseline, y=noms, mode="markers", marker=dict(symbol="circle", size=10, color="white", line=dict(color="#94A3B8", width=2)),
            name="Baseline (point de départ)", hoverinfo="skip",
        ))
        fig_evolution.add_vline(x=100, line_dash="dash", line_color="#94A3B8", annotation_text="Cible (100%)", annotation_position="top")

        # Légende par statut — une entrée par couleur réellement utilisée dans les barres,
        # avec le même seuil que le reste de l'application (cohérence globale)
        legende_statuts = [
            ("success", "#10B981", "🟢 ≥ 100% (cible atteinte)"),
            ("muted", "#2563EB", "🔵 60-99% (bonne progression)"),
            ("warning", "#F59E0B", "🟠 30-59% (attention)"),
            ("danger", "#EF4444", "🔴 < 30% (critique)"),
        ]
        for kind, couleur, label in legende_statuts:
            if kind in couleurs:  # n'affiche que les statuts réellement présents dans le graphique
                fig_evolution.add_trace(go.Bar(x=[None], y=[None], marker_color=couleur, name=label, showlegend=True))

        style_plotly_chart(fig_evolution)
        fig_evolution.update_layout(
            margin=dict(l=10, r=10, t=30, b=10), height=max(220, 32 * len(indicateurs_avec_donnees)),
            xaxis_title="% de la cible atteint", yaxis_title="", showlegend=True,
            yaxis=dict(automargin=True, tickfont=dict(size=11)),
        )
        st.plotly_chart(fig_evolution, use_container_width=True)

    # ------------------------------------------------------------------------
    # 4. Détails complets — repliés
    # ------------------------------------------------------------------------
    if indicateurs_liste:
        with st.expander("🔍 Voir le détail de tous les indicateurs"):
            for i in range(0, len(indicateurs_liste), 4):
                ligne = indicateurs_liste[i:i + 4]
                cols_kpi = st.columns(4)
                for col, ind in zip(cols_kpi, ligne):
                    icone, kind, label, pct = ind["statut"]
                    valeur_affichee = f"{(ind['actuelle'] or 0):,.0f}/{(ind['cible'] or 0):,.0f} {ind['unite']}".replace(",", " ").strip()
                    with col:
                        st.markdown(kpi_card_html(icone, ind["nom"], valeur_affichee, progress_percent=pct), unsafe_allow_html=True)
                        if ind["baseline"] is not None:
                            st.caption(f"Baseline : {ind['baseline']}")
                        st.markdown(badge_html(label, kind), unsafe_allow_html=True)

    # ------------------------------------------------------------------------
    # 5. Indicateurs par calendrier — basé sur la ventilation temporelle, pas
    # uniquement le taux final. Un indicateur sans ventilation configurée
    # n'apparaît simplement pas ici (rien à comparer dans le temps).
    # ------------------------------------------------------------------------
    toutes_periodes_df = crud.get_toutes_periodes_projet(selected_projet_id)
    if not toutes_periodes_df.empty:
        st.write("")
        st.markdown("**📅 Indicateurs par calendrier**")
        st.caption("Basé sur les cibles périodiques renseignées (ventilation temporelle) — comparaison cumulée, pas le taux final brut.")

        resultats_calendrier = []
        for cle, groupe in toutes_periodes_df.groupby("indicateur_key"):
            periodes_ind = groupe.rename(columns={"periode_label": "label"}).to_dict("records")
            periodes_calc_ind = indicateurs_temporels.calculer_statuts_cumules(sorted(periodes_ind, key=lambda p: p["date_debut"]))
            derniere = periodes_calc_ind[-1]
            # Le statut affiché est celui de la dernière période déjà commencée (pas future)
            periodes_commencees = [p for p in periodes_calc_ind if p["statut"] != "À venir"]
            statut_actuel = periodes_commencees[-1] if periodes_commencees else derniere
            resultats_calendrier.append({
                "nom": groupe.iloc[0]["nom_indicateur"], "statut": statut_actuel["statut"],
                "ecart": statut_actuel["ecart"], "cible_cumulee": statut_actuel["cible_cumulee"],
                "realise_cumule": statut_actuel["realise_cumule"],
            })

        comptage = {"Conforme": 0, "En avance": 0, "En retard": 0, "Critique": 0, "À venir": 0}
        for r in resultats_calendrier:
            comptage[r["statut"]] = comptage.get(r["statut"], 0) + 1

        cal_cols = st.columns(4)
        cal_cols[0].markdown(kpi_card_html("🟢", "Conforme", str(comptage["Conforme"] + comptage["En avance"])), unsafe_allow_html=True)
        cal_cols[1].markdown(kpi_card_html("🟠", "En retard", str(comptage["En retard"])), unsafe_allow_html=True)
        cal_cols[2].markdown(kpi_card_html("🔴", "Retard critique", str(comptage["Critique"])), unsafe_allow_html=True)
        cal_cols[3].markdown(kpi_card_html("🔵", "À venir", str(comptage["À venir"])), unsafe_allow_html=True)

        indicateurs_en_retard = sorted(
            [r for r in resultats_calendrier if r["statut"] in ("En retard", "Critique")],
            key=lambda r: r["ecart"],
        )
        if indicateurs_en_retard:
            st.write("")
            st.markdown("**Indicateurs les plus en retard**")
            for r in indicateurs_en_retard[:5]:
                badge_kind = "danger" if r["statut"] == "Critique" else "warning"
                st.markdown(
                    f"{badge_html(r['statut'], badge_kind)} **{r['nom']}** — cible cumulée : {r['cible_cumulee']:.1f}, "
                    f"réalisé : {r['realise_cumule']:.1f} (écart : {r['ecart']:+.1f})",
                    unsafe_allow_html=True,
                )

st.write("")

# ----------------------------------------------------------------------------
# Graphiques — configurables directement sur cette page (admin)
# ----------------------------------------------------------------------------
indicateurs_config = load_visible_indicators()
graphiques = indicateurs_config[indicateurs_config["type_element"] == "graphique"]

st.write("")

if is_admin:
    with st.expander("⚙️ Choisir les graphiques affichés (visible par toute l'équipe)"):
        st.caption(
            "Les indicateurs clés (KPI) ne se configurent plus ici — ils sont désormais automatiques, "
            "dérivés directement des indicateurs définis dans chaque projet (section Résultats)."
        )
        df_indic_all = load_all_indicators()
        subset = df_indic_all[df_indic_all["type_element"] == "graphique"]

        if subset.empty:
            st.caption("Aucun graphique configurable.")
        else:
            with st.form("form_dashboard_graphique"):
                updated_rows = []
                for _, row in subset.iterrows():
                    cols = st.columns([0.6, 3.4, 1.2, 1.8])
                    visible = cols[0].checkbox("Actif", value=bool(row["visible"]), key=f"dash_visible_{row['id']}", label_visibility="collapsed")
                    cols[1].write(f"{row['icone'] or ''} {row['libelle']}")
                    ordre = cols[2].number_input("Ordre", value=int(row["ordre"]), min_value=0, max_value=100, step=1, key=f"dash_ordre_{row['id']}", label_visibility="collapsed")
                    badge_kind = "success" if row["visible"] else "muted"
                    cols[3].markdown(badge_html("Actif" if row["visible"] else "Masqué", badge_kind), unsafe_allow_html=True)
                    updated_rows.append((row["id"], visible, ordre))

                if st.form_submit_button("💾 Enregistrer", use_container_width=True):
                    for indicateur_id, visible, ordre in updated_rows:
                        update_indicator(indicateur_id, visible, ordre)
                    st.cache_data.clear()
                    st.toast("✅ Configuration enregistrée avec succès.")
                    st.rerun()

st.divider()

# ----------------------------------------------------------------------------
# Graphiques du projet sélectionné
# ----------------------------------------------------------------------------
if not graphiques.empty:
    for _, row in graphiques.iterrows():
        section_title(row["icone"] or "", row["libelle"])

        if row["cle"] == "graph_budget_projet":
            activites_avec_budget = activites_df[activites_df["budget"].notna() & (activites_df["budget"] > 0)] if not activites_df.empty else activites_df
            if not activites_avec_budget.empty:
                nb_sans_budget = len(activites_df) - len(activites_avec_budget)
                activites_avec_budget = activites_avec_budget.copy()
                activites_avec_budget["titre_court"] = activites_avec_budget["titre"].apply(truncate_label)
                activites_avec_budget = activites_avec_budget.sort_values("budget", ascending=True)
                fig = px.bar(
                    activites_avec_budget,
                    x="budget", y="titre_court", orientation="h",
                    text_auto=",.0f", color_discrete_sequence=["#2563EB"],
                )
                fig.update_traces(hoverinfo="skip", hovertemplate=None)  # le survol se fait via la couche invisible ci-dessous
                max_budget = activites_avec_budget["budget"].max()
                fig.add_trace(go.Bar(
                    x=[max_budget * 1.001] * len(activites_avec_budget), y=activites_avec_budget["titre_court"],
                    orientation="h", marker=dict(color="rgba(0,0,0,0)"),
                    customdata=activites_avec_budget[["titre", "budget"]],
                    hovertemplate="<b>%{customdata[0]}</b><br>Budget : %{customdata[1]:,.0f} FCFA<extra></extra>",
                    showlegend=False,
                ))
                fig.update_layout(barmode="overlay")
                style_plotly_chart(fig)
                fig.update_layout(
                    xaxis_title="Budget (FCFA)", yaxis_title="",
                    margin=dict(l=10, r=10, t=40, b=10), height=max(280, 32 * len(activites_avec_budget)),
                    yaxis=dict(automargin=True, tickfont=dict(size=11)),
                )
                st.plotly_chart(fig, use_container_width=True)
                if nb_sans_budget > 0:
                    st.caption(f"ℹ️ {nb_sans_budget} activité(s) sans budget renseigné, non affichée(s) ci-dessus.")
            else:
                st.info("Aucune activité avec budget pour ce projet.")

        elif row["cle"] == "graph_progression_projet":
            if not activites_df.empty and "progression" in activites_df.columns:
                activites_prog = activites_df.copy()
                activites_prog["titre_court"] = activites_prog["titre"].apply(truncate_label)
                activites_prog = activites_prog.sort_values("progression", ascending=True)
                fig = px.bar(
                    activites_prog,
                    x="progression", y="titre_court", orientation="h",
                    text_auto=".0f", color="progression",
                    color_continuous_scale=["#F59E0B", "#10B981"], range_color=[0, 100],
                )
                fig.update_traces(hoverinfo="skip", hovertemplate=None)
                fig.add_trace(go.Bar(
                    x=[101] * len(activites_prog), y=activites_prog["titre_court"],
                    orientation="h", marker=dict(color="rgba(0,0,0,0)"),
                    customdata=activites_prog[["titre", "progression"]],
                    hovertemplate="<b>%{customdata[0]}</b><br>Progression : %{customdata[1]:.0f}%<extra></extra>",
                    showlegend=False,
                ))
                fig.update_layout(barmode="overlay")
                style_plotly_chart(fig)
                fig.update_layout(
                    xaxis_title="Progression (%)", yaxis_title="",
                    margin=dict(l=10, r=10, t=40, b=10), height=max(280, 32 * len(activites_prog)),
                    coloraxis_showscale=False,
                    yaxis=dict(automargin=True, tickfont=dict(size=11)),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune activité pour ce projet.")

        st.write("")

# ----------------------------------------------------------------------------
# Diagramme de Gantt — planification des activités, avec chemin critique
# ----------------------------------------------------------------------------
section_title("📅", "Planification (Gantt)")

gantt_df = activites_df.dropna(subset=["date_debut", "date_fin"]) if not activites_df.empty else activites_df

if gantt_df.empty:
    st.info("Ajoutez des dates de début/fin à vos activités pour voir apparaître la planification ici.")
else:
    gantt_df = gantt_df.copy()
    gantt_df["date_debut"] = pd.to_datetime(gantt_df["date_debut"])
    gantt_df["date_fin"] = pd.to_datetime(gantt_df["date_fin"])
    gantt_df = gantt_df.sort_values("date_debut")  # ordre chronologique, pour suivre visuellement l'enchaînement

    chemin_critique_ids = critical_path.compute_critical_path(activites_df)
    gantt_df["chemin"] = gantt_df["id"].apply(lambda x: "🔴 Chemin critique" if x in chemin_critique_ids else "Autres activités")
    gantt_df["titre_court"] = gantt_df["titre"].apply(truncate_label)

    tip("gantt_chemin_critique", "Le chemin critique (en rouge) est la séquence d'activités qui détermine la durée totale du projet — tout retard sur l'une d'elles retarde le projet entier. Renseignez le champ « Dépend de » sur vos activités pour le faire apparaître.")

    fig_gantt = px.timeline(
        gantt_df, x_start="date_debut", x_end="date_fin", y="titre_court",
        color="chemin", color_discrete_map={
            "🔴 Chemin critique": "#EF4444", "Autres activités": "#93C5FD",
        },
        category_orders={"titre_court": gantt_df["titre_court"].tolist()},
        custom_data=["titre", "statut"],
    )
    fig_gantt.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Statut : %{customdata[1]}<br>%{base|%d/%m/%Y} → %{x|%d/%m/%Y}<extra></extra>")
    fig_gantt.update_yaxes(autorange="reversed", title="", automargin=True, tickfont=dict(size=11))
    style_plotly_chart(fig_gantt)
    fig_gantt.update_layout(
        margin=dict(l=10, r=10, t=40, b=10), height=max(200, 32 * len(gantt_df)),
        legend_title="",
    )
    st.plotly_chart(fig_gantt, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# Performance des responsables
# ----------------------------------------------------------------------------
section_title("🏆", "Performance des responsables")
tip(
    "performance_responsables",
    "La performance d'un responsable est la moyenne de la progression de toutes ses activités "
    "assignées dans ce projet. Les responsables sans activité ne sont pas affichés. ⚠️ Un score bas "
    "ne signifie pas forcément une sous-performance : il peut simplement refléter des activités dont "
    "la période n'a pas encore commencé (donc à 0% par nature, pas par retard). Comparez toujours ce "
    "score aux dates prévues des activités avant d'en tirer une conclusion."
)

perf_df = crud.get_performance_responsables(selected_projet_id)

if perf_df.empty:
    st.info("Aucun responsable n'a d'activité assignée pour l'instant dans ce projet.")
else:
    perf_df = perf_df.sort_values("performance_moyenne", ascending=True)
    perf_df["performance_moyenne"] = perf_df["performance_moyenne"].round(1)
    perf_df["responsable_court"] = perf_df["responsable"].apply(truncate_label)

    fig_perf = px.bar(
        perf_df, x="performance_moyenne", y="responsable_court", orientation="h",
        text_auto=".0f", color_discrete_sequence=["#2563EB"],
        custom_data=["responsable", "nb_activites", "nb_terminees", "nb_en_cours", "nb_en_retard", "nb_a_venir"],
    )
    fig_perf.update_traces(textposition="outside")  # sans ça, une barre à 0% n'affiche aucune étiquette
    fig_perf.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Performance moyenne : %{x:.0f}%<br>"
            "Activités assignées : %{customdata[1]}<br>"
            "Terminées : %{customdata[2]} · En cours : %{customdata[3]}<br>"
            "En retard : %{customdata[4]} · Pas encore commencées : %{customdata[5]}"
            "<extra></extra>"
        )
    )
    style_plotly_chart(fig_perf)
    fig_perf.update_layout(
        xaxis_title="Performance moyenne (%)", yaxis_title="",
        xaxis_range=[0, 112],
        margin=dict(l=10, r=10, t=20, b=10), height=max(200, 32 * len(perf_df)),
        showlegend=False,
        yaxis=dict(automargin=True, tickfont=dict(size=11)),
    )
    st.plotly_chart(fig_perf, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# Détail lisible du projet sélectionné (activités)
# ----------------------------------------------------------------------------
section_title("📋", f"Détail des activités — {projet_row['nom']}")

if activites_df.empty:
    st.info("Aucune activité pour ce projet.")
else:
    st.dataframe(
        activites_df[["titre", "statut", "progression", "budget", "date_debut", "date_fin", "responsable"]].rename(
            columns={"titre": "Activité", "statut": "Statut", "progression": "Progression (%)",
                     "budget": "Budget (FCFA)", "date_debut": "Début", "date_fin": "Fin", "responsable": "Responsable"}
        ),
        use_container_width=True, hide_index=True,
        column_config={
            "Budget (FCFA)": st.column_config.NumberColumn(format="%,.0f"),
            "Progression (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
        },
    )

st.divider()

# ----------------------------------------------------------------------------
# Export pour analyse externe (Excel, Power BI, etc.) — toujours sur l'ensemble des projets
# ----------------------------------------------------------------------------
section_title("📥", "Exporter pour Excel / Power BI")
st.caption(
    "Téléchargez les données de tous vos projets sous forme de tables reliées (par identifiants), "
    "prêtes à être importées dans Excel, Power BI ou tout autre outil d'analyse."
)

if st.button("📥 Générer l'export (ZIP de fichiers CSV)", type="primary"):
    import io
    import zipfile

    tables = {
        "projets.csv": crud.export_projets(),
        "objectifs.csv": crud.export_objectifs(),
        "resultats.csv": crud.export_resultats(),
        "activites.csv": crud.export_activites(),
        "taches.csv": crud.export_taches(),
        "indicateurs.csv": crud.export_indicateurs(),
        "depenses.csv": crud.export_depenses(),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, table_df in tables.items():
            zf.writestr(filename, table_df.to_csv(index=False))
    st.session_state["export_analyse_externe"] = buffer.getvalue()

if "export_analyse_externe" in st.session_state:
    st.download_button(
        "⬇️ Télécharger l'export (.zip)",
        data=st.session_state["export_analyse_externe"],
        file_name="suiviprojets_export.zip",
        mime="application/zip",
    )

with st.expander("ℹ️ Comment utiliser cet export"):
    st.markdown("""
**Dans Excel :**
1. Décompressez le fichier `.zip` téléchargé.
2. Ouvrez chaque fichier `.csv` directement dans Excel (double-clic), ou importez-les via **Données → À partir d'un fichier texte/CSV**.
3. Pour relier les tables entre elles, utilisez les colonnes d'identifiants (`projet_id`, `objectif_id`, etc.) avec RECHERCHEV ou le modèle de données Excel (Power Pivot).

**Dans Power BI :**
1. Décompressez le fichier `.zip` téléchargé.
2. **Accueil → Obtenir les données → Texte/CSV**, importez les 6 fichiers un par un.
3. Dans **Gérer les relations**, reliez les tables par leurs colonnes d'identifiants.
4. Construisez vos visuels normalement — toutes les tables sont désormais reliées.
    """)