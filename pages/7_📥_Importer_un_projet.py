import streamlit as st
from auth import require_login
from ui_style import sidebar_brand, section_title, tip
import crud
import ai_project_import as api

require_login()
sidebar_brand()

st.title("📥 Importer un projet depuis un document")
st.caption("Déposez un document Word ou PDF décrivant un projet — l'IA en extrait automatiquement les objectifs, résultats, activités et budget, que vous pourrez vérifier et corriger avant l'import définitif.")
st.divider()

tip(
    "import_ia_verification",
    "⚠️ Vérifiez toujours attentivement ce que l'IA a extrait avant de créer le projet — en particulier les "
    "chiffres (budget, cibles d'indicateurs). L'IA a pour consigne de ne jamais inventer une valeur absente du "
    "document, mais une relecture humaine reste indispensable avant tout enregistrement définitif.",
)

# ----------------------------------------------------------------------------
# Étape 1 — Dépôt du document
# ----------------------------------------------------------------------------
section_title("1️⃣", "Déposer le document")

uploaded_file = st.file_uploader("Document de projet (.docx ou .pdf)", type=["docx", "pdf"])

if uploaded_file and st.button("🤖 Analyser avec l'IA", type="primary"):
    with st.spinner("Lecture du document et extraction en cours..."):
        try:
            texte = api.extraire_texte_document(uploaded_file)
            extraction = api.extraire_structure_projet(texte)
            st.session_state["import_extraction"] = extraction
            st.session_state.pop("import_termine", None)
            st.toast("✅ Extraction terminée — vérifiez les informations ci-dessous avant de créer le projet.")
        except (RuntimeError, ValueError) as e:
            st.error(str(e))
            if "import_derniere_reponse_brute" in st.session_state:
                with st.expander("🔍 Voir la réponse brute de l'IA (pour diagnostic)"):
                    st.code(st.session_state["import_derniere_reponse_brute"], language="text")
        except Exception as e:
            st.error(f"Erreur inattendue lors de l'extraction : {e}")

# ----------------------------------------------------------------------------
# Étape 2 — Vérification et correction (obligatoire avant tout import)
# ----------------------------------------------------------------------------
if "import_extraction" in st.session_state and not st.session_state.get("import_termine"):
    extraction = st.session_state["import_extraction"]

    st.divider()
    section_title("2️⃣", "Vérifier et corriger avant l'import")
    st.warning("Rien n'est encore enregistré. Corrigez les champs ci-dessous si nécessaire, puis validez en bas de page.")

    with st.container(border=True):
        st.markdown("**📁 Informations générales du projet**")
        p = extraction["projet"]
        p["nom"] = st.text_input("Nom du projet", value=p.get("nom") or "")
        p["description"] = st.text_area("Description", value=p.get("description") or "", height=100)
        pc1, pc2, pc3, pc4 = st.columns(4)
        date_debut_str = pc1.text_input("Date de début (AAAA-MM-JJ)", value=p.get("date_debut") or "")
        date_fin_str = pc2.text_input("Date de fin (AAAA-MM-JJ)", value=p.get("date_fin") or "")
        budget_val = pc3.number_input("Budget", value=float(p.get("budget") or 0), step=1000.0)
        devise_val = pc4.text_input("Devise", value=p.get("devise") or "FCFA")
        p["date_debut"] = date_debut_str or None
        p["date_fin"] = date_fin_str or None
        p["budget"] = budget_val or None
        p["devise"] = devise_val or None

    st.write("")
    st.markdown("**🎯 Objectif général**")
    st.caption("Unique, énoncé de haut niveau — ne porte pas de résultats directement.")
    objectif_general = extraction.setdefault("objectif_general", {})
    objectif_general["titre"] = st.text_input("Titre de l'objectif général", value=objectif_general.get("titre") or "")
    objectif_general["description"] = st.text_area("Description", value=objectif_general.get("description") or "", height=68)

    st.write("")
    objectifs = extraction.setdefault("objectifs_specifiques", [])
    if not objectifs:
        st.info("Aucun objectif spécifique n'a pu être extrait — vous pourrez en ajouter manuellement après la création du projet.")

    objectifs_a_supprimer = []
    for i_obj, obj in enumerate(objectifs):
        with st.container(border=True):
            col_obj1, col_obj2 = st.columns([5, 1])
            with col_obj1:
                obj["titre"] = st.text_input(f"Objectif spécifique {i_obj + 1} — Titre", value=obj.get("titre") or "", key=f"obj_titre_{i_obj}")
                obj["description"] = st.text_area("Description", value=obj.get("description") or "", key=f"obj_desc_{i_obj}", height=68)
            with col_obj2:
                st.write("")
                st.write("")
                if st.button("🗑️ Retirer", key=f"del_obj_{i_obj}"):
                    objectifs_a_supprimer.append(i_obj)

            resultats = obj.get("resultats", [])
            resultats_a_supprimer = []
            for i_res, res in enumerate(resultats):
                st.markdown(f"　**↳ Résultat {i_res + 1}**")
                rc1, rc2 = st.columns([5, 1])
                with rc1:
                    res["titre"] = st.text_input("Titre du résultat", value=res.get("titre") or "", key=f"res_titre_{i_obj}_{i_res}")
                    res["description"] = st.text_area("Description", value=res.get("description") or "", key=f"res_desc_{i_obj}_{i_res}", height=68)
                    rcc1, rcc2, rcc3, rcc4 = st.columns(4)
                    res["indicateur"] = rcc1.text_input("Indicateur", value=res.get("indicateur") or "", key=f"res_ind_{i_obj}_{i_res}")
                    res["baseline"] = rcc2.number_input("Baseline", value=float(res.get("baseline") or 0), key=f"res_base_{i_obj}_{i_res}")
                    res["valeur_cible"] = rcc3.number_input("Cible", value=float(res.get("valeur_cible") or 0), key=f"res_cible_{i_obj}_{i_res}")
                    res["unite"] = rcc4.text_input("Unité", value=res.get("unite") or "", key=f"res_unite_{i_obj}_{i_res}")
                with rc2:
                    st.write("")
                    if st.button("🗑️", key=f"del_res_{i_obj}_{i_res}"):
                        resultats_a_supprimer.append(i_res)

                activites = res.get("activites", [])
                activites_a_supprimer = []
                for i_act, act in enumerate(activites):
                    st.markdown(f"　　**↳↳ Activité {i_act + 1}**")
                    ac1, ac2 = st.columns([5, 1])
                    with ac1:
                        act["titre"] = st.text_input("Titre de l'activité", value=act.get("titre") or "", key=f"act_titre_{i_obj}_{i_res}_{i_act}")
                        acc1, acc2, acc3 = st.columns(3)
                        act["date_debut"] = acc1.text_input("Début (AAAA-MM-JJ)", value=act.get("date_debut") or "", key=f"act_debut_{i_obj}_{i_res}_{i_act}") or None
                        act["date_fin"] = acc2.text_input("Fin (AAAA-MM-JJ)", value=act.get("date_fin") or "", key=f"act_fin_{i_obj}_{i_res}_{i_act}") or None
                        act["budget"] = acc3.number_input("Budget", value=float(act.get("budget") or 0), key=f"act_budget_{i_obj}_{i_res}_{i_act}") or None
                    with ac2:
                        st.write("")
                        if st.button("🗑️", key=f"del_act_{i_obj}_{i_res}_{i_act}"):
                            activites_a_supprimer.append(i_act)

                for idx in sorted(activites_a_supprimer, reverse=True):
                    activites.pop(idx)

            for idx in sorted(resultats_a_supprimer, reverse=True):
                resultats.pop(idx)

    for idx in sorted(objectifs_a_supprimer, reverse=True):
        objectifs.pop(idx)

    st.divider()
    section_title("3️⃣", "Créer le projet")
    st.caption("Cette étape écrit définitivement les données ci-dessus dans la base — vérifiez une dernière fois avant de valider.")

    if st.button("✅ Créer le projet avec ces données", type="primary", use_container_width=True):
        try:
            nouveau_projet_id = crud.create_projet_depuis_extraction(extraction)
            if st.session_state.get("user", {}).get("compte_restreint"):
                crud.grant_acces_restreint(st.session_state["user"]["id"], nouveau_projet_id)
            st.session_state["import_termine"] = True
            st.session_state.pop("import_extraction", None)
            st.success(f"✅ Projet créé avec succès ! Rendez-vous dans **📂 Mes projets** pour le retrouver et compléter les détails restants (responsables, tâches, budget détaillé...).")
        except Exception as e:
            st.error(f"Erreur lors de la création du projet : {e}")