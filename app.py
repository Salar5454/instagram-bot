from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
import uuid, os, re, requests, time, json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

SESSION_FILE = "insta_session.json"
cl = Client()
logged_in = False
replied_to = set()
welcomed_users = set()  # for sending welcome only once per user

def setup_client():
    cl.set_uuids({
        "uuid": str(uuid.uuid4()),
        "phone_id": str(uuid.uuid4()),
        "client_session_id": str(uuid.uuid4()),
        "advertising_id": str(uuid.uuid4()),
        "device_id": str(uuid.uuid4())
    })

def fmt(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y, %I:%M:%S %p")
    except:
        return "N/A"

def login(username, password):
    global logged_in
    setup_client()
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                s = f.read().strip()
                if not s:
                    os.remove(SESSION_FILE)
                    print("⚠️ Empty session deleted.")
                    return
                cl.set_settings(json.loads(s))
            cl.login(username, password)
            logged_in = True
            print("✅ Logged in via session.")
            return
        cl.login(username, password)
        cl.dump_settings(SESSION_FILE)
        logged_in = True
        print("✅ Fresh login successful.")
    except ChallengeRequired:
        print("🔐 Challenge required.")
    except Exception as e:
        print(f"❌ Login failed: {e}")

def extract_uid(text, cmd="/info"):
    match = re.search(rf"{cmd}\s+(\d+)", text.lower())
    return match.group(1) if match else None

def fetch_info(uid):
    try:
        res = requests.get(f"https://glob-info.vercel.app/info?uid={uid}")
        data = res.json()
        b = data.get("basicInfo", {})
        s = data.get("socialInfo", {})
        c = data.get("clanBasicInfo", {})
        p = data.get("petInfo", {})
        cs = data.get("creditScoreInfo", {})
        pr = data.get("profileInfo", {})

        return f"""┌ 👤 ACCOUNT BASIC INFO
├─ Name: {b.get('nickname','?')}
├─ UID: {uid}
├─ Level: {b.get('level','?')} (Exp: {b.get('exp','?')})
├─ Region: {b.get('region','?')} | Likes: {b.get('liked','?')}
├─ Gender: {s.get('gender','N/A').replace('Gender_', '')}
├─ Language: {s.get('language','N/A').replace('Language_', '')}
└─ Signature: {s.get('signature','-')}

┌ 🎮 ACTIVITY
├─ BR Rank: {b.get('rank','?')} ({b.get('rankingPoints','?')})
├─ CS Rank: {b.get('csRank','?')}
├─ OB: {b.get('releaseVersion','?')}
├─ Created: {fmt(b.get('createAt', 0))}
└─ Last Login: {fmt(b.get('lastLoginAt', 0))}

┌ 🛡 CLAN INFO
├─ Name: {c.get('clanName','-')}
├─ Level: {c.get('clanLevel','-')} | Members: {c.get('memberNum','-')}
└─ Leader UID: {c.get('captainId','-')}

┌ 🐾 PET INFO
├─ Level: {p.get('level','-')} | Exp: {p.get('exp','-')}
├─ Skill ID: {p.get('selectedSkillId','-')} | Skin ID: {p.get('skinId','-')}
└─ Equipped: {'Yes' if p.get('isSelected', False) else 'No'}

┌ 🧩 PROFILE
├─ Avatar: {pr.get('avatarId','-')} | Starred: {pr.get('isMarkedStar','-')}
├─ Clothes: {', '.join(map(str, pr.get('clothes', [])))}
└─ Skills: {', '.join(map(str, pr.get('equipedSkills', [])))}

┌ ✅ HONOR
└─ Credit Score: {cs.get('creditScore','-')}"""
    except Exception as e:
        return f"❌ Error: {e}"

def fetch_vists(uid):
    try:
        res = requests.get(f"https://vists-api.vercel.app/ind/{uid}")
        if res.status_code != 200:
            return "❌ Vists API Error"
        
        data = res.json()
        return f"""📊 VISTS DATA
├─ 👤 Nickname: {data.get("nickname", "-")}
├─ 🆔 UID: {data.get("uid", "-")}
├─ 🗺️ Region: {data.get("region", "-")}
├─ 🆙 Level: {data.get("level", "-")}
├─ 👍 Likes: {data.get("likes", "-")}
├─ ✅ Success: {data.get("success", "-")}
└─ ❌ Fail: {data.get("fail", "-")}
"""
    except Exception as e:
        return f"❌ Vists API error: {e}"


def check_inbox():
    try:
        inbox = cl.direct_threads(amount=10)
        for thread in inbox:
            messages = cl.direct_messages(thread.id, amount=5)
            for msg in messages:
                if not msg.text or msg.id in replied_to:
                    continue
                replied_to.add(msg.id)
                user_id = msg.user_id

                text = msg.text.strip().lower()
                handled = False

                if text.startswith("/info "):
                    uid = extract_uid(text, "/info")
                    if uid:
                        cl.direct_send("⌛ Please wait... fetching Free Fire info.", thread_ids=[thread.id])
                        time.sleep(1)
                        reply = fetch_info(uid)
                        cl.direct_send(reply, thread_ids=[thread.id])
                        print(f"[✅] /info {uid}")
                        handled = True

                elif text.startswith("/vists "):
                    uid = extract_uid(text, "/vists")
                    if uid:
                        cl.direct_send("⌛ Please wait... fetching vists data.", thread_ids=[thread.id])
                        time.sleep(1)
                        reply = fetch_vists(uid)
                        cl.direct_send(reply, thread_ids=[thread.id])
                        print(f"[✅] /vists {uid}")
                        handled = True

                # Only send welcome message once if no command matched
                if not handled and user_id not in welcomed_users:
                    cl.direct_send("👋 Welcome! You can use:\n• /info <uid>\n• /vists <uid>", thread_ids=[thread.id])
                    welcomed_users.add(user_id)

    except Exception as e:
        print(f"⚠️ Error checking inbox: {e}")

def start_bot():
    print("🤖 Bot running... checking inbox every 1s")
    while True:
        check_inbox()
        time.sleep(1)

if __name__ == "__main__":
    print("📲 Insta FF Info Bot")
    if not USERNAME or not PASSWORD:
        print("❌ Missing USERNAME or PASSWORD in .env")
    else:
        login(USERNAME, PASSWORD)
        if logged_in:
            start_bot()
