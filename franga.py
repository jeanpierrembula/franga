import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import io
import requests
from database import (add_transaction, get_all_transactions, update_transaction, delete_transaction,
                      add_user, get_user_by_username, add_budget, get_budgets,
                      add_reminder, get_reminders, close_session)

# Initialisation des clés de session pour l'authentification et les transactions
st.session_state.setdefault("user", None)
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("transactions", [])
# Les budgets et rappels seront persistés en BDD

# Fonction de récupération du taux de change via l'API avec cache
@st.cache_data(ttl=3600)
def get_exchange_rate(currency):
    try:
        response = requests.get('https://v6.exchangerate-api.com/v6/9e26924cca88ef6262e60a6b/latest/USD')
        data = response.json()
        rate = data['conversion_rates'].get(currency)
        if rate:
            return rate
        else:
            raise ValueError("Devise non trouvée dans l'API.")
    except Exception as e:
        fallback = {"USD": 1, "CDF": 2800, "EUR": 1.1, "GBP": 1.3}
        return fallback.get(currency, 1)

# Liste prédéfinie de catégories
CATEGORIES = ["Alimentation", "Logement", "Transport", "Loisirs", "Santé", "Salaire", "Prime", "Autres Activité", "Quinzaine"]

def transaction_to_dict(t):
    return {
        "id": t.id,
        "date": t.date,
        "type": t.type,
        "amount": t.amount,
        "amount_usd": t.amount_usd,
        "currency": t.currency,
        "category": t.category,
        "description": t.description,
        "exchange_rate": t.exchange_rate,
        "source": "manuel"
    }

# CSS étendu avec une palette orange pour un look moderne et équilibré
st.markdown("""
    <style>
    /* Global Reset et Base */
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background-color: #f0f2f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
    img { max-width: 100%; height: auto; }
    a { color: #FF6600; text-decoration: none; transition: color 0.3s ease; }
    a:hover { color: #E65C00; }
    /* Mise en page centrale */
    .reportview-container .main .block-container { max-width: 1200px; margin: auto; padding: 2rem 1rem; }
    /* Header */
    header { background-color: #FF6600; color: #fff; padding: 2rem; text-align: center; border-bottom: 4px solid #E65C00; }
    header h1 { font-size: 3rem; margin-bottom: 0.5rem; }
    header p { font-size: 1.2rem; }
    /* Sidebar */
    .sidebar .sidebar-content { background: linear-gradient(135deg, #FF6600, #E65C00); padding: 2rem; border-radius: 8px; }
    .sidebar .sidebar-content h2 { color: #fff; font-size: 1.8rem; margin-bottom: 1rem; text-align: center; }
    /* Footer */
    footer { background: #f0f2f6; color: #666; text-align: center; padding: 1rem; border-top: 1px solid #ddd; margin-top: 2rem; }
    /* Boutons */
    .stButton > button { background-color: #FF6600; color: #fff; border: none; border-radius: 5px; padding: 0.8rem 1.5rem; font-size: 1rem; cursor: pointer; transition: background 0.3s ease; }
    .stButton > button:hover { background-color: #E65C00; }
    /* Formulaires */
    form { background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-bottom: 2rem; }
    label { font-weight: bold; margin-bottom: 0.5rem; display: block; }
    input[type="text"], input[type="password"], input[type="number"], textarea, select {
        width: 100%; padding: 0.8rem; margin-bottom: 1.2rem; border: 1px solid #ccc; border-radius: 4px;
        transition: border-color 0.3s ease;
    }
    input:focus, textarea:focus, select:focus { border-color: #FF6600; outline: none; }
    /* Cartes */
    .wallet-card, .card { background: #fff; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.3s ease; }
    .wallet-card:hover, .card:hover { transform: translateY(-5px); }
    .card h3 { font-size: 1.8rem; margin-bottom: 1rem; color: #FF6600; }
    .card p { font-size: 1rem; color: #333; }
    /* Tables */
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th, td { padding: 1rem; border: 1px solid #ddd; text-align: left; }
    th { background-color: #FF6600; color: #fff; }
    /* Navigation */
    nav { background: #fff; padding: 1rem; border-bottom: 2px solid #f0f0f0; margin-bottom: 2rem; }
    nav a { margin-right: 1.5rem; color: #FF6600; font-weight: bold; transition: color 0.3s; }
    nav a:hover { color: #E65C00; }
    /* Progress Bars */
    .progress-container { margin: 1rem 0; }
    .progress-bar { background-color: #FF6600; height: 20px; border-radius: 10px; }
    .progress-label { font-size: 0.9rem; color: #333; text-align: right; padding-right: 5px; }
    /* Grille de cartes */
    .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
    /* Modales */
    .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); }
    .modal.show { display: block; }
    .modal-content { background: #fff; margin: 10% auto; padding: 2rem; border-radius: 8px; width: 80%; max-width: 500px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .modal-header { border-bottom: 1px solid #ddd; margin-bottom: 1rem; }
    .modal-title { font-size: 1.5rem; }
    .modal-body { font-size: 1rem; }
    .modal-footer { border-top: 1px solid #ddd; margin-top: 1rem; text-align: right; }
    /* Alertes */
    .alert { padding: 1rem; border-radius: 4px; margin: 1rem 0; }
    .alert-success { background: #d4edda; color: #155724; }
    .alert-danger { background: #f8d7da; color: #721c24; }
    .alert-info { background: #d1ecf1; color: #0c5460; }
    /* Utilitaires */
    .text-center { text-align: center; }
    .text-right { text-align: right; }
    .fw-bold { font-weight: bold; }
    .mt-1 { margin-top: 1rem; }
    .mt-2 { margin-top: 2rem; }
    .mt-3 { margin-top: 3rem; }
    .mb-1 { margin-bottom: 1rem; }
    .mb-2 { margin-bottom: 2rem; }
    .mb-3 { margin-bottom: 3rem; }
    .px-1 { padding-left: 1rem; padding-right: 1rem; }
    .px-2 { padding-left: 2rem; padding-right: 2rem; }
    .py-1 { padding-top: 1rem; padding-bottom: 1rem; }
    .py-2 { padding-top: 2rem; padding-bottom: 2rem; }
    .rounded { border-radius: 8px; }
    .shadow { box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .transition { transition: all 0.3s ease; }
    .hover-scale:hover { transform: scale(1.02); }
    /* Grille et Flex */
    .d-flex { display: flex; }
    .flex-column { flex-direction: column; }
    .flex-row { flex-direction: row; }
    .justify-center { justify-content: center; }
    .justify-between { justify-content: space-between; }
    .align-center { align-items: center; }
    .flex-wrap { flex-wrap: wrap; }
    .gap-1 { gap: 1rem; }
    .gap-2 { gap: 2rem; }
    /* Typographie */
    .fs-large { font-size: 1.5rem; }
    .fs-medium { font-size: 1.2rem; }
    .fs-small { font-size: 0.9rem; }
    .text-uppercase { text-transform: uppercase; }
    .text-lowercase { text-transform: lowercase; }
    .text-capitalize { text-transform: capitalize; }
    /* Espacement */
    .m-0 { margin: 0; }
    .p-0 { padding: 0; }
    .m-auto { margin: auto; }
    .p-auto { padding: auto; }
    /* Responsive */
    @media (max-width: 768px) {
        .reportview-container .main .block-container { padding: 1rem; }
        header h1 { font-size: 2.5rem; }
        .sidebar .sidebar-content { padding: 1.5rem; }
        .card-container { grid-template-columns: 1fr; }
    }
    /* Extra Détails */
    .input-error { border-color: #f44336; }
    .error-text { color: #f44336; font-size: 0.9rem; }
    .success-text { color: #4caf50; font-size: 0.9rem; }
    .underline { text-decoration: underline; }
    .line-through { text-decoration: line-through; }
    .cursor-pointer { cursor: pointer; }
    .bg-gradient { background: linear-gradient(135deg, #FF6600, #E65C00); }
    .border-dashed { border: 1px dashed #ccc; }
    .border-dotted { border: 1px dotted #ccc; }
    .outline-none { outline: none; }
    .z-index-high { z-index: 9999; }
    .custom-scrollbar::-webkit-scrollbar { width: 8px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #888; border-radius: 10px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #555; }
    .text-shadow { text-shadow: 1px 1px 2px rgba(0,0,0,0.2); }
    .modal-backdrop { background: rgba(0, 0, 0, 0.5); }
    </style>
""", unsafe_allow_html=True)

# --- Interface de connexion / inscription ---
def login_page():
    st.sidebar.title("Connexion / Inscription")
    auth_mode = st.sidebar.radio("Choisir", ["Connexion", "Inscription"])
    if auth_mode == "Connexion":
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter")
            if submitted:
                user = get_user_by_username(username)
                if user:
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    if pwd_context.verify(password, user.password):
                        st.session_state.user = username
                        st.session_state.user_id = user.id
                        st.success("Connecté !")
                        transactions_db = get_all_transactions(user_id=st.session_state.user_id)
                        st.session_state.transactions = [transaction_to_dict(t) for t in transactions_db]
                        st.rerun()  # Redirection immédiate vers l'interface principale
                    else:
                        st.error("Nom d'utilisateur ou mot de passe incorrect.")
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect.")
    else:
        with st.form("register_form"):
            new_username = st.text_input("Choisissez un nom d'utilisateur", key="register_username")
            new_password = st.text_input("Choisissez un mot de passe", type="password", key="register_password")
            submitted = st.form_submit_button("S'inscrire")
            if submitted:
                if get_user_by_username(new_username):
                    st.error("Nom d'utilisateur déjà existant.")
                else:
                    if add_user(new_username, new_password):
                        st.success("Inscription réussie, veuillez vous connecter.")
                    else:
                        st.error("Erreur lors de l'inscription.")

# Bouton de déconnexion
if st.session_state.user is not None:
    if st.sidebar.button("Déconnexion"):
        st.session_state.user = None
        st.session_state.user_id = None
        st.rerun()

# Si l'utilisateur n'est pas connecté, afficher la page de connexion
if st.session_state.user is None:
    login_page()
else:
    st.sidebar.title(f"Bienvenue {st.session_state.user} !")
    menu = st.sidebar.radio("Navigation", ["Transactions", "Importer", "Budgets", "Rappels", "Prévisions", "Analyse"])

    # Affichage des taux de change dans la sidebar
    st.sidebar.subheader("Taux de change")
    def local_get_exchange_rate(currency):
        return get_exchange_rate(currency)
    for cur in ["USD", "CDF", "EUR", "GBP"]:
        st.sidebar.write(f"1 USD = {local_get_exchange_rate(cur)} {cur}")

    def refresh_transactions():
        transactions_db = get_all_transactions(user_id=st.session_state.user_id)
        st.session_state.transactions = [transaction_to_dict(t) for t in transactions_db]

    # --- Transactions ---
    if menu == "Transactions":
        st.header("Gérer vos transactions")
        with st.expander("Enregistrer une Transaction", expanded=True):
            with st.form("new_transaction"):
                trans_type = st.selectbox("Type de transaction", options=["Entrée", "Dépense"])
                amount = st.number_input("Montant", min_value=0.0, value=0.0, step=1.0)
                currency = st.selectbox("Devise", options=["USD", "CDF", "EUR", "GBP"])
                category = st.selectbox("Catégorie", options=CATEGORIES)
                description = st.text_area("Description", value="")
                trans_date = st.date_input("Date", value=date.today())
                submitted = st.form_submit_button("Enregistrer")
                if submitted:
                    if amount <= 0:
                        st.error("Le montant doit être supérieur à zéro.")
                    else:
                        # Calcul des fonds disponibles (pour USD et CDF uniquement)
                        wallet_usd = sum(t["amount"] if t["currency"]=="USD" and t["type"]=="Entrée" else -t["amount"] if t["currency"]=="USD" and t["type"]=="Dépense" else 0 
                                          for t in st.session_state.transactions if t["date"] <= date.today())
                        wallet_cdf = sum(t["amount"] if t["currency"]=="CDF" and t["type"]=="Entrée" else -t["amount"] if t["currency"]=="CDF" and t["type"]=="Dépense" else 0 
                                          for t in st.session_state.transactions if t["date"] <= date.today())
                        if trans_type == "Dépense" and trans_date <= date.today():
                            if currency == "USD" and wallet_usd < amount:
                                st.error("Fonds insuffisants dans le compte USD.")
                            elif currency == "CDF" and wallet_cdf < amount:
                                st.error("Fonds insuffisants dans le compte CDF.")
                            else:
                                rate = local_get_exchange_rate(currency)
                                amount_usd = amount if currency == "USD" else amount / rate
                                if add_transaction(trans_date, trans_type, amount, amount_usd, currency, category, description, rate, st.session_state.user_id):
                                    st.success("Transaction enregistrée !")
                                    refresh_transactions()
                                else:
                                    st.error("Erreur lors de l'ajout de la transaction.")
                        else:
                            rate = local_get_exchange_rate(currency)
                            amount_usd = amount if currency == "USD" else amount / rate
                            if add_transaction(trans_date, trans_type, amount, amount_usd, currency, category, description, rate, st.session_state.user_id):
                                st.success("Transaction enregistrée !")
                                refresh_transactions()
                            else:
                                st.error("Erreur lors de l'ajout de la transaction.")

        st.subheader("Filtrer les transactions")
        col1, col2 = st.columns(2)
        with col1:
            date_range = st.date_input("Plage de dates", [date.today().replace(day=1), date.today()])
        with col2:
            type_filter = st.selectbox("Type", options=["Tous", "Entrée", "Dépense"])
        df = pd.DataFrame(st.session_state.transactions)
        if df.empty:
            st.info("Aucune transaction enregistrée.")
        else:
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.date
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
                if type_filter != "Tous":
                    df = df[df["type"] == type_filter]
                st.dataframe(df.sort_values(by="date", ascending=False))
            else:
                st.error("Erreur: la colonne 'date' est introuvable dans les transactions.")
        
        st.subheader("Modifier / Supprimer une transaction")
        if df.empty:
            st.info("Aucune transaction à modifier ou supprimer.")
        else:
            transaction_ids = df["id"].tolist()
            selected_id = st.selectbox("Sélectionnez la transaction", options=transaction_ids)
            trans = df[df["id"] == selected_id].iloc[0]
            with st.form("edit_transaction"):
                new_date = st.date_input("Date", value=trans["date"])
                new_type = st.selectbox("Type", options=["Entrée", "Dépense"], index=0 if trans["type"]=="Entrée" else 1)
                new_amount = st.number_input("Montant", min_value=0.0, value=float(trans["amount"]), step=1.0)
                new_currency = st.selectbox("Devise", options=["USD", "CDF", "EUR", "GBP"], index=["USD", "CDF", "EUR", "GBP"].index(trans["currency"]))
                new_category = st.selectbox("Catégorie", options=CATEGORIES, index=CATEGORIES.index(trans["category"]) if trans["category"] in CATEGORIES else 0)
                new_description = st.text_area("Description", value=trans["description"])
                update_submit = st.form_submit_button("Mettre à jour")
                delete_submit = st.form_submit_button("Supprimer")
                if update_submit:
                    new_rate = local_get_exchange_rate(new_currency)
                    new_amount_usd = new_amount if new_currency == "USD" else new_amount / new_rate
                    if update_transaction(selected_id, st.session_state.user_id,
                                          date=new_date, type=new_type, amount=new_amount, amount_usd=new_amount_usd,
                                          currency=new_currency, category=new_category, description=new_description, exchange_rate=new_rate):
                        st.success("Transaction mise à jour.")
                        refresh_transactions()
                    else:
                        st.error("Erreur lors de la mise à jour.")
                if delete_submit:
                    if delete_transaction(selected_id, st.session_state.user_id):
                        st.success("Transaction supprimée.")
                        refresh_transactions()
                    else:
                        st.error("Erreur lors de la suppression.")

    # --- Import ---
    elif menu == "Importer":
        st.header("Importer des transactions")
        uploaded_file = st.file_uploader("Choisissez un fichier CSV", type="csv")
        if uploaded_file is not None:
            try:
                df_import = pd.read_csv(uploaded_file)
                required_cols = {"date", "type", "amount", "currency", "category", "description"}
                if not required_cols.issubset(set(df_import.columns)):
                    st.error("Le fichier CSV doit contenir les colonnes : date, type, amount, currency, category, description")
                else:
                    count = 0
                    for index, row in df_import.iterrows():
                        try:
                            trans_date = pd.to_datetime(row["date"]).date()
                            trans_type = row["type"]
                            amount = float(row["amount"])
                            currency = row["currency"]
                            category = row["category"]
                            description = row.get("description", "")
                            rate = local_get_exchange_rate(currency)
                            amount_usd = amount if currency == "USD" else amount / rate
                            if add_transaction(trans_date, trans_type, amount, amount_usd, currency, category, description, rate, st.session_state.user_id):
                                count += 1
                        except Exception as e:
                            st.error(f"Erreur sur la ligne {index+1} : {e}")
                    st.success(f"{count} transactions importées avec succès.")
                    refresh_transactions()
            except Exception as e:
                st.error(f"Erreur lors de l'importation : {e}")

    # --- Budgets ---
    elif menu == "Budgets":
        st.header("Gestion des Budgets")
        st.write("Définissez des budgets par catégorie (les données sont persistées en BDD).")
        budgets_db = get_budgets(st.session_state.user_id)
        if budgets_db:
            st.subheader("Budgets définis")
            for b in budgets_db:
                st.write(f"{b.category} : {b.amount} USD")
        with st.form("budget_form"):
            budget_category = st.selectbox("Catégorie", options=CATEGORIES)
            budget_amount = st.number_input("Montant du budget (en USD)", min_value=0.0, value=0.0, step=1.0)
            budget_submit = st.form_submit_button("Définir le budget")
            if budget_submit:
                if budget_category:
                    if add_budget(st.session_state.user_id, budget_category, budget_amount):
                        st.success(f"Budget pour {budget_category} défini à {budget_amount} USD.")
                    else:
                        st.error("Erreur lors de l'ajout du budget.")
                else:
                    st.error("Veuillez sélectionner une catégorie.")
        st.subheader("Suivi des Budgets")
        df = pd.DataFrame(st.session_state.transactions)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"]).dt.date
            depenses = df[df["type"]=="Dépense"].groupby("category")["amount_usd"].sum().to_dict()
            for b in budgets_db:
                spent = depenses.get(b.category, 0)
                progress = min(spent / b.amount, 1.0) if b.amount > 0 else 0.0
                st.progress(progress)
                st.caption(f"{b.category} : {spent:.2f} / {b.amount:.2f} USD")
    
    # --- Rappels ---
    elif menu == "Rappels":
        st.header("Rappels")
        st.write("Ajoutez des rappels pour ne pas oublier vos échéances (persistants en BDD).")
        reminders_db = get_reminders(st.session_state.user_id)
        if reminders_db:
            st.subheader("Rappels existants")
            reminders_df = pd.DataFrame([{"date": r.date, "titre": r.title, "message": r.message} for r in reminders_db])
            st.table(reminders_df.sort_values(by="date"))
        with st.form("reminder_form"):
            reminder_date = st.date_input("Date du rappel", value=date.today())
            reminder_title = st.text_input("Titre du rappel")
            reminder_message = st.text_area("Message")
            reminder_submit = st.form_submit_button("Ajouter le rappel")
            if reminder_submit:
                if reminder_title:
                    if add_reminder(st.session_state.user_id, reminder_date, reminder_title, reminder_message):
                        st.success("Rappel ajouté.")
                    else:
                        st.error("Erreur lors de l'ajout du rappel.")
                else:
                    st.error("Veuillez entrer un titre pour le rappel.")
    
    # --- Prévisions ---
    elif menu == "Prévisions":
        st.header("Transactions Prévisionnelles")
        df_forecast = pd.DataFrame([t for t in st.session_state.transactions if t["source"]=="prévision"])
        if df_forecast.empty:
            st.info("Aucune transaction prévisionnelle.")
        else:
            st.dataframe(df_forecast.sort_values(by="date"))
    
    # --- Analyse ---
    elif menu == "Analyse":
        st.header("Analyse Financière")
        if st.session_state.transactions:
            df = pd.DataFrame(st.session_state.transactions)
            if df.empty:
                st.info("Aucune transaction à analyser.")
            else:
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"]).dt.date
                # Calcul des totaux par devise d'origine
                total_entrees_usd = df[(df["type"]=="Entrée") & (df["currency"]=="USD")]["amount"].sum()
                total_entrees_cdf = df[(df["type"]=="Entrée") & (df["currency"]=="CDF")]["amount"].sum()
                total_depenses_usd = df[(df["type"]=="Dépense") & (df["currency"]=="USD")]["amount"].sum()
                total_depenses_cdf = df[(df["type"]=="Dépense") & (df["currency"]=="CDF")]["amount"].sum()
                solde_usd = total_entrees_usd - total_depenses_usd
                solde_cdf = total_entrees_cdf - total_depenses_cdf

                st.write(f"**Total Entrées (USD) :** {total_entrees_usd:.2f}")
                st.write(f"**Total Entrées (CDF) :** {total_entrees_cdf:.2f}")
                st.write(f"**Total Dépenses (USD) :** {total_depenses_usd:.2f}")
                st.write(f"**Total Dépenses (CDF) :** {total_depenses_cdf:.2f}")
                st.write(f"**Solde USD :** {solde_usd:.2f} $")
                st.write(f"**Solde CDF :** {solde_cdf:.2f} CDF")
                df_sorted = df.sort_values(by="date")
                df_sorted["balance"] = df_sorted.apply(lambda row: row["amount"] if row["type"]=="Entrée" else -row["amount"], axis=1).cumsum()
                fig_balance = px.line(df_sorted, x="date", y="balance", title="Évolution du Solde Cumulé")
                st.plotly_chart(fig_balance)
                depenses_cat = df[df["type"]=="Dépense"].groupby("category")["amount_usd"].sum().reset_index()
                if not depenses_cat.empty:
                    pie_fig = px.pie(depenses_cat, names="category", values="amount_usd", title="Répartition des Dépenses par Catégorie")
                    st.plotly_chart(pie_fig)
                    for idx, row in depenses_cat.iterrows():
                        cat = row["category"]
                        spent = row["amount_usd"]
                        budgets_db = get_budgets(st.session_state.user_id)
                        budget_amount = None
                        for b in budgets_db:
                            if b.category == cat:
                                budget_amount = b.amount
                                break
                        if budget_amount is not None and spent > budget_amount:
                            st.error(f"Dépassement de budget pour {cat} : dépensé {spent:.2f} USD, budget {budget_amount:.2f} USD.")
                st.subheader("Exporter les données")
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Exporter en CSV", data=csv, file_name="transactions.csv", mime="text/csv")
                try:
                    towrite = io.BytesIO()
                    df.to_excel(towrite, index=False, engine='xlsxwriter')
                    towrite.seek(0)
                    st.download_button(label="Exporter en Excel", data=towrite, file_name="transactions.xlsx", mime="application/vnd.ms-excel")
                except Exception as e:
                    st.error(f"Erreur lors de l'export Excel : {e}")
        else:
            st.info("Aucune transaction à analyser.")

    st.markdown("---")
    st.markdown("Développé par Franga Finances")
    close_session()
