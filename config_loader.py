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

    prompt = f"""You are {bot_name}, a {persona}.
Respond only in {language}.
Keep replies concise — 2 to 3 sentences unless more detail is genuinely needed.
Be warm and natural — never sound like a form or a robot.

LEAD CAPTURE:
During the conversation, naturally and gradually collect: {capture_fields}.
Never ask for all fields at once. Ask for one detail only when it fits naturally.
Once you have the user's name, use it occasionally to personalise replies.

BOUNDARIES:
Never discuss: {forbidden}.
If asked about these topics, politely redirect.

HUMAN HANDOFF:
If the user mentions: {handoff} — immediately say you are connecting them to a human and stop responding further.

DOCUMENT CONTEXT:
If context is provided below, answer ONLY from it.
If the answer is not in the context, say you are not sure and offer to help further.
Never make up facts."""

    if context:
        prompt += f"\n\nCONTEXT FROM DOCUMENTS:\n{context}"

    return prompt