import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import io
import requests
from database import (add_transaction, get_all_transactions, update_transaction, delete_transaction,
                      add_user, get_user_by_username, close_session)

# Initialisation des clés de session pour s'assurer qu'elles existent
st.session_state.setdefault("user", None)
st.session_state.setdefault("user_id", None)
st.session_state.setdefault("transactions", [])
st.session_state.setdefault("budgets", {})     # Pour l'instant en session, vous pouvez persister en BDD
st.session_state.setdefault("reminders", {})     # Pareil pour les rappels

# Restauration de la session via st.query_params (lecture uniquement)
params = st.query_params
if params.get("loggedIn", ["0"])[0] == "1" and st.session_state.get("user") is None:
    username_from_qp = params.get("username", [None])[0]
    if username_from_qp:
        st.session_state.user = username_from_qp
        user = get_user_by_username(username_from_qp)
        if user:
            st.session_state.user_id = user.id

# Fonction de récupération du taux de change depuis l'API avec cache
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

# Liste prédéfinie de catégories pour améliorer l'UX
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

# Injecter du CSS personnalisé
st.markdown("""
    <style>
    body {
        background-color: #f0f2f6;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .reportview-container .main .block-container {
        max-width: 1200px;
        padding: 2rem 1rem;
    }
    .sidebar .sidebar-content {
        background-image: linear-gradient(135deg, #2e7bcf, #1b5fa7);
        color: white;
    }
    .stButton>button {
        background-color: #2e7bcf;
        color: white;
        border-radius: 5px;
    }
    .wallet-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2e7bcf;
    }
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
                # Vérifier le mot de passe haché avec passlib
                if user and user.password and st.session_state.get("user") is None and user and \
                   st.session_state.get("user") is None and st.session_state.get("user") is None:
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    if pwd_context.verify(password, user.password):
                        st.session_state.user = username
                        st.session_state.user_id = user.id
                        st.query_params = {"loggedIn": "1", "username": username}
                        st.success("Connecté !")
                        transactions_db = get_all_transactions(user_id=st.session_state.user_id)
                        st.session_state.transactions = [transaction_to_dict(t) for t in transactions_db]
                    else:
                        st.error("Nom d'utilisateur ou mot de passe incorrect.")
                elif user and user.password:
                    # Vérification si la session est déjà active
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                    if pwd_context.verify(password, user.password):
                        st.session_state.user = username
                        st.session_state.user_id = user.id
                        st.query_params = {"loggedIn": "1", "username": username}
                        st.success("Connecté !")
                        transactions_db = get_all_transactions(user_id=st.session_state.user_id)
                        st.session_state.transactions = [transaction_to_dict(t) for t in transactions_db]
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
        st.query_params = {"loggedIn": "0"}
        st.rerun()

# Si l'utilisateur n'est pas connecté, afficher la page de login
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
                # Utiliser la liste prédéfinie pour les catégories
                currency = st.selectbox("Devise", options=["USD", "CDF", "EUR", "GBP"])
                category = st.selectbox("Catégorie", options=CATEGORIES)
                description = st.text_area("Description", value="")
                trans_date = st.date_input("Date", value=date.today())
                submitted = st.form_submit_button("Enregistrer")
                if submitted:
                    if amount <= 0:
                        st.error("Le montant doit être supérieur à zéro.")
                    else:
                        # Calcul simplifié des fonds disponibles (USD et CDF uniquement pour les transactions réelles)
                        wallet_usd = sum(t["amount"] if t["currency"]=="USD" and t["type"]=="Entrée" else -t["amount"] if t["currency"]=="USD" and t["type"]=="Dépense" else 0 
                                          for t in st.session_state.transactions if t["date"] <= date.today())
                        wallet_cdf = sum(t["amount"] if t["currency"]=="CDF" and t["type"]=="Entrée" else -t["amount"] if t["currency"]=="CDF" and t["type"]=="Dépense" else 0 
                                          for t in st.session_state.transactions if t["date"] <= date.today())
                        if trans_type=="Dépense" and trans_date <= date.today():
                            if currency=="USD" and wallet_usd < amount:
                                st.error("Fonds insuffisants dans le compte USD.")
                            elif currency=="CDF" and wallet_cdf < amount:
                                st.error("Fonds insuffisants dans le compte CDF.")
                            else:
                                rate = local_get_exchange_rate(currency)
                                amount_usd = amount if currency=="USD" else amount / rate
                                if add_transaction(trans_date, trans_type, amount, amount_usd, currency, category, description, rate, st.session_state.user_id):
                                    st.success("Transaction enregistrée !")
                                    refresh_transactions()
                                else:
                                    st.error("Erreur lors de l'ajout de la transaction.")
                        else:
                            rate = local_get_exchange_rate(currency)
                            amount_usd = amount if currency=="USD" else amount / rate
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
                    df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
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
                new_currency = st.selectbox("Devise", options=["USD", "CDF", "EUR", "GBP"], index=["USD","CDF","EUR","GBP"].index(trans["currency"]))
                new_category = st.selectbox("Catégorie", options=CATEGORIES, index=CATEGORIES.index(trans["category"]) if trans["category"] in CATEGORIES else 0)
                new_description = st.text_area("Description", value=trans["description"])
                update_submit = st.form_submit_button("Mettre à jour")
                delete_submit = st.form_submit_button("Supprimer")
                if update_submit:
                    new_rate = local_get_exchange_rate(new_currency)
                    new_amount_usd = new_amount if new_currency=="USD" else new_amount / new_rate
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
                            amount_usd = amount if currency=="USD" else amount / rate
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
        st.write("Définissez des budgets par catégorie.")
        with st.form("budget_form"):
            budget_category = st.selectbox("Catégorie", options=CATEGORIES)
            budget_amount = st.number_input("Montant du budget (en USD)", min_value=0.0, value=0.0, step=1.0)
            budget_submit = st.form_submit_button("Définir le budget")
            if budget_submit:
                if budget_category:
                    st.session_state.budgets[budget_category] = budget_amount
                    st.success(f"Budget pour {budget_category} défini à {budget_amount} USD.")
                else:
                    st.error("Veuillez entrer une catégorie.")
        if st.session_state.budgets:
            st.subheader("Suivi des Budgets")
            df = pd.DataFrame(st.session_state.transactions)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"]).dt.date
                depenses = df[df["type"]=="Dépense"].groupby("category")["amount_usd"].sum().to_dict()
                for cat, budget in st.session_state.budgets.items():
                    spent = depenses.get(cat, 0)
                    if budget > 0:
                        progress = min(spent / budget, 1.0)  # <-- Correction ici
                    else:
                        progress = 0.0
                    st.progress(progress)
                    st.caption(f"{cat} : {spent:.2f} / {budget:.2f} USD")
    
    # --- Rappels ---
    elif menu == "Rappels":
        st.header("Rappels")
        st.write("Ajoutez des rappels pour ne pas oublier vos échéances.")
        with st.form("reminder_form"):
            reminder_date = st.date_input("Date du rappel", value=date.today())
            reminder_title = st.text_input("Titre du rappel")
            reminder_message = st.text_area("Message")
            reminder_submit = st.form_submit_button("Ajouter le rappel")
            if reminder_submit:
                if reminder_title:
                    st.session_state.reminders[datetime.now().isoformat()] = {"date": reminder_date, "title": reminder_title, "message": reminder_message}
                    st.success("Rappel ajouté.")
                else:
                    st.error("Veuillez entrer un titre pour le rappel.")
        if st.session_state.reminders:
            st.subheader("Rappels à venir")
            reminders_df = pd.DataFrame(list(st.session_state.reminders.values()))
            st.table(reminders_df.sort_values(by="date"))
            today_reminders = [r for r in st.session_state.reminders.values() if r["date"] == date.today()]
            if today_reminders:
                st.warning("Vous avez des rappels pour aujourd'hui !")
    
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
                total_entrees = df[df["type"]=="Entrée"]["amount_usd"].sum()
                total_depenses = df[df["type"]=="Dépense"]["amount_usd"].sum()
                st.write(f"**Total Entrées (USD) :** {total_entrees:.2f}")
                st.write(f"**Total Dépenses (USD) :** {total_depenses:.2f}")
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
                        if cat in st.session_state.budgets and spent > st.session_state.budgets[cat]:
                            st.error(f"Dépassement de budget pour {cat} : dépensé {spent:.2f} USD, budget {st.session_state.budgets[cat]} USD.")
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
