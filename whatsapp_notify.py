import requests
import os
from datetime import datetime
from pdf_export import generate_leads_pdf
from crm import get_all_leads, Session, Lead
from datetime import timedelta

WATI_API   = os.environ.get("WATI_API_URL")   # e.g. https://live-mt-server.wati.io/YOUR_ID
WATI_TOKEN = os.environ.get("WATI_TOKEN")      # your WATI API token
YOUR_DOMAIN = os.environ.get("YOUR_DOMAIN", "http://127.0.0.1:8000")

def send_whatsapp_message(phone: str, message: str):
    """Send a plain text WhatsApp message via WATI"""
    url     = f"{WATI_API}/api/v1/sendSessionMessage/{phone}"
    headers = {"Authorization": f"Bearer {WATI_TOKEN}", "Content-Type": "application/json"}
    payload = {"messageText": message}
    try:
        res = requests.post(url, json=payload, headers=headers)
        print(f"WATI response: {res.status_code} {res.text}")
    except Exception as e:
        print(f"WATI error: {e}")

def build_daily_message(client_id: str, leads: list, pdf_url: str) -> str:
    date_str = datetime.utcnow().strftime("%d %B %Y")

    if not leads:
        return (
            f"Good morning! 👋\n\n"
            f"No new leads were captured yesterday ({date_str}).\n\n"
            f"Zeno is active and ready for today. Have a great day!"
        )

    lead_lines = ""
    for i, l in enumerate(leads, 1):
        lead_lines += f"\n{i}. {l.name or 'Unknown'}\n"
        if l.phone: lead_lines += f"   📞 {l.phone}\n"
        if l.email: lead_lines += f"   📧 {l.email}\n"
        lead_lines += "\n"

    return (
        f"Good morning! 👋 Here are your leads from {date_str}:\n"
        f"{lead_lines}"
        f"Total: {len(leads)} lead{'s' if len(leads) != 1 else ''}\n\n"
        f"📄 Download full PDF:\n{pdf_url}"
    )

def send_daily_report(client_id: str, owner_phone: str):
    """Generate PDF + send WhatsApp report to business owner"""
    today = datetime.utcnow()

    # get yesterday's leads
    db    = Session()
    start = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    end   = start + timedelta(days=1)
    leads = db.query(Lead).filter(
        Lead.created >= start,
        Lead.created < end
    ).order_by(Lead.created).all()
    db.close()

    # generate PDF
    pdf_path = generate_leads_pdf(client_id, start)
    pdf_filename = os.path.basename(pdf_path)
    pdf_url  = f"{YOUR_DOMAIN}/leads/{client_id}/{pdf_filename}"

    # build and send message
    message = build_daily_message(client_id, leads, pdf_url)
    send_whatsapp_message(owner_phone, message)
    print(f"Daily report sent to {owner_phone} for {client_id}")