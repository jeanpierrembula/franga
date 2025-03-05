from sqlalchemy import create_engine, Column, Integer, String, Float, Date, CheckConstraint, UniqueConstraint, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import logging
from passlib.context import CryptContext  # Pour le hachage des mots de passe

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Contexte de hachage avec bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Déclaration de la base
Base = declarative_base()

# Modèle Utilisateur
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)  # On stocke ici le hash

# Modèle Transaction
class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)  # Liaison avec l'utilisateur
    date = Column(Date, default=datetime.datetime.utcnow)
    type = Column(String, nullable=False)         # "Entrée" ou "Dépense"
    amount = Column(Float, nullable=False)          # Montant dans la devise d'origine
    amount_usd = Column(Float, nullable=False)      # Montant converti en USD
    currency = Column(String, nullable=False)       # "USD", "CDF", "EUR", "GBP"
    category = Column(String, nullable=False)
    description = Column(String)
    exchange_rate = Column(Float, nullable=False)   # Taux de change utilisé

    __table_args__ = (
        CheckConstraint('amount > 0', name='check_amount_positive'),
        CheckConstraint('amount_usd > 0', name='check_amount_usd_positive'),
        CheckConstraint("type IN ('Entrée', 'Dépense')", name='check_type_valid'),
        CheckConstraint("currency IN ('USD', 'CDF', 'EUR', 'GBP')", name='check_currency_valid'),
        Index('idx_user_date', 'user_id', 'date'),
        Index('idx_user_category', 'user_id', 'category'),
    )

# Log des automatisations (pour éviter les doublons)
class AutomationLog(Base):
    __tablename__ = 'automation_logs'
    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.datetime.utcnow)
    automation_type = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('date', 'automation_type', name='uix_date_automation'),)

# Modèle Budget pour la persistance des budgets
class Budget(Base):
    __tablename__ = 'budgets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)

# Modèle Reminder pour la persistance des rappels
class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    date = Column(Date, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String)

# IMPORTANT : Si vous avez déjà créé transactions.db avec un ancien schéma,
# supprimez-le pour recréer la base avec les nouveaux modèles.
engine = create_engine('sqlite:///transactions.db', connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def get_all_transactions(user_id=None):
    try:
        query = session.query(Transaction)
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        transactions = query.all()
        logger.info(f"{len(transactions)} transactions récupérées.")
        return transactions
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des transactions : {e}")
        return []

def update_transaction(transaction_id, user_id, **kwargs):
    try:
        trans = session.query(Transaction).filter_by(id=transaction_id, user_id=user_id).first()
        if not trans:
            return False
        for key, value in kwargs.items():
            setattr(trans, key, value)
        session.commit()
        logger.info(f"Transaction mise à jour : {trans}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de la mise à jour de la transaction : {e}")
        return False

def delete_transaction(transaction_id, user_id):
    try:
        trans = session.query(Transaction).filter_by(id=transaction_id, user_id=user_id).first()
        if not trans:
            return False
        session.delete(trans)
        session.commit()
        logger.info(f"Transaction supprimée : {trans}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de la suppression de la transaction : {e}")
        return False

def add_user(username, password):
    try:
        hashed_password = pwd_context.hash(password)
        new_user = User(username=username, password=hashed_password)
        session.add(new_user)
        session.commit()
        logger.info(f"Utilisateur ajouté : {username}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de l'ajout de l'utilisateur : {e}")
        return False

def get_user_by_username(username):
    try:
        user = session.query(User).filter_by(username=username).first()
        return user
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur : {e}")
        return None

def log_automation(date, automation_type):
    try:
        log = AutomationLog(date=date, automation_type=automation_type)
        session.add(log)
        session.commit()
        logger.info(f"Automation log ajouté pour {automation_type} le {date}.")
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de l'ajout du log d'automatisation : {e}")

def check_automation(date, automation_type):
    try:
        result = session.query(AutomationLog).filter_by(date=date, automation_type=automation_type).first()
        return result is not None
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du log d'automatisation : {e}")
        return False

def add_budget(user_id, category, amount):
    try:
        new_budget = Budget(user_id=user_id, category=category, amount=amount)
        session.add(new_budget)
        session.commit()
        logger.info(f"Budget ajouté pour {category} : {amount} USD")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de l'ajout du budget : {e}")
        return False

def get_budgets(user_id):
    try:
        return session.query(Budget).filter_by(user_id=user_id).all()
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des budgets : {e}")
        return []

def add_reminder(user_id, date, title, message):
    try:
        new_reminder = Reminder(user_id=user_id, date=date, title=title, message=message)
        session.add(new_reminder)
        session.commit()
        logger.info(f"Rappel ajouté : {title} le {date}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de l'ajout du rappel : {e}")
        return False

def get_reminders(user_id):
    try:
        return session.query(Reminder).filter_by(user_id=user_id).all()
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des rappels : {e}")
        return []

def add_transaction(date, trans_type, amount, amount_usd, currency, category, description, exchange_rate, user_id):
    try:
        if amount <= 0 or amount_usd <= 0:
            raise ValueError("Le montant doit être positif.")
        if date > datetime.datetime.utcnow().date():
            raise ValueError("La date ne peut pas être dans le futur.")
        if trans_type not in ["Entrée", "Dépense"]:
            raise ValueError("Le type de transaction doit être 'Entrée' ou 'Dépense'.")
        if currency not in ["USD", "CDF", "EUR", "GBP"]:
            raise ValueError("La devise doit être 'USD', 'CDF', 'EUR' ou 'GBP'.")
        if not category:
            raise ValueError("La catégorie ne peut pas être vide.")

        new_trans = Transaction(
            user_id=user_id,
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

def close_session():
    try:
        session.close()
        logger.info("Session de la base de données fermée.")
    except Exception as e:
        logger.error(f"Erreur lors de la fermeture de la session : {e}")
