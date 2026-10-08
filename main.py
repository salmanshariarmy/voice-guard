import time
import os
import asyncio
from pyrogram import Client, raw
from pyrogram.types import ChatPermissions
from flask import Flask
from threading import Thread

# --- কনফিগারেশন ---
API_ID = int(os.environ.get("API_ID", 1234567))          
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")   
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN") 

# কমা (,) দিয়ে একাধিক গ্রুপের ID দেওয়া যাবে
chat_ids_str = os.environ.get("CHAT_IDS", "-1001234567890")
CHAT_LIST = [int(cid.strip()) for cid in chat_ids_str.split(",") if cid.strip()]

MAX_CALL_JOINS = 3   
TIME_WINDOW = 15     
MUTE_DURATION = 20   

app = Client("MultiGroupGuard", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call_history = {}

async def auto_unmute_worker(client, chat_id, target_user_id):
    await asyncio.sleep(MUTE_DURATION)
    try:
        await client.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_user_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        print(f"🔊 UNMUTED: ID {target_user_id} কে গ্রুপ {chat_id} এ আনমিউট করা হয়েছে।")
    except Exception:
        pass

@app.on_raw_update()
async def voice_chat_tracker(client, update, users, chats):
    if isinstance(update, raw.types.UpdateGroupCallParticipants):
        current_time = time.time()
        for participant in update.participants:
            peer = participant.peer
            if getattr(peer, "user_id", None):
                user_id = peer.user_id
                
                if user_id not in call_history:
                    call_history[user_id] = []
                
                call_history[user_id] = [t for t in call_history[user_id] if current_time - t < TIME_WINDOW]
                call_history[user_id].append(current_time)
                
                if len(call_history[user_id]) > MAX_CALL_JOINS:
                    # সব গ্রুপে চেক করে স্প্যামারকে মিউট করবে
                    for chat_id in CHAT_LIST:
                        try:
                            await client.restrict_chat_member(
                                chat_id=chat_id,
                                user_id=user_id,
                                permissions=ChatPermissions() 
                            )
                            print(f"🔇 MUTED: ID {user_id} কে গ্রুপ {chat_id} এ মিউট করা হয়েছে।")
                            asyncio.create_task(auto_unmute_worker(client, chat_id, user_id))
                        except Exception:
                            pass
                    
                    call_history[user_id] = []

# --- ওয়েব সার্ভার ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive and guarding MULTIPLE calls 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    Thread(target=run_web).start()
    app.run()
