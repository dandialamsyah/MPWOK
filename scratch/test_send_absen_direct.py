import sys
import os
sys.path.append(os.path.abspath("."))

from config import BOT_TOKEN, GROUP_ID_ABSEN, GROUP_ID_ABSEN_PROV
import telebot

def main():
    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...")
    print(f"GROUP_ID_ABSEN: {GROUP_ID_ABSEN}")
    print(f"GROUP_ID_ABSEN_PROV: {GROUP_ID_ABSEN_PROV}")
    
    bot = telebot.TeleBot(BOT_TOKEN)
    
    target_assurance = GROUP_ID_ABSEN
    target_provisioning = GROUP_ID_ABSEN_PROV if GROUP_ID_ABSEN_PROV else GROUP_ID_ABSEN
    
    # 1. Test Assurance
    if target_assurance:
        print(f"Sending test to target_assurance: {target_assurance}")
        try:
            res = bot.send_message(target_assurance, "Test Pengingat Absen (Assurance) dari script testing.")
            print(f"Assurance Send Success! Message ID: {res.message_id}")
        except Exception as e:
            print(f"Assurance Send Failed: {e}")
            
    # 2. Test Provisioning
    if target_provisioning:
        print(f"Sending test to target_provisioning: {target_provisioning}")
        try:
            res = bot.send_message(target_provisioning, "Test Pengingat Absen (Provisioning) dari script testing.")
            print(f"Provisioning Send Success! Message ID: {res.message_id}")
        except Exception as e:
            print(f"Provisioning Send Failed: {e}")

if __name__ == "__main__":
    main()
