import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database import add_transaction, get_all_transactions, close_session

# Injecter du CSS personnalisé pour moderniser l'interface
st.markdown("""
    <style>
    /* Global */
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
    .export-button {
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Barre latérale personnalisée
st.sidebar.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQU2FWjcc_WFv3s-JcfuQ-mrqf2V7447bef3g&s", use_container_width=True)
st.sidebar.title("Franga Finances")
st.sidebar.markdown("Gérez vos finances avec style et simplicité.")

# Charger les transactions depuis la base de données si non déjà en session
if 'transactions' not in st.session_state:
    st.session_state.transactions = []
    try:
        transactions_db = get_all_transactions()
        for t in transactions_db:
            st.session_state.transactions.append({
                "date": t.date,
                "type": t.type,
                "amount": t.amount,
                "amount_usd": t.amount_usd,
                "currency": t.currency,
                "category": t.category,
                "description": t.description,
                "source": "manuel"  # Par défaut, transactions enregistrées sont considérées réelles
            })
    except Exception as e:
        st.error(f"Erreur lors du chargement des transactions : {e}")

# Recalcul des soldes à partir des transactions réelles (source "manuel" ou "automatique") dont la date est <= aujourd'hui
wallet_usd = 0.0
wallet_cdf = 0.0
for t in st.session_state.transactions:
    # On considère uniquement les transactions réelles (et non les prévisions)
    if t["source"] in ["manuel", "automatique"] and t["date"] <= date.today():
        if t["type"] == "Entrée":
            if t["currency"] == "USD":
                wallet_usd += t["amount"]
            else:
                wallet_cdf += t["amount"]
        else:  # Dépense
            if t["currency"] == "USD":
                wallet_usd -= t["amount"]
            else:
                wallet_cdf -= t["amount"]

st.session_state.wallet_usd = wallet_usd
st.session_state.wallet_cdf = wallet_cdf

# Taux de change ajustable (pour l'affichage, sans incidence rétroactive sur les soldes déjà enregistrés)
exchange_rate = st.sidebar.number_input("Taux de change (1 USD = ? CDF)", value=2800, step=1)
if exchange_rate <= 0:
    st.error("Le taux de change doit être un nombre positif.")
    st.stop()

# Titre principal
st.markdown("<p class='header-title'>💰 Gestion Financière Personnelle – Version Congolaise</p>", unsafe_allow_html=True)
st.markdown("**Une solution moderne pour maîtriser vos finances**")

# Affichage du portefeuille avec des "cards"
st.markdown("<div class='wallet-card'>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.subheader("Solde en USD")
    st.write(f"${st.session_state.wallet_usd:.2f}")
with col2:
    st.subheader("Solde en CDF")
    st.write(f"{st.session_state.wallet_cdf:.2f} CDF")
st.markdown("</div>", unsafe_allow_html=True)

# Formulaire de transaction dans un expander
with st.expander("Enregistrer une Transaction", expanded=True):
    with st.form("new_transaction"):
        trans_type = st.selectbox("Type de transaction", options=["Entrée", "Dépense"])
        amount = st.number_input("Montant", min_value=0.0, value=0.0, step=1.0)
        currency = st.selectbox("Devise", options=["USD", "CDF"])
        category = st.text_input("Catégorie", value="Général")
        description = st.text_area("Description", value="")
        trans_date = st.date_input("Date", value=date.today())
        submit = st.form_submit_button("Enregistrer")
        
        if submit:
            # Validation des entrées
            if amount <= 0:
                st.error("Le montant doit être supérieur à zéro.")
                st.stop()
            # Pour les transactions réelles, vérification de la disponibilité des fonds pour une dépense
            if trans_type == "Dépense" and trans_date <= date.today():
                if currency == "USD" and st.session_state.wallet_usd < amount:
                    st.error("Fonds insuffisants dans le compte USD.")
                    st.stop()
                if currency == "CDF" and st.session_state.wallet_cdf < amount:
                    st.error("Fonds insuffisants dans le compte CDF.")
                    st.stop()
            
            # Calcul du montant converti pour le suivi (pour l'analyse)
            amount_usd = amount if currency == "USD" else amount / exchange_rate
            
            # Déterminer la source en fonction de la date : Réel si aujourd'hui ou passé, Prévision si futur
            source = "manuel" if trans_date <= date.today() else "prévision"
            
            transaction = {
                "date": trans_date,
                "type": trans_type,
                "amount": amount,
                "amount_usd": amount_usd,
                "currency": currency,
                "category": category,
                "description": description,
                "source": source
            }
            
            # Vérification des doublons pour les transactions réelles (on ignore les prévisions)
            def is_duplicate(new_t, transactions):
                if new_t["source"] != "manuel":
                    return False
                for t in transactions:
                    if (t["source"] == "manuel" and
                        t["date"] == new_t["date"] and
                        t["type"] == new_t["type"] and
                        t["amount"] == new_t["amount"] and
                        t["category"].lower() == new_t["category"].lower()):
                        return True
                return False
            
            if not is_duplicate(transaction, st.session_state.transactions):
                try:
                    if add_transaction(trans_date, trans_type, amount, amount_usd, currency, category, description, exchange_rate):
                        st.session_state.transactions.append(transaction)
                        # Mise à jour des soldes seulement pour les transactions réelles
                        if trans_date <= date.today():
                            if trans_type == "Entrée":
                                if currency == "USD":
                                    st.session_state.wallet_usd += amount
                                else:
                                    st.session_state.wallet_cdf += amount
                            else:  # Dépense
                                if currency == "USD":
                                    st.session_state.wallet_usd -= amount
                                else:
                                    st.session_state.wallet_cdf -= amount
                        st.success("Transaction enregistrée!")
                    else:
                        st.error("Erreur lors de l'ajout de la transaction.")
                except Exception as e:
                    st.error(f"Erreur lors de l'ajout de la transaction : {e}")
            else:
                st.warning("Cette transaction semble être un doublon.")

# Budgétisation automatique
st.subheader("Budgétisation Automatique")
today = date.today()

# Allocation automatique le 10 du mois pour la restauration (transaction réelle)
if today.day == 10:
    st.info("Allocation automatique de 100 USD pour la restauration")
    transaction = {
        "date": today,
        "type": "Entrée",
        "amount": 100,
        "amount_usd": 100,
        "currency": "USD",
        "category": "Restauration",
        "description": "Allocation automatique du 10 du mois",
        "source": "automatique"
    }
    try:
        if add_transaction(today, "Entrée", 100, 100, "USD", "Restauration", "Allocation automatique du 10 du mois", exchange_rate):
            st.session_state.transactions.append(transaction)
            st.session_state.wallet_usd += 100
            st.success("Allocation automatique du 10 appliquée.")
    except Exception as e:
        st.error(f"Erreur lors de l'allocation automatique du 10 : {e}")

# Allocation automatique le 25 du mois pour les dépenses programmées (transaction réelle)
if today.day == 25:
    st.info("Allocation automatique de 700 USD répartis")
    allocations = {
        "Dîme": 70,
        "Épargne": 300,
        "Loyer": 100,
        "Loisir": 100,
        "Transport": 60
    }
    for cat, amt in allocations.items():
        transaction = {
            "date": today,
            "type": "Dépense",
            "amount": amt,
            "amount_usd": amt,
            "currency": "USD",
            "category": cat,
            "description": f"Allocation automatique du 25 pour {cat}",
            "source": "automatique"
        }
        try:
            if add_transaction(today, "Dépense", amt, amt, "USD", cat, f"Allocation automatique du 25 pour {cat}", exchange_rate):
                st.session_state.transactions.append(transaction)
                if st.session_state.wallet_usd < amt:
                    st.error(f"Fonds insuffisants pour l'allocation de {cat}.")
                else:
                    st.session_state.wallet_usd -= amt
            else:
                st.error(f"Erreur lors de l'allocation pour {cat}.")
        except Exception as e:
            st.error(f"Erreur lors de l'allocation pour {cat} : {e}")
    st.success("Allocations automatiques du 25 appliquées.")

# Affichage détaillé du portefeuille dans un expander
with st.expander("Voir Détails du Portefeuille"):
    st.write(f"**Solde en USD :** {st.session_state.wallet_usd:.2f} $")
    st.write(f"**Solde en CDF :** {st.session_state.wallet_cdf:.2f} CDF")
    if st.checkbox("Voir l'équivalence entre devises"):
        st.write(f"1 USD = {exchange_rate} CDF")
        st.write(f"{st.session_state.wallet_usd:.2f} USD = {st.session_state.wallet_usd * exchange_rate:.2f} CDF")
        st.write(f"{st.session_state.wallet_cdf:.2f} CDF = {st.session_state.wallet_cdf / exchange_rate:.2f} USD")

# Export CSV des transactions
if st.session_state.transactions:
    df = pd.DataFrame(st.session_state.transactions)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Exporter les transactions en CSV",
        data=csv,
        file_name='transactions.csv',
        mime='text/csv',
        key='download-csv'
    )

# Tableau interactif des transactions avec st.data_editor
if st.session_state.transactions:
    st.subheader("Historique des Transactions")
    df = pd.DataFrame(st.session_state.transactions)
    edited_df = st.data_editor(df.sort_values(by="date", ascending=False), num_rows="dynamic")
    
    st.subheader("Analyse Financière")
    total_entrees = df[df["type"] == "Entrée"]["amount_usd"].sum()
    total_depenses = df[df["type"] == "Dépense"]["amount_usd"].sum()
    st.write(f"**Total Entrées (USD) :** {total_entrees:.2f}")
    st.write(f"**Total Dépenses (USD) :** {total_depenses:.2f}")
    st.write(f"**Solde Final (USD) :** {st.session_state.wallet_usd:.2f}")
    
    depenses_cat = df[df["type"] == "Dépense"].groupby("category")["amount_usd"].sum().reset_index()
    if not depenses_cat.empty:
        pie_fig = px.pie(depenses_cat, names="category", values="amount_usd",
                         title="Répartition des Dépenses par Catégorie")
        st.plotly_chart(pie_fig)
    else:
        st.warning("Aucune donnée disponible pour créer le graphique.")

    # Graphique d'évolution mensuelle (entrées et dépenses)
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
    evolution = df.groupby(["month", "type"])["amount_usd"].sum().reset_index()
    line_fig = px.line(evolution, x="month", y="amount_usd", color="type", markers=True,
                       title="Évolution Mensuelle (USD)")
    st.plotly_chart(line_fig)

# Fermeture de la session de la base de données
close_session()
