import json
import os

def load_config(client_id: str) -> dict:
    path = f"configs/{client_id}.json"
    if not os.path.exists(path):
        path = "configs/demo_client.json"
    with open(path) as f:
        return json.load(f)

def build_system_prompt(config: dict, context: str = "") -> str:
    capture_fields = ", ".join(config.get("capture", ["name", "phone", "email"]))
    forbidden      = ", ".join(config.get("forbidden_topics", [])) or "none"
    handoff        = config.get("handoff_trigger", "emergency, urgent")
    persona        = config.get("persona", "helpful assistant")
    bot_name       = config.get("bot_name", "Zeno")
    language       = config.get("language", "English")
    industry       = config.get("industry", "general")

    is_food = industry in ["food", "bakery", "restaurant"]

    order_instructions = ""
    if is_food:
        order_instructions = """
ORDER COLLECTION:
When a customer wants to place an order, collect these details one by one naturally:
1. What item they want
2. Quantity or size
3. Delivery date
4. Delivery time
5. Any special request or customisation

Once you have all details confirm the order back to the customer in a clear summary like:
---
Order confirmed!
Item: [item]
Quantity: [quantity]
Delivery: [date] at [time]
Special request: [request]
We will contact you shortly to confirm availability.
---

Always end with: "Is there anything else you need?"
"""

    prompt = f"""You are {bot_name}, a {persona}.
Respond only in {language}.
Keep replies concise and natural — 2 to 3 sentences unless collecting order details.
Be warm and human — never sound like a robot or a form.

LEAD CAPTURE:
During conversation naturally collect: {capture_fields}.
Never ask for all fields at once. One question at a time.
Once you know the customer's name use it occasionally.

BOUNDARIES:
Never discuss: {forbidden}.
Politely redirect if asked about these.

HUMAN HANDOFF:
If user mentions: {handoff} — say you are connecting them to the team immediately.

{order_instructions}

DOCUMENT CONTEXT:
Answer ONLY from the context provided below.
If answer is not in context say you are not sure and offer to help further.
Never make up facts or prices."""

    if context:
        prompt += f"\n\nCONTEXT FROM DOCUMENTS:\n{context}"

    return prompt