from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
import uuid, os, re, requests, time, json
from datetime import datetime
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

SESSION_FILE = "insta_session.json"
INFO_API = "https://glob-info.vercel.app/info?uid="
VISTS_API = "https://vists-api.vercel.app/ind/"

cl = Client()
logged_in = False
login_user = ""
last_msg_ids = set()

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
    global logged_in, login_user
    setup_client()
    login_user = username
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
            print("✅ Logged in using saved session.")
            return
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        logged_in = True
        print("✅ Fresh login success.")
    except ChallengeRequired:
        print("🔐 Challenge required. Login on browser first.")
    except Exception as e:
        print(f"❌ Login failed: {e}")

def extract_uid(text, cmd):
    match = re.search(rf"/{cmd}\s+(\d{{5,}})", text.lower())
    return match.group(1) if match else None

def fetch_info(uid):
    try:
        res = requests.get(INFO_API + uid)
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
            f"┌ 👤 ACCOUNT BASIC INFO
"
            f"├─ Name: {b.get('nickname','?')}
"
            f"├─ UID: {uid}
"
            f"├─ Level: {b.get('level','?')} (Exp: {b.get('exp','?')})
"
            f"├─ Region: {b.get('region','?')} | Likes: {b.get('liked','?')}
"
            f"├─ Gender: {s.get('gender','N/A').replace('Gender_', '')}
"
            f"├─ Language: {s.get('language','N/A').replace('Language_', '')}
"
            f"└─ Signature: {s.get('signature','-')}

"
            f"┌ 🎮 ACTIVITY
"
            f"├─ BR Rank: {b.get('rank','?')} ({b.get('rankingPoints','?')})
"
            f"├─ CS Rank: {b.get('csRank','?')}
"
            f"├─ Season: {b.get('seasonId','?')} | OB: {b.get('releaseVersion','?')}
"
            f"├─ Created: {fmt(b.get('createAt', 0))}
"
            f"└─ Last Login: {fmt(b.get('lastLoginAt', 0))}

"
            f"┌ 🛡 CLAN INFO
"
            f"├─ Name: {c.get('clanName','-')}
"
            f"├─ Level: {c.get('clanLevel','-')} | Members: {c.get('memberNum','-')}
"
            f"└─ Leader UID: {c.get('captainId','-')}

"
            f"┌ 🐾 PET INFO
"
            f"├─ Level: {p.get('level','-')} | Exp: {p.get('exp','-')}
"
            f"├─ Skill ID: {p.get('selectedSkillId','-')} | Skin ID: {p.get('skinId','-')}
"
            f"└─ Equipped: {'Yes' if p.get('isSelected', False) else 'No'}

"
            f"┌ 🧩 PROFILE
"
            f"├─ Avatar: {pr.get('avatarId','-')} | Starred: {pr.get('isMarkedStar','-')}
"
            f"├─ Clothes: {', '.join(map(str, pr.get('clothes', [])))}
"
            f"└─ Skills: {', '.join(map(str, pr.get('equipedSkills', [])))}

"
            f"┌ ✅ HONOR
"
            f"└─ Credit Score: {cs.get('creditScore','-')}"
        )
    except Exception as e:
        return f"❌ Error fetching info: {e}"

def fetch_vists(uid):
    try:
        res = requests.get(VISTS_API + uid)
        if res.status_code != 200:
            return f"❌ VISTS API Error: {res.status_code}"
        return res.text.strip()
    except Exception as e:
        return f"❌ Error fetching VISTS data: {e}"

def check_inbox():
    global last_msg_ids
    try:
        inbox = cl.direct_threads(amount=10)
        for thread in inbox:
            messages = cl.direct_messages(thread.id, amount=5)
            for msg in messages:
                if msg.id in last_msg_ids:
                    continue
                last_msg_ids.add(msg.id)
                if msg.text:
                    text = msg.text.strip()
                    if text.lower().startswith("/info"):
                        cl.direct_send("⏳ Please wait while I fetch the data...", thread_ids=[thread.id])
                        uid = extract_uid(text, "info")
                        if uid:
                            reply = fetch_info(uid)
                            cl.direct_send(reply, thread_ids=[thread.id])
                    elif text.lower().startswith("/vists"):
                        cl.direct_send("⏳ Fetching VISTS data, please wait...", thread_ids=[thread.id])
                        uid = extract_uid(text, "vists")
                        if uid:
                            reply = fetch_vists(uid)
                            cl.direct_send(reply, thread_ids=[thread.id])
                    elif "start" in text.lower():
                        cl.direct_send("👋 Hi! You can use the following commands:
"
                                       "/info <UID> — Get Free Fire account info
"
                                       "/vists <UID> — Get VISTS API data", thread_ids=[thread.id])
    except Exception as e:
        print(f"⚠️ Inbox error: {e}")

def start_bot():
    print("🤖 Bot running... instant command processing.")
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
