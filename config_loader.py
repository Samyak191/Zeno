import json
import os

def load_config(client_id: str) -> dict:
    path = f"configs/{client_id}.json"
    if not os.path.exists(path):
        path = "configs/demo_client.json"
    with open(path) as f:
        return json.load(f)

def build_menu_text(menu: dict) -> str:
    if not menu:
        return ""
    lines = ["\nOUR MENU & PRICING:"]
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for item, details in menu.items():
        if "price_per_kg" in details:
            lines.append(f"{item}")
            lines.append(f"  Price: Rs {details['price_per_kg']}/kg (min {details['min_kg']}kg)")
            lines.append(f"  {details.get('description', '')}")
        elif "price_per_dozen" in details:
            lines.append(f"{item}")
            lines.append(f"  Price: Rs {details['price_per_dozen']}/dozen (min {details['min_dozen']} dozen)")
            lines.append(f"  {details.get('description', '')}")
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def build_system_prompt(config: dict, context: str = "") -> str:
    forbidden     = ", ".join(config.get("forbidden_topics", [])) or "none"
    handoff       = config.get("handoff_trigger", "emergency, urgent")
    persona       = config.get("persona", "helpful assistant")
    bot_name      = config.get("bot_name", "Zeno")
    language      = config.get("language", "English")
    industry      = config.get("industry", "general")
    menu          = config.get("menu", {})

    is_bakery     = industry in ["bakery", "food", "restaurant"]
    is_realestate = industry in ["realestate", "real estate", "property"]

    menu_text     = build_menu_text(menu)

    order_flow = ""
    if is_bakery:
        order_flow = """
YOUR ONLY JOB IS TAKING ORDERS.
Do not talk about appointments, PDFs, documents, or anything unrelated to food orders.

Follow this EXACT order collection sequence, one question at a time:
STEP 1 → Ask: What would you like to order? (cake, cupcakes, cookies, etc.)
STEP 2 → Ask: What flavor or type?
STEP 3 → Ask: What size or quantity?
STEP 4 → Ask: What date do you need it?
STEP 5 → Ask: What time for delivery or pickup?
STEP 6 → Ask: Any special message or design request?
STEP 7 → Ask: Your name please?
STEP 8 → Ask: Your WhatsApp number?

After collecting ALL 8 steps, show this confirmation summary:

ORDER CONFIRMED!
━━━━━━━━━━━━━━━━━━
Item: [item + flavor]
Size/Qty: [quantity]
Date: [date]
Time: [time]
Special request: [request]
Name: [name]
Phone: [phone]
━━━━━━━━━━━━━━━━━━
We will confirm availability within 2 hours. Thank you!

RULES:
- Ask ONLY ONE question at a time
- Never ask for email
- Never skip a step
- Never combine two questions in one message
- Be warm and friendly throughout
- Use the customer's name once you know it
"""

    realestate_flow = ""
    if is_realestate:
        realestate_flow = """
YOUR JOB IS QUALIFYING PROPERTY BUYERS AND CAPTURING LEADS.

Follow this sequence one question at a time:
STEP 1 → Ask: Are you looking to buy, rent, or invest?
STEP 2 → Ask: What type of property? (Builder floor, plot, flat, villa)
STEP 3 → Ask: Which location or sector do you prefer?
STEP 4 → Ask: What is your budget range?
STEP 5 → Ask: How many BHK do you need?
STEP 6 → Ask: When are you looking to buy? (Timeline)
STEP 7 → Ask: Would you like to schedule a site visit?
STEP 8 → Ask: Your name please?
STEP 9 → Ask: Your WhatsApp number?

After ALL steps show this summary:

LEAD CAPTURED!
━━━━━━━━━━━━━━━━━━
Type: [buy/rent/invest]
Property: [type]
Location: [preference]
Budget: [budget]
BHK: [bhk]
Timeline: [timeline]
Site visit: [date or TBD]
Name: [name]
Phone: [phone]
━━━━━━━━━━━━━━━━━━
Our agent will call you within 2 hours!

RULES:
- One question at a time
- Be professional and confident
- If they mention a specific budget suggest it is a good range
- Never discuss commission or agency fees
- If they say ready to buy or serious — trigger human handoff immediately
"""

    prompt = f"""You are {bot_name}, a {persona}.
Respond in {language} only. Never use any other language.

{order_flow}
{realestate_flow}
{menu_text}

BOUNDARIES:
Never discuss: {forbidden}.
If asked about anything unrelated to your job, politely redirect.

HUMAN HANDOFF:
If user mentions: {handoff} — say you are connecting them to the team immediately.

DOCUMENT CONTEXT:
Answer questions using the context provided below.
Never make up facts, prices, or properties not in the context."""

    if context:
        prompt += f"\n\nCONTEXT:\n{context}"

    return prompt