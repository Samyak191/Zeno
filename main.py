from crm import save_message, upsert_lead, upsert_order, get_history, get_all_leads, get_orders
from apscheduler.schedulers.background import BackgroundScheduler
from whatsapp_notify import send_daily_report
from pdf_export import generate_leads_pdf
from fastapi.responses import FileResponse
import json
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq
import os, re, uuid, shutil, json

from rag import ingest_pdf, retrieve
from crm import save_message, upsert_lead, get_history, get_all_leads
from config_loader import load_config, build_system_prompt

app  = FastAPI()
# ── scheduler — runs daily at 9am ─────────────────────────────
scheduler = BackgroundScheduler()

def schedule_daily_reports():
    """Load all client configs and schedule their reports"""
    for filename in os.listdir("configs"):
        if not filename.endswith(".json"):
            continue
        with open(f"configs/{filename}") as f:
            config = json.load(f)
        owner_phone = config.get("owner_phone")
        client_id   = config.get("client_id")
        if owner_phone and client_id:
            scheduler.add_job(
                send_daily_report,
                'cron',
                hour=9, minute=0,
                args=[client_id, owner_phone],
                id=client_id,
                replace_existing=True
            )
            print(f"Scheduled daily report for {client_id} → {owner_phone}")

schedule_daily_reports()
scheduler.start()
groq = Groq(api_key=os.environ["GROQ_API_KEY"])

# ── chat endpoint ──────────────────────────────────────────────
@app.post("/chat")
async def chat(
    message:    str = Form(...),
    session_id: str = Form(default=None),
    channel:    str = Form(default="web"),
    client_id:  str = Form(default="demo_client")
):
    if not session_id:
        session_id = str(uuid.uuid4())

    config  = load_config(client_id)
    context = retrieve(message, client_id)
    system  = build_system_prompt(config, context)
    history = get_history(session_id)

    response = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system",    "content": system},
            *history,
            {"role": "user",      "content": message}
        ],
        max_tokens=500,
        temperature=0.4
    )
    reply = response.choices[0].message.content

    save_message(session_id, "user",      message)
    save_message(session_id, "assistant", reply)
    _extract_and_save_lead(session_id, message + " " + reply, channel, config)
    _extract_order_details(session_id, client_id, message + " " + reply)

    return JSONResponse({"reply": reply, "session_id": session_id})



# ── PDF upload ─────────────────────────────────────────────────
@app.post("/upload-doc")
async def upload_doc(
    file:      UploadFile = File(...),
    client_id: str        = Form(default="demo_client")
):
    folder = f"docs/{client_id}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    ingest_pdf(path, client_id)
    return {"status": "ingested", "file": file.filename, "client": client_id}


# ── list docs ─────────────────────────────────────────────────
@app.get("/list-docs")
async def list_docs(client_id: str = "demo_client"):
    folder = f"docs/{client_id}"
    if not os.path.exists(folder):
        return {"files": []}
    files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
    return {"files": files}


# ── list clients ──────────────────────────────────────────────
@app.get("/list-clients")
async def list_clients():
    configs = [
        f.replace(".json", "")
        for f in os.listdir("configs")
        if f.endswith(".json")
    ]
    return {"clients": configs}


# ── widget config (for dynamic branding) ──────────────────────
@app.get("/widget-config")
async def widget_config(client_id: str = "demo_client"):
    config = load_config(client_id)
    return {
        "bot_name":    config.get("bot_name", "Zeno"),
        "brand_color": config.get("brand_color", "#0ACF83"),
        "greeting":    config.get("greeting", "Hi! How can I help?"),
        "client_id":   client_id
    }


# ── admin dashboard ────────────────────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def admin(client_id: str = "demo_client"):
    config = load_config(client_id)
    leads  = get_all_leads()
    clients_raw = [
        f.replace(".json", "")
        for f in os.listdir("configs")
        if f.endswith(".json")
    ]
    client_options = "".join(
        f'<option value="{c}" {"selected" if c == client_id else ""}>{c}</option>'
        for c in clients_raw
    )
    lead_rows = "".join(
        f"<tr><td>{l.name or '—'}</td><td>{l.phone or '—'}</td>"
        f"<td>{l.email or '—'}</td><td>{l.channel}</td>"
        f"<td>{l.created.strftime('%d %b %H:%M')}</td></tr>"
        for l in leads
)

    orders     = get_orders(client_id)
    order_rows = "".join(
        f"<tr>"
        f"<td>{o.customer_name or '—'}</td>"
        f"<td>{o.phone or '—'}</td>"
        f"<td>{o.item or '—'}</td>"
        f"<td>{o.quantity or '—'}</td>"
        f"<td>{o.delivery_date or '—'} {o.delivery_time or ''}</td>"
        f"<td>{o.special_request or '—'}</td>"
        f"<td><span style='color:{'#0ACF83' if o.status == 'pending' else '#aaa'}'>{o.status}</span></td>"
        f"<td>{o.created.strftime('%d %b %H:%M')}</td>"
        f"</tr>"
        for o in orders
)

    brand = config.get("brand_color", "#0ACF83")
    return f"""
    <html><head><title>Zeno Admin — {config['bot_name']}</title>
    <style>
      *{{box-sizing:border-box;margin:0;padding:0}}
      body{{font-family:sans-serif;background:#f5f5f5;padding:2rem}}
      h1{{font-size:1.3rem;font-weight:500;margin-bottom:1.5rem;color:#111}}
      h2{{font-size:.95rem;font-weight:500;margin-bottom:1rem;color:#333}}
      .card{{background:#fff;border-radius:12px;padding:1.5rem;border:1px solid #eee;margin-bottom:1.5rem}}
      .row{{display:flex;gap:12px;align-items:center;margin-bottom:1rem;flex-wrap:wrap}}
      select{{padding:8px 12px;border-radius:8px;border:1px solid #ddd;font-size:13px;background:#fff}}
      .upload-area{{border:2px dashed #ddd;border-radius:8px;padding:1.5rem;text-align:center;cursor:pointer;background:#fafafa}}
      .upload-area:hover{{border-color:{brand}}}
      #file-input{{display:none}}
      #file-name{{font-size:13px;color:{brand};margin-top:6px;font-weight:500}}
      .btn{{padding:9px 20px;background:{brand};color:#fff;border:none;border-radius:8px;font-size:13px;cursor:pointer;margin-top:10px;display:none}}
      .btn:hover{{opacity:.9}}
      .btn:disabled{{background:#aaa;cursor:not-allowed}}
      #status{{margin-top:8px;font-size:13px}}
      .ok{{color:{brand}}}.err{{color:#e53935}}
      .doc-pill{{display:inline-flex;align-items:center;gap:6px;background:#f0faf5;border:1px solid #b2dfcf;border-radius:20px;padding:4px 12px;font-size:12px;color:#0F6E56;margin:4px}}
      table{{width:100%;border-collapse:collapse}}
      th{{background:#f8f8f8;padding:10px 14px;text-align:left;font-size:13px;color:#555;border-bottom:1px solid #eee}}
      td{{padding:10px 14px;font-size:13px;border-bottom:1px solid #f5f5f5;color:#222}}
      .empty{{text-align:center;color:#aaa;padding:2rem;font-size:13px}}
      .config-box{{background:#f8f8f8;border-radius:8px;padding:12px 14px;font-family:monospace;font-size:12px;color:#333;line-height:1.8;overflow-x:auto}}
    </style>
    </head><body>
    <h1>Zeno Admin</h1>

    <div class="card">
      <h2>Active client</h2>
      <div class="row">
        <select onchange="window.location='/admin?client_id='+this.value">{client_options}</select>
        <span style="font-size:13px;color:#888">Viewing: <strong>{config['bot_name']}</strong></span>
      </div>
      <div class="config-box">{json.dumps(config, indent=2)}</div>
    </div>

    <div class="card">
      <h2>Upload documents</h2>
      <div class="upload-area" onclick="document.getElementById('file-input').click()">
        <div style="font-size:1.8rem">📄</div>
        <p style="font-size:13px;color:#888;margin-top:6px">Click to select a PDF</p>
        <div id="file-name"></div>
      </div>
      <input type="file" id="file-input" accept=".pdf" onchange="fileSelected(this)"/>
      <button class="btn" id="upload-btn" onclick="uploadFile()">Upload & ingest</button>
      <div id="status"></div>
    </div>

    <div class="card">
      <h2>Ingested documents</h2>
      <div id="docs-list">{_get_docs_html(client_id)}</div>
    </div>

    <div class="card">
      <h2>Leads — {len(leads)} total</h2>
      <table>
        <tr><th>Name</th><th>Phone</th><th>Email</th><th>Channel</th><th>Time</th></tr>
        {lead_rows if lead_rows else '<tr><td colspan="5" class="empty">No leads yet</td></tr>'}
      </table>
    </div>
    <div class="card">
      <h2>Orders — {len(orders)} total</h2>
      <table>
        <tr>
            <th>Name</th><th>Phone</th><th>Property / Item</th>
            <th>BHK / Qty</th><th>Site Visit / Delivery</th><th>Location / Special request</th>
            <th>Status</th><th>Time</th>
        </tr>
        {order_rows if order_rows else '<tr><td colspan="8" class="empty">No orders yet</td></tr>'}
      </table>
    </div>

    <script>
      const clientId = "{client_id}";
      let selectedFile = null;

      function fileSelected(input) {{
        selectedFile = input.files[0];
        document.getElementById('file-name').textContent = selectedFile.name;
        document.getElementById('upload-btn').style.display = 'inline-block';
        document.getElementById('status').textContent = '';
      }}

      async function uploadFile() {{
        if (!selectedFile) return;
        const btn = document.getElementById('upload-btn');
        btn.disabled = true; btn.textContent = 'Uploading...';
        const form = new FormData();
        form.append('file', selectedFile);
        form.append('client_id', clientId);
        try {{
          const res  = await fetch('/upload-doc', {{method:'POST',body:form}});
          const data = await res.json();
          document.getElementById('status').innerHTML = '<span class="ok">✓ Ingested: ' + data.file + '</span>';
          btn.style.display = 'none';
          document.getElementById('file-name').textContent = '';
          document.getElementById('file-input').value = '';
          selectedFile = null;
          const r2 = await fetch('/list-docs?client_id=' + clientId);
          const d2 = await r2.json();
          document.getElementById('docs-list').innerHTML = d2.files.length
            ? d2.files.map(f => '<span class="doc-pill">📄 ' + f + '</span>').join('')
            : '<p style="color:#aaa;font-size:13px">No documents yet</p>';
        }} catch(e) {{
          document.getElementById('status').innerHTML = '<span class="err">✗ Failed. Try again.</span>';
          btn.disabled = false; btn.textContent = 'Upload & ingest';
        }}
      }}
    </script>
    </body></html>
    """


# ── widget ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def widget():
    return open("widget.html").read()


# ── lead extractor ─────────────────────────────────────────────
def _extract_and_save_lead(session_id, text, channel, config):
    phone = re.search(r"\b[6-9]\d{9}\b", text)
    email = re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text, re.I)
    name  = re.search(r"(?:my name is|i am|i'm|mera naam)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", text)
    upsert_lead(
        session_id,
        name=name.group(1)  if name  else None,
        phone=phone.group() if phone else None,
        email=email.group() if email else None,
        channel=channel
    )


def _get_docs_html(client_id: str):
    folder = f"docs/{client_id}"
    if not os.path.exists(folder):
        return '<p style="color:#aaa;font-size:13px">No documents yet</p>'
    files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
    if not files:
        return '<p style="color:#aaa;font-size:13px">No documents yet</p>'
    return "".join(f'<span class="doc-pill">📄 {f}</span>' for f in files)


# ── PDF download endpoint ──────────────────────────────────────
@app.get("/leads/{client_id}/{filename}")
async def download_leads_pdf(client_id: str, filename: str):
    path = f"exports/{filename}"
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename
    )

# ── manual trigger (for testing) ──────────────────────────────
@app.post("/send-report/{client_id}")
async def trigger_report(client_id: str):
    config = load_config(client_id)
    owner_phone = config.get("owner_phone")
    if not owner_phone:
        return JSONResponse({"error": "No owner_phone in config"}, status_code=400)
    send_daily_report(client_id, owner_phone)
    return {"status": "sent", "to": owner_phone}




def _extract_order_details(session_id: str, client_id: str, conversation: str):
    config   = load_config(client_id)
    industry = config.get("industry", "general")
    if industry not in ["food", "bakery", "restaurant", "realestate", "real estate", "property"]:
        return

    is_realestate = industry in ["realestate", "real estate", "property"]

    if is_realestate:
        extraction_prompt = f"""Extract property lead details from this conversation.
Return ONLY a JSON object with these fields (use null if not found):
{{
  "customer_name": null,
  "phone": null,
  "item": null,
  "quantity": null,
  "delivery_date": null,
  "delivery_time": null,
  "special_request": null,
  "property_type": null,
  "budget": null,
  "location_preference": null,
  "bhk_preference": null,
  "site_visit_date": null,
  "timeline": null
}}

Conversation:
{conversation[-3000:]}

Return ONLY the JSON, nothing else."""
    else:
        extraction_prompt = f"""Extract order details from this conversation.
Return ONLY a JSON object with these fields (use null if not found):
{{
  "customer_name": null,
  "phone": null,
  "item": null,
  "quantity": null,
  "delivery_date": null,
  "delivery_time": null,
  "special_request": null
}}

Conversation:
{conversation[-2000:]}

Return ONLY the JSON, nothing else."""

    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=300,
            temperature=0
        )
        raw  = response.choices[0].message.content.strip()
        raw  = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        upsert_order(
            session_id=session_id,
            client_id=client_id,
            customer_name=data.get("customer_name"),
            phone=data.get("phone"),
            item=data.get("item") or data.get("property_type"),
            quantity=data.get("quantity") or data.get("bhk_preference"),
            delivery_date=data.get("delivery_date") or data.get("site_visit_date"),
            delivery_time=data.get("delivery_time") or data.get("timeline"),
            special_request=data.get("special_request") or data.get("location_preference"),
        )
        if data.get("customer_name") or data.get("phone"):
            upsert_lead(
                session_id=session_id,
                name=data.get("customer_name"),
                phone=data.get("phone"),
                channel="web"
            )
    except Exception as e:
        print(f"Order extraction error: {e}")

    extraction_prompt = f"""Extract order details from this conversation. 
Return ONLY a JSON object with these fields (use null if not found):
{{
  "customer_name": null,
  "phone": null,
  "item": null,
  "quantity": null,
  "delivery_date": null,
  "delivery_time": null,
  "special_request": null
}}

Conversation:
{conversation[-2000:]}

Return ONLY the JSON, nothing else."""

    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=200,
            temperature=0
        )
        raw  = response.choices[0].message.content.strip()
        raw  = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        upsert_order(
            session_id=session_id,
            client_id=client_id,
            customer_name=data.get("customer_name"),
            phone=data.get("phone"),
            item=data.get("item"),
            quantity=data.get("quantity"),
            delivery_date=data.get("delivery_date"),
            delivery_time=data.get("delivery_time"),
            special_request=data.get("special_request")
        )
    except Exception as e:
        print(f"Order extraction error: {e}")