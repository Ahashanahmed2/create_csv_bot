import os
import csv
import json
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
        """CSV ফরম্যাটে ডাটা যোগ করুন"""
        lines = csv_text.strip().split('\n')
        added = 0
        
        # প্রথম লাইন যদি header হয়, সেটা স্কিপ করুন
        start_line = 0
        if ',' in lines[0] and ('symbol' in lines[0].lower() or 'সিম্বল' in lines[0]):
            start_line = 1
        
        for line in lines[start_line:]:
            if not line.strip():
                continue
            
            # কমা দিয়ে ভাগ করুন
            row = [item.strip() for item in line.split(',')]
            
            # যত কলাম থাকুক, যোগ করুন
            if len(row) >= 2:  # অন্তত 2 টি কলাম থাকতে হবে
                self.stock_data.append(row)
                added += 1
        
        if added > 0:
            self.save_data()
            return f"✅ {added} টি ডাটা যোগ হয়েছে। মোট: {len(self.stock_data)} টি"
        return "❌ কোনো ডাটা যোগ হয়নি। সঠিক CSV ফরম্যাট দিন।"
    
    def save_to_csv(self):
        """সব ডাটা CSV ফাইলে সেভ করুন"""
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
        for i, row in enumerate(self.stock_data[:10]):  # প্রথম 10 টা দেখান
            preview += f"{i+1}. {', '.join(row[:3])}...\n"
        
        if len(self.stock_data) > 10:
            preview += f"\n... এবং {len(self.stock_data) - 10} টি বেশি"
        
        return preview

bot = StockDataBot()

# টেলিগ্রাম হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 স্টক ডাটা বট\n\n"
        "**কীভাবে ব্যবহার করবেন:**\n\n"
        "1️⃣ CSV ফরম্যাটে ডাটা পাঠান:\n"
        "```\nBDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate\nKTL,Corrective (Wave 2),Sub-wave B,9.00-9.40,8.70,10.20,11.50,1:2.0,80,Very High,BUY\n```\n\n"
        "2️⃣ কমান্ড:\n"
        "/list - সব ডাটা দেখুন\n"
        "/save - CSV ফাইলে সেভ করুন\n"
        "/clear - সব ডাটা মুছুন\n"
        "/status - স্ট্যাটাস দেখুন\n\n"
        "**যেকোনো CSV ফরম্যাটেই কাজ করবে!**",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CSV ডাটা গ্রহণ করুন"""
    text = update.message.text
    
    # কমান্ড চেক করুন
    if text.startswith('/'):
        return
    
    # CSV ফরম্যাট চেক করুন (কমা থাকতে হবে)
    if ',' in text:
        await update.message.reply_text("⏳ ডাটা যোগ করা হচ্ছে...")
        result = bot.add_csv_data(text)
        await update.message.reply_text(result)
    else:
        await update.message.reply_text(
            "❌ CSV ফরম্যাটে ডাটা পাঠান। উদাহরণ:\n"
            "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`",
            parse_mode='Markdown'
        )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preview = bot.get_preview()
    await update.message.reply_text(preview)

async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💾 সেভ হচ্ছে...")
    result = bot.save_to_csv()
    await update.message.reply_text(result)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ সব ডাটা মুছে যাবে। /yesclear দিয়ে কনফার্ম করুন।")
    context.user_data['confirm'] = True

async def yesclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('confirm'):
        result = bot.clear_all()
        await update.message.reply_text(result)
        context.user_data['confirm'] = False
    else:
        await update.message.reply_text("❌ আগে /clear দিন।")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = f"/tmp/stock/{current_date}.csv"
    exists = os.path.exists(filename)
    
    status = f"📊 স্ট্যাটাস\n\n"
    status += f"📝 মোট রেকর্ড: {len(bot.stock_data)}\n"
    status += f"📅 আজকের তারিখ: {current_date}\n"
    status += f"📁 CSV ফাইল: {filename}\n"
    status += f"✅ ফাইল আছে: {'হ্যাঁ' if exists else 'না'}"
    
    await update.message.reply_text(status)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("CSV ফরম্যাটে ডাটা পাঠান বা /start দেখুন।")

# Flask routes
@app.route('/')
def home():
    return jsonify({"status": "active", "records": len(bot.stock_data)})

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Token not set!")
        return
    
    app_bot = Application.builder().token(token).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("list", list_command))
    app_bot.add_handler(CommandHandler("save", save_command))
    app_bot.add_handler(CommandHandler("clear", clear_command))
    app_bot.add_handler(CommandHandler("yesclear", yesclear_command))
    app_bot.add_handler(CommandHandler("status", status_command))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.add_handler(MessageHandler(filters.COMMAND, echo))
    
    print("🤖 Bot starting...")
    app_bot.run_polling()

def main():
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask on port {port}")
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()