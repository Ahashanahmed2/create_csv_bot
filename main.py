import os
import csv
import json
import threading
from datetime import datetime
from flask import Flask, jsonify
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

app = Flask(__name__)

class StockDataBot:
    def __init__(self):
        self.data_file = "stock_data.json"
        self.stock_data = []
        self.stock_folder = "/tmp/stock"
        self.load_data()
    
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stock_data = data.get('stock_data', [])
                    print(f"Loaded {len(self.stock_data)} records")
        except Exception as e:
            print(f"Error: {e}")
            self.stock_data = []
    
    def save_data(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({'stock_data': self.stock_data}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def add_csv_data(self, csv_text):
        lines = csv_text.strip().split('\n')
        added = 0
        
        for line in lines:
            if not line.strip():
                continue
            row = [item.strip() for item in line.split(',')]
            if len(row) >= 2:
                self.stock_data.append(row)
                added += 1
        
        if added > 0:
            self.save_data()
            return f"✅ {added} টি ডাটা যোগ হয়েছে। মোট: {len(self.stock_data)} টি"
        return "❌ কোনো ডাটা যোগ হয়নি।"
    
    def save_to_csv(self):
        if not self.stock_data:
            return "⚠️ কোনো ডাটা নেই"
        
        if not os.path.exists(self.stock_folder):
            os.makedirs(self.stock_folder)
        
        current_date = datetime.now().strftime("%d-%m-%Y")
        filename = f"{self.stock_folder}/{current_date}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(self.stock_data)
            return f"✅ সেভ হয়েছে: {filename}\n📊 {len(self.stock_data)} টি রেকর্ড"
        except Exception as e:
            return f"❌ Error: {e}"
    
    def clear_all(self):
        count = len(self.stock_data)
        self.stock_data = []
        self.save_data()
        return f"✅ {count} টি ডাটা মুছে ফেলা হয়েছে"
    
    def get_preview(self):
        if not self.stock_data:
            return "📭 কোনো ডাটা নেই। CSV ফরম্যাটে ডাটা পাঠান।"
        
        preview = f"📊 মোট {len(self.stock_data)} টি রেকর্ড:\n\n"
        for i, row in enumerate(self.stock_data[:10]):
            short = ', '.join(row[:3])
            if len(row) > 3:
                short += "..."
            preview += f"{i+1}. {short}\n"
        
        if len(self.stock_data) > 10:
            preview += f"\n... এবং {len(self.stock_data) - 10} টি বেশি"
        
        return preview

bot = StockDataBot()

def start(update, context):
    update.message.reply_text(
        "🤖 স্টক ডাটা বট\n\n"
        "কীভাবে ব্যবহার করবেন:\n\n"
        "1️⃣ CSV ফরম্যাটে ডাটা পাঠান:\n"
        "BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate\n\n"
        "2️⃣ কমান্ড:\n"
        "/list - সব ডাটা দেখুন\n"
        "/save - CSV ফাইলে সেভ করুন\n"
        "/clear - সব ডাটা মুছুন\n"
        "/status - স্ট্যাটাস দেখুন"
    )

def handle_message(update, context):
    text = update.message.text
    
    if text.startswith('/'):
        return
    
    if ',' in text:
        update.message.reply_text("⏳ ডাটা যোগ করা হচ্ছে...")
        result = bot.add_csv_data(text)
        update.message.reply_text(result)
    else:
        update.message.reply_text(
            "❌ CSV ফরম্যাটে ডাটা পাঠান। উদাহরণ:\n"
            "BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate"
        )

def list_command(update, context):
    preview = bot.get_preview()
    update.message.reply_text(preview)

def save_command(update, context):
    update.message.reply_text("💾 সেভ হচ্ছে...")
    result = bot.save_to_csv()
    update.message.reply_text(result)

def clear_command(update, context):
    update.message.reply_text("⚠️ সব ডাটা মুছে যাবে। /yesclear দিয়ে কনফার্ম করুন।")
    context.user_data['confirm'] = True

def yesclear_command(update, context):
    if context.user_data.get('confirm'):
        result = bot.clear_all()
        update.message.reply_text(result)
        context.user_data['confirm'] = False
    else:
        update.message.reply_text("❌ আগে /clear দিন।")

def status_command(update, context):
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = f"/tmp/stock/{current_date}.csv"
    exists = os.path.exists(filename)
    
    status = f"📊 স্ট্যাটাস\n\n"
    status += f"📝 মোট রেকর্ড: {len(bot.stock_data)}\n"
    status += f"📅 আজকের তারিখ: {current_date}\n"
    status += f"📁 CSV ফাইল: {filename}\n"
    status += f"✅ ফাইল আছে: {'হ্যাঁ' if exists else 'না'}"
    
    update.message.reply_text(status)

def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Token not set!")
        return
    
    try:
        updater = Updater(token, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("list", list_command))
        dp.add_handler(CommandHandler("save", save_command))
        dp.add_handler(CommandHandler("clear", clear_command))
        dp.add_handler(CommandHandler("yesclear", yesclear_command))
        dp.add_handler(CommandHandler("status", status_command))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        
        print("🤖 Telegram Bot starting...")
        updater.start_polling()
        updater.idle()
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask on port {port}")
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()