import os
import csv
import json
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Flask app for uptime monitoring
app = Flask(__name__)

class StockDataBot:
    def __init__(self):
        self.data_file = "stock_data.json"
        self.stock_data = []
        self.headers = ["symbol", "এলিয়ট ওয়েব (বর্তমান অবস্থান)", "সাব-ওয়েব (বর্তমান অবস্থান)", 
                       "এন্ট্রি জোন (টাকা)", "স্টপ লস (টাকা)", "টেক প্রফিট ১ (টাকা)", 
                       "টেক প্রফিট ২ (টাকা)", "রিস্ক-রিওয়ার্ড অনুপাত (RRR)", 
                       "স্কোর (১০০ এর মধ্যে)", "কনফিডেন্স লেভেল", "অ্যাকশন রিকমেন্ডেশন"]
        
        self.base_path = "/tmp"
        self.stock_folder = os.path.join(self.base_path, "stock")
        self.load_data()
    
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stock_data = data.get('stock_data', [])
                    print(f"✅ Loaded {len(self.stock_data)} records")
            else:
                self.stock_data = []
                print("ℹ️ No existing data")
        except Exception as e:
            print(f"⚠️ Error: {e}")
            self.stock_data = []
    
    def save_data_to_json(self):
        try:
            data = {
                'stock_data': self.stock_data,
                'headers': self.headers,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def ensure_directory(self):
        if not os.path.exists(self.stock_folder):
            os.makedirs(self.stock_folder)
    
    def save_to_csv(self):
        self.ensure_directory()
        if not self.stock_data:
            return "⚠️ কোনো ডাটা নেই"
        
        current_date = datetime.now().strftime("%d-%m-%Y")
        filename = os.path.join(self.stock_folder, f"{current_date}.csv")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(self.headers)
                writer.writerows(self.stock_data)
            self.save_data_to_json()
            return f"✅ সেভ হয়েছে: {filename}\n📊 {len(self.stock_data)} টি রেকর্ড"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def add_bulk_data(self, csv_text):
        lines = csv_text.strip().split('\n')
        added = 0
        errors = []
        
        for i, line in enumerate(lines):
            if i == 0:
                continue
            if not line.strip():
                continue
            
            row_data = [item.strip() for item in line.split(',')]
            
            if len(row_data) != len(self.headers):
                errors.append(f"লাইন {i+1}: {len(row_data)} টি কলাম (প্রয়োজন {len(self.headers)})")
                continue
            
            symbol = row_data[0]
            exists = False
            for existing in self.stock_data:
                if existing[0] == symbol:
                    exists = True
                    break
            
            if exists:
                errors.append(f"লাইন {i+1}: {symbol} ইতিমধ্যে আছে")
            else:
                self.stock_data.append(row_data)
                added += 1
        
        if added > 0:
            self.save_data_to_json()
        
        result = f"✅ {added} টি নতুন স্টক যোগ হয়েছে।\n"
        if errors:
            result += f"\n⚠️ {len(errors)} টি সমস্যা:\n" + "\n".join(errors[:5])
        result += f"\n📊 মোট রেকর্ড: {len(self.stock_data)}"
        
        return result
    
    def add_stock_data(self, row_data):
        if len(row_data) != len(self.headers):
            return f"❌ ভুল ডাটা। {len(self.headers)} টি কলাম প্রয়োজন।"
        
        symbol = row_data[0]
        for existing in self.stock_data:
            if existing[0] == symbol:
                return f"⚠️ {symbol} ইতিমধ্যে আছে।"
        
        self.stock_data.append(row_data)
        self.save_data_to_json()
        return f"✅ {symbol} যোগ হয়েছে। মোট: {len(self.stock_data)}"
    
    def delete_stock_data(self, index):
        if index < 0 or index >= len(self.stock_data):
            return "❌ ভুল ইনডেক্স"
        
        deleted = self.stock_data.pop(index)
        self.save_data_to_json()
        return f"✅ ডিলিট: {deleted[0]}"
    
    def clear_all_data(self):
        count = len(self.stock_data)
        self.stock_data = []
        self.save_data_to_json()
        return f"✅ {count} টি রেকর্ড ক্লিয়ার"
    
    def get_data_preview(self):
        if not self.stock_data:
            return "📭 কোনো ডাটা নেই। /bulk বা /add দিয়ে যোগ করুন।"
        
        preview = f"📊 **মোট {len(self.stock_data)} টি রেকর্ড:**\n\n"
        preview += "```\n"
        preview += f"{'ক্রম':<4} {'সিম্বল':<12} {'স্কোর':<5} {'অ্যাকশন'}\n"
        preview += "-" * 40 + "\n"
        
        for i, row in enumerate(self.stock_data):
            preview += f"{i+1:<4} {row[0]:<12} {row[8]:<5} {row[10]}\n"
        
        preview += "```"
        return preview

bot_instance = StockDataBot()

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 স্টক ডাটা বটে স্বাগতম!\n\n"
        "কমান্ড:\n"
        "/bulk - একসাথে সব ডাটা যোগ করুন\n"
        "/add - একটি ডাটা যোগ করুন\n"
        "/list - সব ডাটা দেখুন\n"
        "/save - CSV ফাইলে সেভ করুন\n"
        "/delete [নম্বর] - ডাটা ডিলিট\n"
        "/clear - সব ডাটা মুছুন\n"
        "/status - স্ট্যাটাস দেখুন\n"
        "/help - সাহায্য"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "সাহায্য গাইড\n\n"
        "একসাথে ডাটা যোগ করুন:\n"
        "/bulk\n"
        "symbol,wave,subwave,entry,stop,tp1,tp2,rrr,score,confidence,action\n"
        "BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate\n\n"
        "একটি ডাটা যোগ করুন:\n"
        "/add BDCOM|Impulse (Wave 4)|Sub-wave C|25.80-26.30|24.90|27.50|29.00|1:1.8|72|High|Accumulate\n\n"
        "সব ডাটা দেখুন: /list\n"
        "CSV সেভ করুন: /save\n"
        "ডাটা ডিলিট: /delete 1\n"
        "স্ট্যাটাস: /status"
    )
    await update.message.reply_text(help_text)

async def bulk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ /bulk কমান্ডের পর আপনার ডাটা পেস্ট করুন।\n\n"
            "ফরম্যাট:\n"
            "/bulk symbol,wave,subwave,entry,stop,tp1,tp2,rrr,score,confidence,action\n"
            "BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate"
        )
        return
    
    full_text = ' '.join(context.args)
    
    if ',' not in full_text:
        await update.message.reply_text("❌ সঠিক ফরম্যাট নয়। কমা (,) দিয়ে আলাদা করে ডাটা দিন।")
        return
    
    await update.message.reply_text("⏳ ডাটা যোগ করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    result = bot_instance.add_bulk_data(full_text)
    await update.message.reply_text(result)

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ /add সিম্বল|ওয়েব|সাব-ওয়েব|এন্ট্রি|স্টপ|টিপি১|টিপি২|আরআরআর|স্কোর|কনফিডেন্স|অ্যাকশন\n\n"
            "উদাহরণ: /add BDCOM|Impulse (Wave 4)|Sub-wave C|25.80-26.30|24.90|27.50|29.00|1:1.8|72|High|Accumulate"
        )
        return
    
    data_str = ' '.join(context.args)
    row_data = [item.strip() for item in data_str.split('|')]
    
    if len(row_data) != 11:
        await update.message.reply_text(f"❌ {len(row_data)} টি কলাম। ১১ টি প্রয়োজন।")
        return
    
    result = bot_instance.add_stock_data(row_data)
    await update.message.reply_text(result)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preview = bot_instance.get_data_preview()
    await update.message.reply_text(preview, parse_mode='Markdown')

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ /delete 1 - ১ নম্বর স্টক ডিলিট হবে")
        return
    
    try:
        index = int(context.args[0]) - 1
        result = bot_instance.delete_stock_data(index)
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("❌ সঠিক নম্বর দিন।")

async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💾 ডাটা সেভ হচ্ছে...")
    result = bot_instance.save_to_csv()
    await update.message.reply_text(result)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ সব ডাটা মুছে যাবে। /yesclear দিয়ে কনফার্ম করুন।")
    context.user_data['confirm_clear'] = True

async def yesclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('confirm_clear'):
        result = bot_instance.clear_all_data()
        await update.message.reply_text(result)
        context.user_data['confirm_clear'] = False
    else:
        await update.message.reply_text("❌ আগে /clear দিন।")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = f"/tmp/stock/{current_date}.csv"
    
    status_text = f"স্ট্যাটাস\n\nরেকর্ড: {len(bot_instance.stock_data)}\nতারিখ: {current_date}\nJSON ফাইল: stock_data.json\nCSV ফাইল: {filename}\n"
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        status_text += f"CSV আছে: {size} bytes"
    else:
        status_text += "CSV এখনো তৈরি হয়নি"
    
    await update.message.reply_text(status_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("সঠিক কমান্ড দিন। /start দেখুন।")

# Flask routes
@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "bot": "Stock Data Bot",
        "records": len(bot_instance.stock_data),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/status')
def get_status():
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = f"/tmp/stock/{current_date}.csv"
    file_exists = os.path.exists(filename)
    
    return jsonify({
        "records": len(bot_instance.stock_data),
        "date": current_date,
        "file_exists": file_exists
    })

def run_telegram_bot():
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("bulk", bulk_command))
        application.add_handler(CommandHandler("add", add_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("delete", delete_command))
        application.add_handler(CommandHandler("save", save_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("yesclear", yesclear_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        print("🤖 Telegram Bot starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()