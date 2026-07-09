import sys
import os
sys.path.append(os.path.abspath("."))

from config import BOT_TOKEN, GROUP_ID, GROUP_ID_STA, GROUP_ID_ABSEN, GROUP_ID_ABSEN_PROV
import telebot

def test_chat(bot, name, chat_id):
    if not chat_id:
        print(f"[{name}] Not configured in .env (empty or None)")
        return
    
    try:
        chat = bot.get_chat(chat_id)
        print(f"[{name}] ID: {chat_id} -> SUCCESS! Title: '{chat.title}', Type: {chat.type}")
    except Exception as e:
        print(f"[{name}] ID: {chat_id} -> FAILED! Error: {e}")

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is not defined in .env!")
        return
        
    bot = telebot.TeleBot(BOT_TOKEN)
    print("Testing configured Group IDs...")
    test_chat(bot, "GROUP_ID", GROUP_ID)
    test_chat(bot, "GROUP_ID_STA", GROUP_ID_STA)
    test_chat(bot, "GROUP_ID_ABSEN", GROUP_ID_ABSEN)
    test_chat(bot, "GROUP_ID_ABSEN_PROV", GROUP_ID_ABSEN_PROV)

if __name__ == "__main__":
    main()
