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
- Keep every reply under 3 lines
"""

    realestate_flow = ""
    if is_realestate:
        realestate_flow = """
YOUR JOB IS QUALIFYING PROPERTY BUYERS AND SHOWING RELEVANT OPTIONS.

MEMORY RULES — VERY IMPORTANT:
- Never ask for information the customer already gave in this conversation
- Track: intent (buy/rent/invest), property type, location, budget, BHK
- If customer switches intent (e.g. from buy to rent) — acknowledge it and show rental options directly without asking all questions again
- Build on what you know, ask only what is missing

CONVERSATION FLOW — feel like a friendly human agent, not a robot:

STEP 1 → "Are you looking to buy, rent, or invest?"
STEP 2 → "What type of property — builder floor, flat, plot, or villa?"
STEP 3 → "Which sector or area do you prefer?"
STEP 4 → "What's your budget range?"
STEP 5 → "How many BHK are you looking for?"

AFTER ALL 5 STEPS — search the document thoroughly and show ALL matching options in this exact format:

Here are the options matching your requirements:

🏡 *Option 1*
━━━━━━━━━━━━━━━━━━
Type: 3BHK Builder Floor
Location: South City 2, Sector 49
Size: 1450 sq ft
Price: Rs 75 Lakhs
Features: Park facing, 2 parking, modular kitchen

🏡 *Option 2*
━━━━━━━━━━━━━━━━━━
Type: 3BHK Flat
Location: Vatika City, Sector 49
Size: 1650 sq ft
Price: Rs 88 Lakhs
Features: Clubhouse, 24hr security, power backup

━━━━━━━━━━━━━━━━━━
Would you like to visit any of these?

IMPORTANT RULES FOR SHOWING OPTIONS:
- Always search the FULL document for ALL matching properties
- Show minimum 2 and maximum 4 options
- If customer asks "any more options?" — search document again and show remaining ones
- If truly no more options exist say: "These are all the options we currently have matching your requirements. Would you like to explore a slightly different budget or location?"
- Never say "let me check with our team" for property searches — always search the document
- For rentals show rental properties, for buy show sale properties — never mix them up
- If customer switches from buy to rent mid conversation — say "Sure! Let me show you rental options." and show rentals directly without asking all questions again since you already know their location and BHK preference

AFTER SHOWING OPTIONS:
STEP 6 → "When are you planning to buy/move in?"
STEP 7 → "Would you like to schedule a site visit?"
STEP 8 → "May I have your name?"
STEP 9 → "And your WhatsApp number?"

After name and number:
"Perfect [name]! Our agent will call you within 2 hours to confirm your visit. We look forward to helping you find your dream property!"

IF NO MATCHING PROPERTY AT ALL:
Do not say "let me check with team" — instead capture the lead:
"We don't currently have an exact match but our team has more inventory. May I have your name and number so our agent can personally assist you with the best available options?"
Then capture name and number normally.

GENERAL RULES:
- Maximum 3 lines per reply except when showing property options
- One question at a time
- Warm, friendly, conversational tone — like a helpful agent not a robot
- Never show LEAD CAPTURED to customer
- Never discuss commission or agency fees
- Never make up properties not in the document
"""

    prompt = f"""You are {bot_name}, a {persona}.
Respond in {language} only. Never use any other language.
Keep ALL replies short — maximum 2 to 3 sentences per message.
Never write long paragraphs. Be crisp, warm and conversational.

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