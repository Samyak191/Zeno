import json
import os

def load_config(client_id: str) -> dict:
    path = f"configs/{client_id}.json"
    if not os.path.exists(path):
        path = "configs/demo_client.json"
    with open(path) as f:
        return json.load(f)

def build_system_prompt(config: dict, context: str = "") -> str:
    forbidden  = ", ".join(config.get("forbidden_topics", [])) or "none"
    handoff    = config.get("handoff_trigger", "emergency, urgent")
    persona    = config.get("persona", "helpful assistant")
    bot_name   = config.get("bot_name", "Zeno")
    language   = config.get("language", "English")
    industry   = config.get("industry", "general")

    is_bakery = industry in ["bakery", "food", "restaurant"]

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

🎂 ORDER CONFIRMED!
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

    prompt = f"""You are {bot_name}, a {persona}.
Respond in {language}.

{order_flow}

BOUNDARIES:
Never discuss: {forbidden}.
If asked about anything unrelated to orders, politely say you only handle bakery orders.

HUMAN HANDOFF:
If user mentions: {handoff} — say you are connecting them to the owner immediately.

DOCUMENT CONTEXT:
If menu or pricing info is provided below, use it to answer questions about products and prices.
Never make up prices or products not in the menu."""

    if context:
        prompt += f"\n\nMENU & PRICING:\n{context}"

    return prompt