from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid

engine = create_engine("sqlite:///crm.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Lead(Base):
    __tablename__ = "leads"
    id       = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name     = Column(String)
    phone    = Column(String)
    email    = Column(String)
    channel  = Column(String)   # "whatsapp" or "web"
    created  = Column(DateTime, default=datetime.utcnow)

class ChatLog(Base):
    __tablename__ = "chatlogs"
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String)
    role       = Column(String)   # "user" or "assistant"
    message    = Column(Text)
    timestamp  = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

def save_message(session_id: str, role: str, message: str):
    db = Session()
    db.add(ChatLog(session_id=session_id, role=role, message=message))
    db.commit()
    db.close()

def upsert_lead(session_id: str, name=None, phone=None, email=None, channel="web"):
    db = Session()
    lead = db.query(Lead).filter_by(id=session_id).first()
    if not lead:
        lead = Lead(id=session_id, channel=channel)
        db.add(lead)
    if name:  lead.name  = name
    if phone: lead.phone = phone
    if email: lead.email = email
    db.commit()
    db.close()

def get_history(session_id: str, limit=10):
    db = Session()
    logs = db.query(ChatLog).filter_by(session_id=session_id)\
              .order_by(ChatLog.timestamp.desc()).limit(limit).all()
    db.close()
    return [{"role": l.role, "content": l.message} for l in reversed(logs)]

def get_all_leads():
    db = Session()
    leads = db.query(Lead).order_by(Lead.created.desc()).all()
    db.close()
    return leads