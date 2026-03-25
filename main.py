import os
import csv
import json
import threading
import asyncio
import io
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from huggingface_hub import HfApi, upload_file, list_repo_files, delete_file, hf_hub_download
import tempfile

app = Flask(__name__)

# Hugging Face configuration
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_REPO = "ahashanahmed/csv"
HF_FOLDER = "stock"

class HuggingFaceManager:
    """Hugging Face ফাইল ম্যানেজমেন্ট"""
    
    def __init__(self):
        self.api = HfApi()
        self.repo_id = HF_REPO
        self.token = HF_TOKEN
        self.folder = HF_FOLDER
    
    def get_all_csv_files(self):
        """সব CSV ফাইলের তালিকা"""
        if not self.token:
            return []
        
        try:
            files = list_repo_files(self.repo_id, token=self.token)
            # শুধু stock ফোল্ডারের CSV ফাইল
            csv_files = [f for f in files if f.startswith(f"{self.folder}/") and f.endswith('.csv')]
            # তারিখ বের করা (stock/25-03-2026.csv -> 25-03-2026)
            dates = [f.replace(f"{self.folder}/", "").replace(".csv", "") for f in csv_files]
            return sorted(dates, reverse=True)
        except Exception as e:
            print(f"Error getting files: {e}")
            return []
    
    def read_csv_file(self, date):
        """নির্দিষ্ট তারিখের CSV ফাইল পড়ুন"""
        if not self.token:
            return None
        
        filename = f"{self.folder}/{date}.csv"
        
        try:
            # Check if file exists
            files = list_repo_files(self.repo_id, token=self.token)
            if filename not in files:
                return None
            
            # Download file
            temp_file = hf_hub_download(
                repo_id=self.repo_id,
                filename=filename,
                token=self.token,
                local_dir=tempfile.gettempdir()
            )
            
            # Read CSV
            data = []
            with open(temp_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                data = list(reader)
            
            os.remove(temp_file)
            return data
        except Exception as e:
            print(f"Error reading file: {e}")
            return None
    
    def save_csv_file(self, date, data):
        """CSV ফাইল Hugging Face-এ সেভ করুন"""
        if not self.token:
            return False, "HF_TOKEN সেট নেই!"
        
        filename = f"{self.folder}/{date}.csv"
        
        try:
            # Create CSV in memory
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerows(data)
            csv_content = csv_buffer.getvalue()
            csv_buffer.close()
            
            # Upload to Hugging Face
            upload_file(
                path_or_fileobj=io.BytesIO(csv_content.encode('utf-8-sig')),
                path_in_repo=filename,
                repo_id=self.repo_id,
                token=self.token,
                repo_type="dataset"
            )
            
            return True, f"✅ সেভ হয়েছে: {filename}"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def delete_csv_file(self, date):
        """নির্দিষ্ট তারিখের CSV ফাইল ডিলিট করুন"""
        if not self.token:
            return False, "HF_TOKEN সেট নেই!"
        
        filename = f"{self.folder}/{date}.csv"
        
        try:
            delete_file(
                path_in_repo=filename,
                repo_id=self.repo_id,
                token=self.token,
                repo_type="dataset"
            )
            return True, f"✅ {date}.csv ডিলিট করা হয়েছে।"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def delete_symbol_from_file(self, date, symbol):
        """নির্দিষ্ট ফাইল থেকে নির্দিষ্ট সিম্বল ডিলিট করুন"""
        data = self.read_csv_file(date)
        if data is None:
            return False, f"❌ {date}.csv ফাইল পাওয়া যায়নি।"
        
        if not data:
            return False, f"❌ ফাইলটি খালি।"
        
        # সিম্বল খুঁজে ডিলিট করুন
        original_count = len(data)
        new_data = [row for row in data if row[0].upper() != symbol.upper()]
        deleted_count = original_count - len(new_data)
        
        if deleted_count == 0:
            return False, f"❌ {symbol} সিম্বলটি {date}.csv ফাইলে পাওয়া যায়নি।"
        
        # আপডেটেড ডাটা সেভ করুন
        success, msg = self.save_csv_file(date, new_data)
        if success:
            return True, f"✅ {symbol} ডিলিট করা হয়েছে। {date}.csv ফাইল আপডেট হয়েছে।"
        return False, msg
    
    def search_symbol_all_files(self, symbol):
        """সব ফাইলে সিম্বল খুঁজুন"""
        dates = self.get_all_csv_files()
        results = []
        
        for date in dates:
            data = self.read_csv_file(date)
            if data:
                for row in data:
                    if row[0].upper() == symbol.upper():
                        results.append({
                            'date': date,
                            'row': row
                        })
                        break
        
        return results

# Initialize HF Manager
hf_manager = HuggingFaceManager()

class StockDataBot:
    def __init__(self):
        self.current_data = []
        self.current_date = datetime.now().strftime("%d-%m-%Y")
        self.load_current_data()
    
    def load_current_data(self):
        """আজকের ডাটা লোড করুন"""
        data = hf_manager.read_csv_file(self.current_date)
        if data:
            self.current_data = data
            print(f"Loaded {len(self.current_data)} records for {self.current_date}")
        else:
            self.current_data = []
            print(f"No data for {self.current_date}")
    
    def add_csv_data(self, csv_text):
        """আজকের ডাটায় যোগ করুন"""
        lines = csv_text.strip().split('\n')
        added = 0
        
        for line in lines:
            if not line.strip():
                continue
            row = [item.strip() for item in line.split(',')]
            if len(row) >= 2:
                # Check if symbol already exists in today's data
                exists = any(r[0].upper() == row[0].upper() for r in self.current_data)
                if not exists:
                    self.current_data.append(row)
                    added += 1
        
        if added > 0:
            # Auto-save to HF
            success, msg = hf_manager.save_csv_file(self.current_date, self.current_data)
            if success:
                return f"✅ {added} টি ডাটা যোগ হয়েছে। মোট: {len(self.current_data)} টি\n{msg}"
            else:
                return f"⚠️ {added} টি ডাটা যোগ হয়েছে কিন্তু সেভ করতে পারেনি: {msg}"
        return "❌ কোনো নতুন ডাটা যোগ হয়নি (সিম্বল ডুপ্লিকেট?)"
    
    def clear_current_data(self):
        """আজকের ডাটা ক্লিয়ার করুন"""
        count = len(self.current_data)
        self.current_data = []
        success, msg = hf_manager.save_csv_file(self.current_date, self.current_data)
        if success:
            return f"✅ {count} টি ডাটা মুছে ফেলা হয়েছে।"
        return f"⚠️ ডাটা ক্লিয়ার হয়েছে কিন্তু সেভ করতে পারেনি: {msg}"
    
    def get_preview(self):
        """আজকের ডাটার প্রিভিউ"""
        if not self.current_data:
            return f"📭 {self.current_date} তারিখের কোনো ডাটা নেই।"
        
        preview = f"📊 **{self.current_date} - মোট {len(self.current_data)} টি রেকর্ড:**\n\n"
        for i, row in enumerate(self.current_data[:10]):
            short = ', '.join(row[:3])
            if len(row) > 3:
                short += "..."
            preview += f"{i+1}. {short}\n"
        
        if len(self.current_data) > 10:
            preview += f"\n... এবং {len(self.current_data) - 10} টি বেশি"
        
        return preview

bot = StockDataBot()

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট - Hugging Face স্টোরেজ**\n\n"
        "**ডাটা যোগ:**\n"
        "CSV ফরম্যাটে ডাটা পাঠান:\n"
        "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`\n\n"
        "**ফাইল ম্যানেজমেন্ট:**\n"
        "/files - সব CSV ফাইলের তালিকা\n"
        "/view [তারিখ] - ফাইল দেখুন (যেমন: /view 25-03-2026)\n"
        "/deletefile [তারিখ] - ফাইল ডিলিট করুন\n\n"
        "**সিম্বল ম্যানেজমেন্ট:**\n"
        "/symbols [তারিখ] - ফাইলের সিম্বল দেখুন\n"
        "/deletesymbol [তারিখ] [সিম্বল] - সিম্বল ডিলিট করুন\n"
        "/search [সিম্বল] - সব ফাইলে সিম্বল খুঁজুন\n\n"
        "**আজকের ডাটা:**\n"
        "/list - আজকের ডাটা দেখুন\n"
        "/clear - আজকের ডাটা ক্লিয়ার করুন\n"
        "/status - স্ট্যাটাস দেখুন",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.startswith('/'):
        return
    
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
    """আজকের ডাটা দেখান"""
    preview = bot.get_preview()
    await update.message.reply_text(preview, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আজকের ডাটা ক্লিয়ার"""
    await update.message.reply_text("⚠️ আজকের সব ডাটা মুছে যাবে। /yesclear দিয়ে কনফার্ম করুন।")
    context.user_data['confirm'] = True

async def yesclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('confirm'):
        result = bot.clear_current_data()
        await update.message.reply_text(result)
        context.user_data['confirm'] = False
    else:
        await update.message.reply_text("❌ আগে /clear দিন।")

async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব CSV ফাইলের তালিকা"""
    dates = hf_manager.get_all_csv_files()
    
    if not dates:
        await update.message.reply_text("📭 কোনো CSV ফাইল নেই।")
        return
    
    file_list = "\n".join([f"📄 {date}.csv" for date in dates])
    await update.message.reply_text(
        f"📁 **CSV ফাইলের তালিকা ({len(dates)} টি):**\n\n{file_list}\n\n"
        f"ফাইল দেখতে: `/view [তারিখ]`\n"
        f"ফাইল ডিলিট: `/deletefile [তারিখ]`",
        parse_mode='Markdown'
    )

async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ফাইল দেখান"""
    if not context.args:
        await update.message.reply_text("❌ তারিখ দিন। উদাহরণ: `/view 25-03-2026`", parse_mode='Markdown')
        return
    
    date = context.args[0]
    data = hf_manager.read_csv_file(date)
    
    if data is None:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    if not data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলটি খালি।")
        return
    
    preview = f"📊 **{date}.csv - মোট {len(data)} টি রেকর্ড:**\n\n"
    for i, row in enumerate(data[:10]):
        short = ', '.join(row[:3])
        if len(row) > 3:
            short += "..."
        preview += f"{i+1}. {short}\n"
    
    if len(data) > 10:
        preview += f"\n... এবং {len(data) - 10} টি বেশি"
    
    preview += f"\n\nসিম্বল দেখতে: `/symbols {date}`"
    
    await update.message.reply_text(preview, parse_mode='Markdown')

async def deletefile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ফাইল ডিলিট করুন"""
    if not context.args:
        await update.message.reply_text("❌ তারিখ দিন। উদাহরণ: `/deletefile 25-03-2026`", parse_mode='Markdown')
        return
    
    date = context.args[0]
    
    # কনফার্মেশন
    context.user_data['delete_file'] = date
    await update.message.reply_text(
        f"⚠️ আপনি কি নিশ্চিত? {date}.csv ফাইলটি স্থায়ীভাবে মুছে যাবে!\n"
        f"হ্যাঁ হলে: `/confirmdelete`\nনা হলে: `/cancel`"
    )

async def confirmdelete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ফাইল ডিলিট কনফার্ম"""
    date = context.user_data.get('delete_file')
    if not date:
        await update.message.reply_text("❌ আগে /deletefile দিন।")
        return
    
    success, msg = hf_manager.delete_csv_file(date)
    await update.message.reply_text(msg)
    context.user_data['delete_file'] = None

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ফাইলের সব সিম্বল দেখান"""
    date = context.args[0] if context.args else bot.current_date
    
    data = hf_manager.read_csv_file(date)
    
    if data is None:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    if not data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলটি খালি।")
        return
    
    symbols = [row[0] for row in data]
    symbol_list = "\n".join([f"• {s}" for s in symbols])
    
    await update.message.reply_text(
        f"📋 **{date}.csv - সিম্বল লিস্ট ({len(symbols)} টি):**\n\n{symbol_list}\n\n"
        f"সিম্বল ডিলিট: `/deletesymbol {date} [সিম্বল]`",
        parse_mode='Markdown'
    )

async def deletesymbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ফাইল থেকে নির্দিষ্ট সিম্বল ডিলিট"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ তারিখ এবং সিম্বল দিন। উদাহরণ: `/deletesymbol 25-03-2026 BDCOM`",
            parse_mode='Markdown'
        )
        return
    
    date = context.args[0]
    symbol = context.args[1].upper()
    
    success, msg = hf_manager.delete_symbol_from_file(date, symbol)
    await update.message.reply_text(msg)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব ফাইলে সিম্বল খুঁজুন"""
    if not context.args:
        await update.message.reply_text("❌ সিম্বল দিন। উদাহরণ: `/search BDCOM`", parse_mode='Markdown')
        return
    
    symbol = context.args[0].upper()
    
    await update.message.reply_text(f"🔍 '{symbol}' খুঁজছি... দয়া করে অপেক্ষা করুন।")
    
    results = hf_manager.search_symbol_all_files(symbol)
    
    if not results:
        await update.message.reply_text(f"❌ '{symbol}' কোনো ফাইলে পাওয়া যায়নি।")
        return
    
    result_text = f"🔍 **'{symbol}' পাওয়া গেছে {len(results)} টি ফাইলে:**\n\n"
    for r in results:
        result_text += f"📄 **{r['date']}.csv:**\n"
        result_text += f"   {', '.join(r['row'][:5])}...\n\n"
    
    await update.message.reply_text(result_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্ট্যাটাস দেখান"""
    dates = hf_manager.get_all_csv_files()
    
    status = f"""
📊 **বট স্ট্যাটাস**

📁 Hugging Face: `{HF_REPO}/{HF_FOLDER}/`
🔑 HF_TOKEN: {'✅ সেট আছে' if HF_TOKEN else '❌ সেট নেই'}

📅 আজকের তারিখ: {bot.current_date}
📝 আজকের রেকর্ড: {len(bot.current_data)}

📂 মোট CSV ফাইল: {len(dates)} টি
"""
    if dates:
        status += f"\nসর্বশেষ ৫টি ফাইল:\n"
        for date in dates[:5]:
            status += f"   • {date}.csv\n"
    
    await update.message.reply_text(status, parse_mode='Markdown')

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অপারেশন বাতিল"""
    context.user_data.clear()
    await update.message.reply_text("✅ অপারেশন বাতিল করা হয়েছে।")

# Flask routes
@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "bot": "Stock Data Bot",
        "hf_repo": HF_REPO,
        "today_records": len(bot.current_data),
        "time": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/files')
def get_files():
    return jsonify({"files": hf_manager.get_all_csv_files()})

async def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    try:
        application = Application.builder().token(token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("yesclear", yesclear_command))
        application.add_handler(CommandHandler("files", files_command))
        application.add_handler(CommandHandler("view", view_command))
        application.add_handler(CommandHandler("deletefile", deletefile_command))
        application.add_handler(CommandHandler("confirmdelete", confirmdelete_command))
        application.add_handler(CommandHandler("symbols", symbols_command))
        application.add_handler(CommandHandler("deletesymbol", deletesymbol_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("🤖 Telegram Bot starting...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def start_bot():
        asyncio.run(run_bot())
    
    thread = threading.Thread(target=start_bot, daemon=True)
    thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Flask on port {port}")
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()