from sqlalchemy import create_engine, Column, Integer, String, Float, Date, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Déclaration du modèle de base
Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.datetime.utcnow)
    type = Column(String, nullable=False)         # "Entrée" ou "Dépense"
    amount = Column(Float, nullable=False)          # Montant dans la devise d'origine
    amount_usd = Column(Float, nullable=False)      # Montant converti en USD
    currency = Column(String, nullable=False)       # "USD" ou "CDF"
    category = Column(String, nullable=False)
    description = Column(String)
    exchange_rate = Column(Float, nullable=False)   # Taux de change utilisé lors de l'enregistrement

    __table_args__ = (
        CheckConstraint('amount > 0', name='check_amount_positive'),
        CheckConstraint('amount_usd > 0', name='check_amount_usd_positive'),
        CheckConstraint("type IN ('Entrée', 'Dépense')", name='check_type_valid'),
        CheckConstraint("currency IN ('USD', 'CDF')", name='check_currency_valid'),
    )

class AutomationLog(Base):
    __tablename__ = 'automation_logs'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.datetime.utcnow)
    automation_type = Column(String, nullable=False)  # ex: "restauration" ou "allocation25"
    __table_args__ = (UniqueConstraint('date', 'automation_type', name='uix_date_automation'),)

# Création du moteur de base de données
engine = create_engine('sqlite:///transactions.db', connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def add_transaction(date, trans_type, amount, amount_usd, currency, category, description, exchange_rate):
    """
    Ajoute une transaction dans la base de données en stockant le taux de change utilisé.
    """
    try:
        if amount <= 0 or amount_usd <= 0:
            raise ValueError("Le montant doit être positif.")
        if date > datetime.datetime.utcnow().date():
            raise ValueError("La date ne peut pas être dans le futur.")
        if trans_type not in ["Entrée", "Dépense"]:
            raise ValueError("Le type de transaction doit être 'Entrée' ou 'Dépense'.")
        if currency not in ["USD", "CDF"]:
            raise ValueError("La devise doit être 'USD' ou 'CDF'.")
        if not category:
            raise ValueError("La catégorie ne peut pas être vide.")

        new_trans = Transaction(
            date=date,
            type=trans_type,
            amount=amount,
            amount_usd=amount_usd,
            currency=currency,
            category=category,
            description=description,
            exchange_rate=exchange_rate
        )
        session.add(new_trans)
        session.commit()
        logger.info(f"Transaction ajoutée : {new_trans}")
        return True

    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de l'ajout de la transaction : {e}")
        return False

def get_all_transactions():
    """
    Retourne toutes les transactions enregistrées.
    """
    try:
        transactions = session.query(Transaction).all()
        logger.info(f"{len(transactions)} transactions récupérées.")
        return transactions
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transactions : {e}")
        return []

def log_automation(date, automation_type):
    """
    Enregistre l'exécution d'une automatisation pour éviter les doublons.
    """
    try:
        log = AutomationLog(date=date, automation_type=automation_type)
        session.add(log)
        session.commit()
        logger.info(f"Automation log ajouté pour {automation_type} le {date}.")
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de l'ajout du log d'automatisation : {e}")

def check_automation(date, automation_type):
    """
    Vérifie si l'automatisation a déjà été exécutée pour une date donnée.
    """
    try:
        result = session.query(AutomationLog).filter_by(date=date, automation_type=automation_type).first()
        return result is not None
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du log d'automatisation : {e}")
        return False

def close_session():
    """Ferme la session de la base de données."""
    try:
        session.close()
        logger.info("Session de la base de données fermée.")
    except Exception as e:
        logger.error(f"Erreur lors de la fermeture de la session : {e}")
