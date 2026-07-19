import json
import os
import random
import time
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from ai_core.rag import search_knowledge_base
from ai_core.memory import profile_store, conversation_buffer


def _detect_personal_info(text: str) -> dict:
    text_lower = text.lower()
    info = {}
    if "my name is" in text_lower:
        name = text.split("my name is")[-1].split(".")[0].strip().split(",")[0].strip()
        if name and len(name.split()) <= 4:
            info["name"] = name
    for phrase, key in [
        ("i live in ", "city"), ("i work as ", "profession"),
        ("my favorite food ", "favorite_food"), ("i enjoy ", "hobby"),
        ("my hobby ", "hobby"), ("i am from ", "city"),
    ]:
        if phrase in text_lower:
            val = text.split(phrase)[-1].split(".")[0].strip().split(",")[0].strip()
            if val and len(val) < 60:
                info[key] = val
    if "years old" in text_lower:
        parts = text_lower.split("i am ") if "i am " in text_lower else text_lower.split("i'm ")
        if len(parts) > 1:
            age_str = parts[-1].split("years old")[0].strip().split()[-1]
            try:
                int(age_str); info["age"] = age_str
            except ValueError: pass
    return info


@tool
def search_clinic_info(query: str) -> str:
    """Search the clinic knowledge base for services, hours, pricing, policies. Use when user asks about clinic offerings."""
    results = search_knowledge_base(query)
    return "\n\n".join(results) if results else "No relevant info found."


@tool
def update_user_profile(info: str) -> str:
    """Store personal facts about the user. Pass JSON like {"name": "John", "age": "30"}."""
    try:
        data = json.loads(info)
        uid = _get_current_user_id()
        if uid:
            profile_store.update_profile(uid, data)
            return f"Saved {', '.join(data.keys())} to memory."
        return "No user context."
    except json.JSONDecodeError:
        return "Invalid JSON format."


@tool
def get_user_profile() -> str:
    """Retrieve everything the bot remembers about the current user. Use for 'What do you know about me?' queries."""
    uid = _get_current_user_id()
    if not uid: return "No user context."
    profile = profile_store.get_profile(uid)
    cleaned = {k: v for k, v in profile.items() if not k.startswith("_")}
    if not cleaned: return "I don't know anything about you yet."
    lines = [f"  * {k.replace('_', ' ').title()}: {v}" for k, v in cleaned.items()]
    return "Here's what I remember:\n" + "\n".join(lines)


_current_user_id = None

def _get_current_user_id():
    return _current_user_id

def _set_current_user_id(uid):
    global _current_user_id; _current_user_id = uid


SYSTEM_PROMPT = """You are a CityCare Clinic assistant. Guidelines:
1. Use search_clinic_info for clinic questions (hours, pricing, services).
2. Use update_user_profile when user shares personal facts (name, age, etc.).
3. Use get_user_profile when user asks 'What do you know about me?'.
4. For greetings/small talk, respond naturally without tools.
5. Be concise and friendly.

User info context: {detected}
History: {history}"""


def create_agent():
    llm = ChatOpenAI(model="auto", temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENAI_BASE_URL"))
    return create_react_agent(llm, [search_clinic_info, update_user_profile, get_user_profile])


def run_agent(user_id: str, message: str) -> str:
    _set_current_user_id(user_id)
    detected = _detect_personal_info(message)
    if detected:
        profile_store.update_profile(user_id, detected)
    history = conversation_buffer.get_history(user_id)
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-5:])
    
    response = create_agent().invoke({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(
                detected=json.dumps(detected) if detected else "None",
                history=history_text)},
            {"role": "user", "content": message},
        ]
    })
    reply = response["messages"][-1].content
    conversation_buffer.add_message(user_id, "user", message)
    conversation_buffer.add_message(user_id, "assistant", reply)
    time.sleep(random.uniform(2, 5))
    return reply
