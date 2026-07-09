import sys
import os
sys.path.append(os.path.abspath("."))

from config import BOT_TOKEN
import telebot

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is not defined in .env!")
        return
    
    print(f"BOT_TOKEN found: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    bot = telebot.TeleBot(BOT_TOKEN)
    
    try:
        me = bot.get_me()
        print(f"Bot info: ID={me.id}, Username={me.username}, First Name={me.first_name}")
    except Exception as e:
        print(f"Error fetching bot info (get_me): {e}")
        return

    try:
        print("Fetching recent updates (get_updates)...")
        updates = bot.get_updates(limit=100, timeout=1)
        if not updates:
            print("No recent updates found. You might need to send a message to the bot in the group first, or the updates have expired/been read by another session.")
        else:
            print(f"Found {len(updates)} updates:")
            chats_seen = {}
            for u in updates:
                chat = None
                if u.message:
                    chat = u.message.chat
                    text = u.message.text
                    sender = u.message.from_user.username if u.message.from_user else "unknown"
                    print(f"- Message in Chat ID: {chat.id} ({chat.title or chat.username or 'private'}), Type: {chat.type}, From: @{sender}, Text: {text}")
                elif u.callback_query:
                    chat = u.callback_query.message.chat if u.callback_query.message else None
                    data = u.callback_query.data
                    sender = u.callback_query.from_user.username if u.callback_query.from_user else "unknown"
                    if chat:
                        print(f"- Callback in Chat ID: {chat.id} ({chat.title or chat.username or 'private'}), From: @{sender}, Data: {data}")
                
                if chat:
                    chats_seen[chat.id] = chat.title or chat.username or chat.type

            print("\nUnique chats seen in updates:")
            for cid, title in chats_seen.items():
                print(f"  ID: {cid} -> Title/Type: {title}")
    except Exception as e:
        print(f"Error fetching updates: {e}")

if __name__ == "__main__":
    main()
