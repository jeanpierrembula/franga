# franga.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database import add_transaction, get_all_transactions

# Chargement des transactions existantes depuis la base de données dans l'état de session
if 'transactions' not in st.session_state:
    st.session_state.transactions = []
    transactions_db = get_all_transactions()
    for t in transactions_db:
        st.session_state.transactions.append({
            "date": t.date,
            "type": t.type,
            "amount": t.amount,
            "amount_usd": t.amount_usd,
            "currency": t.currency,
            "category": t.category,
            "description": t.description
        })

# Initialisation des soldes si non définis
if 'wallet_usd' not in st.session_state:
    st.session_state.wallet_usd = 0.0
if 'wallet_cdf' not in st.session_state:
    st.session_state.wallet_cdf = 0.0

# Taux de change ajustable (1 USD = ? CDF)
exchange_rate = st.sidebar.number_input("Taux de change (1 USD = ? CDF)", value=2800, step=1)

st.title("Gestion Financière Personnelle – Version Congolaise")
st.markdown("Une solution intuitive pour maîtriser vos finances au quotidien.")

## FORMULAIRE DE TRANSACTION
st.subheader("Enregistrer une Transaction")
with st.form("new_transaction"):
    trans_type = st.selectbox("Type de transaction", options=["Entrée", "Dépense"])
    amount = st.number_input("Montant", min_value=0.0, value=0.0, step=1.0)
    currency = st.selectbox("Devise", options=["USD", "CDF"])
    category = st.text_input("Catégorie", value="Général")
    description = st.text_area("Description", value="")
    trans_date = st.date_input("Date", value=date.today())
    submit = st.form_submit_button("Enregistrer")
    
    if submit:
        # Conversion en USD pour le suivi interne
        amount_usd = amount if currency == "USD" else amount / exchange_rate
        
        # Création de la transaction sous forme de dictionnaire
        transaction = {
            "date": trans_date,
            "type": trans_type,
            "amount": amount,
            "amount_usd": amount_usd,
            "currency": currency,
            "category": category,
            "description": description
        }
        st.session_state.transactions.append(transaction)
        # Enregistrement en base de données
        add_transaction(trans_date, trans_type, amount, amount_usd, currency, category, description)
        
        # Mise à jour du portefeuille
        if trans_type == "Entrée":
            if currency == "USD":
                st.session_state.wallet_usd += amount
                st.session_state.wallet_cdf += amount * exchange_rate
            else:
                st.session_state.wallet_cdf += amount
                st.session_state.wallet_usd += amount / exchange_rate
        else:  # Pour une dépense
            if currency == "USD":
                st.session_state.wallet_usd -= amount
                st.session_state.wallet_cdf -= amount * exchange_rate
            else:
                st.session_state.wallet_cdf -= amount
                st.session_state.wallet_usd -= amount / exchange_rate
        st.success("Transaction enregistrée avec succès!")

## BUDGÉTISATION AUTOMATIQUE
st.subheader("Budgétisation Automatique")
today = date.today()

# Allocation automatique le 10 du mois pour la restauration
if today.day == 10:
    st.info("Allocation automatique de 100 USD pour la restauration")
    transaction = {
        "date": today,
        "type": "Entrée",
        "amount": 100,
        "amount_usd": 100,
        "currency": "USD",
        "category": "Restauration",
        "description": "Allocation automatique du 10 du mois"
    }
    st.session_state.transactions.append(transaction)
    add_transaction(today, "Entrée", 100, 100, "USD", "Restauration", "Allocation automatique du 10 du mois")
    st.session_state.wallet_usd += 100
    st.session_state.wallet_cdf += 100 * exchange_rate

# Allocation automatique le 25 du mois
if today.day == 25:
    st.info("Allocation automatique de 700 USD répartis")
    allocations = {
        "Dîme": 70,         # 10% de 700 USD
        "Épargne": 300,
        "Loyer": 100,       # (70 pour le paiement mensuel et 30 pour la caution)
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
            "description": f"Allocation automatique du 25 pour {cat}"
        }
        st.session_state.transactions.append(transaction)
        add_transaction(today, "Dépense", amt, amt, "USD", cat, f"Allocation automatique du 25 pour {cat}")
        st.session_state.wallet_usd -= amt
        st.session_state.wallet_cdf -= amt * exchange_rate
    st.success("Allocations automatiques du 25 appliquées.")

## AFFICHAGE DU PORTEFEUILLE
st.subheader("Portefeuille Intelligent")
st.write(f"**Solde en USD :** {st.session_state.wallet_usd:.2f} $")
st.write(f"**Solde en CDF :** {st.session_state.wallet_cdf:.2f} CDF")
if st.checkbox("Voir l'équivalence entre devises"):
    st.write(f"1 USD = {exchange_rate} CDF")
    st.write(f"{st.session_state.wallet_usd:.2f} USD = {st.session_state.wallet_usd * exchange_rate:.2f} CDF")
    st.write(f"{st.session_state.wallet_cdf:.2f} CDF = {st.session_state.wallet_cdf / exchange_rate:.2f} USD")

## HISTORIQUE ET ANALYSE
if st.session_state.transactions:
    st.subheader("Historique des Transactions")
    df = pd.DataFrame(st.session_state.transactions)
    st.dataframe(df.sort_values(by="date", ascending=False))
    
    st.subheader("Analyse Financière")
    total_entrees = df[df["type"] == "Entrée"]["amount_usd"].sum()
    total_depenses = df[df["type"] == "Dépense"]["amount_usd"].sum()
    st.write(f"**Total Entrées (USD) :** {total_entrees:.2f}")
    st.write(f"**Total Dépenses (USD) :** {total_depenses:.2f}")
    st.write(f"**Solde Final (USD) :** {st.session_state.wallet_usd:.2f}")
    
    # Graphique en camembert des dépenses par catégorie
    depenses_cat = df[df["type"] == "Dépense"].groupby("category")["amount_usd"].sum().reset_index()
    fig = px.pie(depenses_cat, names="category", values="amount_usd",
                 title="Répartition des Dépenses par Catégorie")
    st.plotly_chart(fig)
