import os, re, json, uuid, time, requests
from datetime import datetime
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
from dotenv import load_dotenv

load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

SESSION_FILE = "insta_session.json"
INFO_API = "https://glob-info.vercel.app/info?uid="
VISTS_API = "https://vists-api.vercel.app/ind/"

cl = Client()
logged_in = False
last_msg_ids = set()
welcomed_users = set()

def setup_client():
    cl.set_uuids({
        "uuid": str(uuid.uuid4()),
        "phone_id": str(uuid.uuid4()),
        "client_session_id": str(uuid.uuid4()),
        "advertising_id": str(uuid.uuid4()),
        "device_id": str(uuid.uuid4())
    })

def fmt(ts):
    return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y, %I:%M:%S %p") if ts else "N/A"

def login(username, password):
    global logged_in
    setup_client()
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                session = f.read().strip()
                if not session:
                    os.remove(SESSION_FILE)
                    print("⚠️ Empty session deleted.")
                    return
                cl.set_settings(json.loads(session))
            cl.login(username, password)
            logged_in = True
            print("✅ Logged in using saved session.")
            return
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        logged_in = True
        print("✅ Fresh login success.")
    except ChallengeRequired:
        print("🔐 Challenge required. Login manually.")
    except Exception as e:
        print(f"❌ Login failed: {e}")

def extract_uid(text, command="/info"):
    match = re.search(rf"{re.escape(command)}\s+(\d+)", text.lower())
    return match.group(1) if match else None

def fetch_info(uid):
    try:
        res = requests.get(INFO_API + uid)
        if res.status_code != 200:
            return f"❌ Info API Error: {res.status_code}"
        d = res.json()
        b, s, c, p, cs, pr = map(d.get, ["basicInfo", "socialInfo", "clanBasicInfo", "petInfo", "creditScoreInfo", "profileInfo"])
        return (
            f"👤 ACCOUNT\n"
            f"• Name: {b.get('nickname','?')} | UID: {uid}\n"
            f"• Level: {b.get('level')} (Exp: {b.get('exp')}) | Likes: {b.get('liked')}\n"
            f"• Region: {b.get('region')} | Rank: {b.get('rank')} ({b.get('rankingPoints')})\n"
            f"• Signature: {s.get('signature','-')}\n"
            f"• Last Login: {fmt(b.get('lastLoginAt',0))} | Created: {fmt(b.get('createAt',0))}\n\n"
            f"🛡 CLAN\n"
            f"• {c.get('clanName','-')} (Level {c.get('clanLevel','-')}) | Members: {c.get('memberNum','-')}\n\n"
            f"🐾 PET\n"
            f"• Level: {p.get('level')} | Skill: {p.get('selectedSkillId')} | Equipped: {p.get('isSelected')}\n\n"
            f"✅ HONOR\n"
            f"• Credit Score: {cs.get('creditScore','-')}"
        )
    except Exception as e:
        return f"❌ Error fetching info: {e}"

def fetch_vists(uid):
    try:
        res = requests.get(VISTS_API + uid)
        if res.status_code != 200:
            return f"❌ Vists API Error: {res.status_code}"
        d = res.json()
        return (
            f"📊 VISTS SUMMARY\n"
            f"• Name: {d.get('nickname', '-')}\n"
            f"• UID: {d.get('uid', '-')}\n"
            f"• Region: {d.get('region', '-')}\n"
            f"• Level: {d.get('level', '-')}\n"
            f"• Likes: {d.get('likes', '-'):,}\n"
            f"• Success: {d.get('success')} ✅ | Fail: {d.get('fail')} ❌"
        )
    except Exception as e:
        return f"❌ Error fetching vists info: {e}"

def check_inbox():
    global last_msg_ids
    try:
        inbox = cl.direct_threads(amount=10)
        for thread in inbox:
            user_id = thread.users[0].pk if thread.users else None
            messages = cl.direct_messages(thread.id, amount=5)

            for msg in messages:
                if msg.id in last_msg_ids:
                    continue
                last_msg_ids.add(msg.id)

                text = msg.text.strip().lower()

                if user_id and user_id not in welcomed_users:
                    cl.direct_send("👋 Welcome! Use /info <uid> or /vists <uid>", thread_ids=[thread.id])
                    welcomed_users.add(user_id)

                if text.startswith("/info "):
                    uid = extract_uid(text, "/info")
                    if uid:
                        cl.direct_send(fetch_info(uid), thread_ids=[thread.id])
                        print(f"[✅] /info {uid}")
                        break

                elif text.startswith("/vists "):
                    uid = extract_uid(text, "/vists")
                    if uid:
                        cl.direct_send(fetch_vists(uid), thread_ids=[thread.id])
                        print(f"[✅] /vists {uid}")
                        break
    except Exception as e:
        print(f"⚠️ Inbox error: {e}")

def start_bot():
    print("🤖 Bot is running... instant reply enabled.")
    while True:
        check_inbox()

if __name__ == "__main__":
    print("=== Insta FF Info Bot ===")
    if not USERNAME or not PASSWORD:
        print("❌ Missing USERNAME or PASSWORD in .env.")
    else:
        login(USERNAME, PASSWORD)
        if logged_in:
            start_bot()
