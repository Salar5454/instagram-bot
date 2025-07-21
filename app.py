from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
import uuid, os, re, requests, time, json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

SESSION_FILE = "insta_session.json"
API_URL = "https://glob-info.vercel.app/info?uid="

cl = Client()
logged_in = False
last_msg_ids = set()
responded_users = set()

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
                    print("⚠️ Empty session file deleted.")
                    return
                cl.set_settings(json.loads(session))
            cl.login(username, password)
            logged_in = True
            print("✅ Logged in with saved session.")
            return
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        logged_in = True
        print("✅ Fresh login success.")
    except ChallengeRequired:
        print("🔐 Challenge required. Login manually on browser.")
    except Exception as e:
        print(f"❌ Login failed: {e}")

def extract_uid(text):
    match = re.search(r"/info\s+(\d{5,})", text.lower())
    return match.group(1) if match else None

def fetch_info(uid):
    try:
        res = requests.get(API_URL + uid)
        if res.status_code != 200:
            return f"❌ API Error: {res.status_code}"

        data = res.json()
        b = data.get("basicInfo", {})
        s = data.get("socialInfo", {})
        c = data.get("clanBasicInfo", {})
        p = data.get("petInfo", {})
        cs = data.get("creditScoreInfo", {})
        pr = data.get("profileInfo", {})

        return (
            f"┌ 👤 ACCOUNT BASIC INFO\n"
            f"├─ Name: {b.get('nickname','?')}\n"
            f"├─ UID: {uid}\n"
            f"├─ Level: {b.get('level','?')} (Exp: {b.get('exp','?')})\n"
            f"├─ Region: {b.get('region','?')} | Likes: {b.get('liked','?')}\n"
            f"├─ Gender: {s.get('gender','N/A').replace('Gender_', '')}\n"
            f"├─ Language: {s.get('language','N/A').replace('Language_', '')}\n"
            f"└─ Signature: {s.get('signature','-')}\n\n"

            f"┌ 🎮 ACTIVITY\n"
            f"├─ BR Rank: {b.get('rank','?')} ({b.get('rankingPoints','?')})\n"
            f"├─ CS Rank: {b.get('csRank','?')}\n"
            f"├─ Season: {b.get('seasonId','?')} | OB: {b.get('releaseVersion','?')}\n"
            f"├─ Created: {fmt(b.get('createAt', 0))}\n"
            f"└─ Last Login: {fmt(b.get('lastLoginAt', 0))}\n\n"

            f"┌ 🛡 CLAN INFO\n"
            f"├─ Name: {c.get('clanName','-')}\n"
            f"├─ Level: {c.get('clanLevel','-')} | Members: {c.get('memberNum','-')}\n"
            f"└─ Leader UID: {c.get('captainId','-')}\n\n"

            f"┌ 🐾 PET INFO\n"
            f"├─ Level: {p.get('level','-')} | Exp: {p.get('exp','-')}\n"
            f"├─ Skill ID: {p.get('selectedSkillId','-')} | Skin ID: {p.get('skinId','-')}\n"
            f"└─ Equipped: {'Yes' if p.get('isSelected', False) else 'No'}\n\n"

            f"┌ 🧩 PROFILE\n"
            f"├─ Avatar: {pr.get('avatarId','-')} | Starred: {pr.get('isMarkedStar','-')}\n"
            f"├─ Clothes: {', '.join(map(str, pr.get('clothes', [])))}\n"
            f"└─ Skills: {', '.join(map(str, pr.get('equipedSkills', [])))}\n\n"

            f"┌ ✅ HONOR\n"
            f"└─ Credit Score: {cs.get('creditScore','-')}"
        )
    except Exception as e:
        return f"❌ Error fetching info: {e}"

def check_inbox():
    global last_msg_ids, responded_users
    try:
        inbox = cl.direct_threads(amount=10)
        for thread in inbox:
            messages = cl.direct_messages(thread.id, amount=5)
            for msg in messages:
                if msg.id in last_msg_ids:
                    continue
                last_msg_ids.add(msg.id)

                sender_id = msg.user_id
                if sender_id not in responded_users:
                    cl.direct_send("👋 Welcome! Send `/info <uid>` to get Free Fire info.", thread_ids=[thread.id])
                    responded_users.add(sender_id)

                if msg.text:
                    uid = extract_uid(msg.text)
                    if uid:
                        reply = fetch_info(uid)
                        cl.direct_send(reply, thread_ids=[thread.id])
                        print(f"[✅] Replied to /info {uid}")
    except Exception as e:
        print(f"⚠️ Inbox error: {e}")

def start_bot():
    print("🤖 Bot is running... Checking inbox.")
    while True:
        check_inbox()
        time.sleep(1)

if __name__ == "__main__":
    print("=== Insta FF Info Bot ===")
    if not USERNAME or not PASSWORD:
        print("❌ Missing USERNAME or PASSWORD in environment.")
    else:
        login(USERNAME, PASSWORD)
        if logged_in:
            start_bot()
