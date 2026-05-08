# -*- coding: utf-8 -*-

import os
import uuid
import click
import psycopg2
from datetime import datetime, UTC
from random import choice
from dotenv import load_dotenv

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.schema import DropConstraint, DropTable, MetaData, Table, ForeignKeyConstraint

from models import (
    Base, engine, SessionLocal,
    RoleEnum, MessageTypeEnum, PriorityEnum,
    LLMModel, Service, Utilisateur, Bot, Conversation, Message, Document,
    ConversationStatus, ConversationTempDocument,
    Chunk, RefreshToken,
)
from rag.smalltalk import SMALLTALK_PATTERN, DEFAULT_RESPONSES
from auth.security import hash_password

load_dotenv()

# =========================================================
# CONFIG
# =========================================================
DATABASE_NAME     = os.getenv("DATABASE_NAME", "regbot")
DATABASE_USER     = os.getenv("DATABASE_USER", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "Salimata")
DATABASE_HOST     = os.getenv("DATABASE_HOST", "127.0.0.1")
DATABASE_PORT     = os.getenv("DATABASE_PORT", "5433")

INFO  = "[INFO]"
WARN  = "[WARN]"
ERROR = "[ERROR]"

# =========================================================
# SESSION HELPER
# =========================================================
def get_session() -> Session:
    return SessionLocal()


# =========================================================
# DATABASE CREATION
# =========================================================
def create_database_if_not_exists():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=DATABASE_PORT,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE_NAME,))
        if not cursor.fetchone():
            print(f"{INFO} Base '{DATABASE_NAME}' non trouvee. Creation en cours...")
            cursor.execute(f'CREATE DATABASE "{DATABASE_NAME}"')
            print(f"{INFO} Base '{DATABASE_NAME}' creee avec succes.")
        else:
            print(f"{INFO} La base '{DATABASE_NAME}' existe deja.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"{ERROR} Erreur lors de la creation de la base : {e}")
        raise


# =========================================================
# PGVECTOR
# =========================================================
def enable_pgvector_extension():
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        print(f"{INFO} Extension pgvector activee.")
    except Exception as e:
        print(f"{WARN} pgvector non disponible : {e}")


# =========================================================
# DROP ALL (FK-aware)
# =========================================================
def drop_everything():
    con = engine.connect()
    trans = con.begin()
    inspector = inspect(engine)
    meta      = MetaData()
    tables    = []
    all_fkeys = []
    for table_name in inspector.get_table_names():
        fkeys = []
        for fkey in inspector.get_foreign_keys(table_name):
            if not fkey["name"]:
                continue
            fkeys.append(ForeignKeyConstraint((), (), name=fkey["name"]))
        tables.append(Table(table_name, meta, *fkeys))
        all_fkeys.extend(fkeys)
    for fkey in all_fkeys:
        con.execute(DropConstraint(fkey))
    for table in tables:
        con.execute(DropTable(table))
    trans.commit()
    con.close()


# =========================================================
# CREATE TABLES + SEED SERVICES
# =========================================================
def create_all_tables():
    Base.metadata.create_all(bind=engine)
    session = get_session()
    try:
        services_ref = [
            ("RH",           "Gestion des ressources humaines"),
            ("FINANCE",      "Gestion comptable et financiere"),
            ("TECHNIQUE",    "Support et maintenance technique"),
            ("JURIDIQUE",    "Conseil et conformite juridique"),
            ("INFORMATIQUE", "Infrastructure et systemes d'information"),
            ("DIRECTION",    "Direction generale"),
        ]
        for nom, description in services_ref:
            if not session.query(Service).filter_by(nom=nom).first():
                session.add(Service(nom=nom, description=description))
        session.commit()
        print(f"{INFO} Services de reference inseres.")
    finally:
        session.close()


# =========================================================
# SEED DATA
# =========================================================
def add_llm_models():
    session = get_session()
    try:
        if not session.query(LLMModel).filter_by(name="llama3.2:3b").first():
            session.add(LLMModel(
                name="llama3.2:3b",
                api_name="llama3.2:3b",
                description="Llama 3.2 3B — modele local leger (2 GB RAM).",
                entry_tokens=131072,
                sortie_tokens=8192,
            ))
            session.commit()
            print(f"{INFO} Modele llama3.2:3b cree.")
        else:
            print(f"{INFO} Modele llama3.2:3b deja present.")
    except Exception as e:
        print(f"{ERROR} Erreur LLM model : {e}")
        session.rollback()
    finally:
        session.close()


def add_utilisateurs():
    session = get_session()
    try:
        service_ids = [s.serviceId for s in session.query(Service).all()]
        if not service_ids:
            print(f"{WARN} Aucun service trouve.")
            return
        utilisateurs = [
            ("Alice Martin", "alice@regbot.com",  "pass1234", RoleEnum.admin,   choice(service_ids)),
            ("Bob Dupont",   "bob@regbot.com",    "pass1234", RoleEnum.employe, choice(service_ids)),
            ("Clara Leroy",  "clara@regbot.com",  "pass1234", RoleEnum.employe, choice(service_ids)),
            ("David Moreau", "david@regbot.com",  "pass1234", RoleEnum.admin,   choice(service_ids)),
            ("Emma Bernard", "emma@regbot.com",   "pass1234", RoleEnum.employe, choice(service_ids)),
        ]
        for nom, email, pwd, role, service_id in utilisateurs:
            if not session.query(Utilisateur).filter_by(email=email).first():
                session.add(Utilisateur(
                    nom=nom, email=email, mot_de_passe=hash_password(pwd),
                    role=role, service_id=service_id, is_active=True,
                ))
        session.commit()
        print(f"{INFO} Utilisateurs crees avec succes.")
    except Exception as e:
        print(f"{ERROR} Erreur utilisateurs : {e}")
        session.rollback()
    finally:
        session.close()


def add_bots():
    session = get_session()
    try:
        services = session.query(Service).all()
        if not services:
            print(f"{WARN} Aucun service trouve.")
            return
        llm = session.query(LLMModel).filter_by(name="llama3.2:3b").first()
        for service in services:
            if not session.query(Bot).filter_by(service_id=service.serviceId).first():
                session.add(Bot(
                    nom=f"Bot {service.nom}",
                    service_id=service.serviceId,
                    langue="fr",
                    actif=True,
                    llm_model_id=llm.llmId if llm else None,
                ))
        session.commit()
        print(f"{INFO} Bots crees avec succes (llama3.1:8b).")
    except Exception as e:
        print(f"{ERROR} Erreur bots : {e}")
        session.rollback()
    finally:
        session.close()


def add_conversations():
    session = get_session()
    try:
        utilisateurs = session.query(Utilisateur).all()
        if not utilisateurs:
            print(f"{WARN} Aucun utilisateur trouve.")
            return
        sample_exchanges = [
            ("Bonjour, j'ai besoin d'aide.",           MessageTypeEnum.user, None, None),
            ("Bien sur, comment puis-je vous aider ?", MessageTypeEnum.bot,  4,    "Reponse utile"),
            ("Quels sont mes avantages RH ?",          MessageTypeEnum.user, None, None),
            ("Voici la liste de vos avantages...",     MessageTypeEnum.bot,  5,    "Tres complet"),
            ("Merci pour l'information.",              MessageTypeEnum.user, None, None),
        ]
        for utilisateur in utilisateurs:
            bot = session.query(Bot).filter_by(service_id=utilisateur.service_id).first()
            conv = Conversation(
                utilisateur_id=utilisateur.utilisateurId,
                service_id=utilisateur.service_id,
                bot_id=bot.botId if bot else None,
                start_time=datetime.now(UTC),
                status=ConversationStatus.active,
            )
            session.add(conv)
            session.flush()
            for contenu, type_msg, feedback, feedback_text in sample_exchanges:
                session.add(Message(
                    conversation_id=conv.conversationid,
                    contenu=contenu,
                    type_message=type_msg,
                    timestamp=datetime.now(UTC),
                    feedback=feedback,
                    feedback_text=feedback_text,
                    priority=PriorityEnum.medium,
                ))
        session.commit()
        print(f"{INFO} Conversations et messages crees avec succes.")
    except Exception as e:
        print(f"{ERROR} Erreur conversations : {e}")
        session.rollback()
    finally:
        session.close()


def add_smalltalk_messages():
    session = get_session()
    try:
        utilisateurs = session.query(Utilisateur).all()
        if not utilisateurs:
            print(f"{WARN} Aucun utilisateur trouve.")
            return

        for utilisateur in utilisateurs:
            bot = session.query(Bot).filter_by(service_id=utilisateur.service_id).first()
            langue = "fr"
            phrases = SMALLTALK_PATTERN.get(langue, [])
            default_response = DEFAULT_RESPONSES.get(langue)

            conv = Conversation(
                utilisateur_id=utilisateur.utilisateurId,
                service_id=utilisateur.service_id,
                bot_id=bot.botId if bot else None,
                start_time=datetime.now(UTC),
                status=ConversationStatus.active,
            )
            session.add(conv)
            session.flush()

            for phrase in phrases:
                session.add(Message(
                    conversation_id=conv.conversationid,
                    contenu=phrase,
                    type_message=MessageTypeEnum.user,
                    timestamp=datetime.now(UTC),
                    langue=langue,
                    type_question="smalltalk",
                    priority=PriorityEnum.low,
                ))
                session.add(Message(
                    conversation_id=conv.conversationid,
                    contenu=default_response,
                    type_message=MessageTypeEnum.bot,
                    timestamp=datetime.now(UTC),
                    langue=langue,
                    type_question="smalltalk",
                    priority=PriorityEnum.low,
                ))

        session.commit()
        print(f"{INFO} Messages smalltalk inseres avec succes.")
    except Exception as e:
        print(f"{ERROR} Erreur smalltalk : {e}")
        session.rollback()
    finally:
        session.close()


def add_documents():
    session = get_session()
    try:
        services = session.query(Service).all()
        if not services:
            print(f"{WARN} Aucun service trouve.")
            return

        docs_par_service = {
            "RH":           ["Politique des conges", "Procedure de recrutement", "Guide de la paie"],
            "FINANCE":      ["Gestion des factures", "Procedure budgetaire", "Politique de paiement"],
            "TECHNIQUE":    ["Administration des serveurs", "Gestion des incidents", "Plan de maintenance"],
            "JURIDIQUE":    ["Conformite RGPD", "Contrats et engagements", "Procedures disciplinaires"],
            "INFORMATIQUE": ["Charte informatique", "Guide d'utilisation des outils", "Securite des systemes"],
            "DIRECTION":    ["Strategie d'entreprise 2025", "Politique de gouvernance", "Plan de communication interne"],
        }

        for service in services:
            noms = docs_par_service.get(service.nom, [])
            for nom in noms:
                if not session.query(Document).filter_by(name=nom, service_id=service.serviceId).first():
                    session.add(Document(
                        documentId=str(uuid.uuid4()),
                        name=nom,
                        source="local",
                        service_id=service.serviceId,
                    ))
        session.commit()
        print(f"{INFO} Documents crees avec succes.")
    except Exception as e:
        print(f"{ERROR} Erreur documents : {e}")
        session.rollback()
    finally:
        session.close()


# =========================================================
# CLI
# =========================================================
@click.group()
def cli():
    pass


@cli.command()
def rebuild_all_tables():
    """Supprime et recree toutes les tables (DESTRUCTIF)."""
    create_database_if_not_exists()
    enable_pgvector_extension()
    print(f"{INFO} Debut de la reconstruction des tables...")
    drop_everything()
    create_all_tables()
    print(f"{INFO} Reconstruction des tables terminee.")


@cli.command()
def generate_db_data():
    """Genere les donnees de test."""
    print(f"{INFO} Generation des donnees de test...")
    add_llm_models()
    add_utilisateurs()
    add_bots()
    add_conversations()
    add_smalltalk_messages()
    add_documents()
    print(f"{INFO} Generation terminee.")


@cli.command()
def init_db():
    """Initialisation douce sans supprimer l'existant."""
    create_database_if_not_exists()
    enable_pgvector_extension()
    create_all_tables()
    print(f"{INFO} Initialisation terminee.")


if __name__ == "__main__":
    cli()
