# database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Déclaration du modèle de base
Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.datetime.utcnow)
    type = Column(String)         # "Entrée" ou "Dépense"
    amount = Column(Float)        # Montant dans la devise d'origine
    amount_usd = Column(Float)    # Montant converti en USD pour le suivi interne
    currency = Column(String)     # "USD" ou "CDF"
    category = Column(String)
    description = Column(String)

# Création du moteur de base de données
engine = create_engine('sqlite:///transactions.db', connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)

# Création d'une session
Session = sessionmaker(bind=engine)
session = Session()

def add_transaction(date, trans_type, amount, amount_usd, currency, category, description):
    """Ajoute une transaction dans la base de données."""
    new_trans = Transaction(
        date=date,
        type=trans_type,
        amount=amount,
        amount_usd=amount_usd,
        currency=currency,
        category=category,
        description=description
    )
    session.add(new_trans)
    session.commit()

def get_all_transactions():
    """Retourne toutes les transactions enregistrées."""
    return session.query(Transaction).all()
