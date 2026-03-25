import os
import csv
import json
import threading
import asyncio
import io
import tempfile
import re
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from huggingface_hub import HfApi, upload_file, list_repo_files, delete_file, hf_hub_download

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
        self.repo_type = "dataset"
        print(f"🔧 HF Manager initialized")
        print(f"   Repo: {self.repo_id}")
        print(f"   Type: {self.repo_type}")
        print(f"   Token: {'✅ Yes' if self.token else '❌ No'}")
        print(f"   Folder: {self.folder}")
    
    def get_all_csv_files(self):
        """সব CSV ফাইলের তালিকা"""
        if not self.token:
            print("❌ No HF_TOKEN!")
            return []
        
        try:
            print(f"🔍 Fetching files from {self.repo_id}...")
            files = list_repo_files(self.repo_id, token=self.token, repo_type=self.repo_type)
            print(f"📁 Total files in repo: {len(files)}")
            
            csv_files = [f for f in files if f.startswith(f"{self.folder}/") and f.endswith('.csv')]
            print(f"📄 CSV files in {self.folder}: {len(csv_files)}")
            
            for f in csv_files[:5]:
                print(f"   - {f}")
            
            dates = [f.replace(f"{self.folder}/", "").replace(".csv", "") for f in csv_files]
            return sorted(dates, reverse=True)
            
        except Exception as e:
            print(f"❌ Error getting files: {e}")
            return []
    
    def read_csv_file(self, date):
        """নির্দিষ্ট তারিখের CSV ফাইল পড়ুন"""
        if not self.token:
            print("❌ No HF_TOKEN!")
            return None
        
        filename = f"{self.folder}/{date}.csv"
        print(f"🔍 Looking for: {filename}")
        
        try:
            files = list_repo_files(self.repo_id, token=self.token, repo_type=self.repo_type)
            if filename not in files:
                print(f"❌ File not found: {filename}")
                return None
            
            print(f"✅ File found, downloading...")
            
            temp_file = hf_hub_download(
                repo_id=self.repo_id,
                filename=filename,
                token=self.token,
                repo_type=self.repo_type,
                local_dir=tempfile.gettempdir()
            )
            
            data = []
            with open(temp_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                data = list(reader)
            
            os.remove(temp_file)
            print(f"✅ Loaded {len(data)} records from {filename}")
            return data
            
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return None
    
    def save_csv_file(self, date, data):
        """CSV ফাইল Hugging Face-এ সেভ করুন"""
        if not self.token:
            return False, "HF_TOKEN সেট নেই!"
        
        filename = f"{self.folder}/{date}.csv"
        
        try:
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerows(data)
            csv_content = csv_buffer.getvalue()
            csv_buffer.close()
            
            upload_file(
                path_or_fileobj=io.BytesIO(csv_content.encode('utf-8-sig')),
                path_in_repo=filename,
                repo_id=self.repo_id,
                token=self.token,
                repo_type=self.repo_type
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
                repo_type=self.repo_type
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
        
        # Check if first row is header
        start_idx = 0
        if data and data[0] and len(data[0]) > 0 and ('symbol' in data[0][0].lower() or 'সিম্বল' in data[0][0]):
            start_idx = 1
        
        original_count = len(data) - start_idx
        new_data = data[:start_idx]  # Keep header if exists
        deleted_count = 0
        
        for row in data[start_idx:]:
            if row and len(row) > 0 and row[0].upper() != symbol.upper():
                new_data.append(row)
            else:
                deleted_count += 1
        
        if deleted_count == 0:
            return False, f"❌ {symbol} সিম্বলটি {date}.csv ফাইলে পাওয়া যায়নি।"
        
        success, msg = self.save_csv_file(date, new_data)
        if success:
            return True, f"✅ {symbol} ডিলিট করা হয়েছে। {date}.csv ফাইল আপডেট হয়েছে। (ডিলিট: {deleted_count} টি)"
        return False, msg
    
    def search_symbol_all_files(self, symbol):
        """সব ফাইলে সিম্বল খুঁজুন - উন্নত ভার্সন"""
        dates = self.get_all_csv_files()
        results = []
        
        for date in dates:
            data = self.read_csv_file(date)
            if data and len(data) > 0:
                # Check if first row is header
                start_idx = 0
                if data[0] and len(data[0]) > 0 and ('symbol' in data[0][0].lower() or 'সিম্বল' in data[0][0]):
                    start_idx = 1
                
                for idx, row in enumerate(data[start_idx:]):
                    if row and len(row) > 0 and row[0].upper() == symbol.upper():
                        results.append({
                            'date': date,
                            'row': row,
                            'line': start_idx + idx + 1
                        })
                        break  # Found in this file, move to next
        
        return results

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
            # Check if first row is header
            start_idx = 0
            if data and data[0] and len(data[0]) > 0 and ('symbol' in data[0][0].lower() or 'সিম্বল' in data[0][0]):
                start_idx = 1
            self.current_data = data[start_idx:]
            print(f"Loaded {len(self.current_data)} records for {self.current_date}")
        else:
            self.current_data = []
            print(f"No data for {self.current_date}")
    
    def add_csv_data(self, csv_text):
        """আজকের ডাটায় যোগ করুন"""
        lines = csv_text.strip().split('\n')
        added = 0
        duplicate_skipped = 0
        
        # Check if current data has header
        has_header = False
        if self.current_data:
            first_row = self.current_data[0] if self.current_data else None
            if first_row and len(first_row) > 0 and ('symbol' in first_row[0].lower() or 'সিম্বল' in first_row[0]):
                has_header = True
        
        for line in lines:
            if not line.strip():
                continue
            row = [item.strip() for item in line.split(',')]
            if len(row) >= 2:
                # Check if symbol already exists
                exists = False
                for existing in self.current_data:
                    if existing and len(existing) > 0 and existing[0].upper() == row[0].upper():
                        exists = True
                        duplicate_skipped += 1
                        break
                
                if not exists:
                    self.current_data.append(row)
                    added += 1
        
        if added > 0:
            # Add header if needed
            if not has_header and self.current_data:
                headers = ["symbol", "এলিয়ট ওয়েব (বর্তমান অবস্থান)", "সাব-ওয়েব (বর্তমান অবস্থান)", 
                          "এন্ট্রি জোন (টাকা)", "স্টপ লস (টাকা)", "টেক প্রফিট ১ (টাকা)", 
                          "টেক প্রফিট ২ (টাকা)", "রিস্ক-রিওয়ার্ড অনুপাত (RRR)", 
                          "স্কোর (১০০ এর মধ্যে)", "কনফিডেন্স লেভেল", "অ্যাকশন রিকমেন্ডেশন"]
                data_to_save = [headers] + self.current_data
            else:
                data_to_save = self.current_data
            
            success, msg = hf_manager.save_csv_file(self.current_date, data_to_save)
            if success:
                result = f"✅ {added} টি ডাটা যোগ হয়েছে। মোট: {len(self.current_data)} টি"
                if duplicate_skipped > 0:
                    result += f"\n⚠️ {duplicate_skipped} টি ডুপ্লিকেট সিম্বল স্কিপ করা হয়েছে।"
                return f"{result}\n{msg}"
            else:
                return f"⚠️ {added} টি ডাটা যোগ হয়েছে কিন্তু সেভ করতে পারেনি: {msg}"
        
        if duplicate_skipped > 0:
            return f"❌ {duplicate_skipped} টি ডুপ্লিকেট সিম্বল। কোনো নতুন ডাটা যোগ হয়নি।"
        return "❌ কোনো নতুন ডাটা যোগ হয়নি।"
    
    def clear_current_data(self):
        """আজকের ডাটা ক্লিয়ার করুন"""
        count = len(self.current_data)
        self.current_data = []
        success, msg = hf_manager.save_csv_file(self.current_date, [])
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

# ==================== HELPER FUNCTIONS ====================

def fix_date_format(date_str):
    """তারিখ ফরম্যাট ঠিক করা: 25-3-2026 -> 25-03-2026"""
    date_str = date_str.strip()
    pattern = r'^(\d{1,2})-(\d{1,2})-(\d{4})$'
    match = re.match(pattern, date_str)
    if match:
        day = match.group(1).zfill(2)
        month = match.group(2).zfill(2)
        year = match.group(3)
        return f"{day}-{month}-{year}"
    return date_str

# ==================== TELEGRAM HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট - Hugging Face স্টোরেজ**\n\n"
        "📝 **ডাটা যোগ করুন:**\n"
        "CSV ফরম্যাটে ডাটা পাঠান:\n"
        "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`\n\n"
        "📚 **কমান্ড:**\n"
        "`/help` - সব কমান্ড দেখুন\n"
        "`/list` - আজকের ডাটা দেখুন\n"
        "`/files` - সব CSV ফাইলের তালিকা\n"
        "`/view [তারিখ]` - ফাইল দেখুন\n"
        "`/symbols [তারিখ]` - ফাইলের সিম্বল দেখুন\n"
        "`/search [সিম্বল]` - সব ফাইলে সিম্বল খুঁজুন\n"
        "`/deletesymbol [তারিখ] [সিম্বল]` - সিম্বল ডিলিট\n"
        "`/deletefile [তারিখ]` - ফাইল ডিলিট\n"
        "`/clear` - আজকের ডাটা ক্লিয়ার\n"
        "`/status` - স্ট্যাটাস দেখুন",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **স্টক ডাটা বট - সম্পূর্ণ গাইড**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **ডাটা যোগ করার নিয়ম**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CSV ফরম্যাটে ডাটা পাঠান:


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **ফাইল ম্যানেজমেন্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/files` - সব CSV ফাইলের তালিকা দেখুন
• `/view 25-03-2026` - নির্দিষ্ট ফাইল দেখুন
• `/deletefile 25-03-2026` - ফাইল ডিলিট করুন

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **সিম্বল ম্যানেজমেন্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/symbols 25-03-2026` - ফাইলের সিম্বল দেখুন
• `/deletesymbol 25-03-2026 BDCOM` - সিম্বল ডিলিট
• `/search BDCOM` - সব ফাইলে সিম্বল খুঁজুন

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **আজকের ডাটা**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/list` - আজকের ডাটা দেখুন
• `/clear` - আজকের সব ডাটা মুছুন
• `/yesclear` - ক্লিয়ার কনফার্ম

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ **অন্যান্য**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/status` - বটের স্ট্যাটাস দেখুন
• `/cancel` - চলমান অপারেশন বাতিল করুন

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 **স্টোরেজ লোকেশন**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hugging Face: `ahashanahmed/csv/stock/`
ফাইল ফরম্যাট: `stock/DD-MM-YYYY.csv`

💡 **টিপস:**
• তারিখ ফরম্যাট: DD-MM-YYYY (যেমন: 25-03-2026)
• সিম্বল কেস সেনসিটিভ নয় (BDCOM = bdcom)
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
            "❌ CSV ফরম্যাটে ডাটা পাঠান। সাহায্যের জন্য `/help` দেখুন।\n\n"
            "উদাহরণ:\n"
            "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`",
            parse_mode='Markdown'
        )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preview = bot.get_preview()
    await update.message.reply_text(preview, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ আজকের সব ডাটা মুছে যাবে। `/yesclear` দিয়ে কনফার্ম করুন।", parse_mode='Markdown')
    context.user_data['confirm'] = True

async def yesclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('confirm'):
        result = bot.clear_current_data()
        await update.message.reply_text(result)
        context.user_data['confirm'] = False
    else:
        await update.message.reply_text("❌ আগে `/clear` দিন।", parse_mode='Markdown')

async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dates = hf_manager.get_all_csv_files()
    
    if not dates:
        await update.message.reply_text("📭 কোনো CSV ফাইল নেই।")
        return
    
    file_list = "\n".join([f"📄 `{date}.csv`" for date in dates])
    await update.message.reply_text(
        f"📁 **CSV ফাইলের তালিকা ({len(dates)} টি):**\n\n{file_list}\n\n"
        f"ফাইল দেখতে: `/view [তারিখ]`\n"
        f"ফাইল ডিলিট: `/deletefile [তারিখ]`",
        parse_mode='Markdown'
    )

async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ তারিখ দিন। উদাহরণ: `/view 25-03-2026`")
        return
    
    date = fix_date_format(context.args[0])
    status_msg = await update.message.reply_text(f"⏳ `{date}.csv` ফাইল খুঁজছি...", parse_mode='Markdown')
    
    data = hf_manager.read_csv_file(date)
    
    if data is None:
        dates = hf_manager.get_all_csv_files()
        if dates:
            file_list = "\n".join([f"• `{d}.csv`" for d in dates])
            await status_msg.edit_text(
                f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।\n\n"
                f"📁 **আপনার ফাইলগুলি:**\n{file_list}",
                parse_mode='Markdown'
            )
        else:
            await status_msg.edit_text(f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।", parse_mode='Markdown')
        return
    
    if not data:
        await status_msg.edit_text(f"📭 `{date}.csv` ফাইলটি খালি।", parse_mode='Markdown')
        return
    
    # Check if first row is header
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and ('symbol' in data[0][0].lower() or 'সিম্বল' in data[0][0]):
        start_idx = 1
    
    actual_data = data[start_idx:]
    
    preview = f"📊 **{date}.csv - মোট {len(actual_data)} টি রেকর্ড:**\n\n"
    for i, row in enumerate(actual_data[:10]):
        short = ', '.join(row[:3])
        if len(row) > 3:
            short += "..."
        preview += f"{i+1}. {short}\n"
    
    if len(actual_data) > 10:
        preview += f"\n... এবং {len(actual_data) - 10} টি বেশি"
    
    preview += f"\n\n💡 সিম্বল দেখতে: `/symbols {date}`"
    
    await status_msg.edit_text(preview, parse_mode='Markdown')

async def deletefile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ তারিখ দিন। উদাহরণ: `/deletefile 25-03-2026`")
        return
    
    date = fix_date_format(context.args[0])
    context.user_data['delete_file'] = date
    await update.message.reply_text(
        f"⚠️ আপনি কি নিশ্চিত? `{date}.csv` ফাইলটি স্থায়ীভাবে মুছে যাবে!\n\n"
        f"✅ হ্যাঁ হলে: `/confirmdelete`\n"
        f"❌ না হলে: `/cancel`",
        parse_mode='Markdown'
    )

async def confirmdelete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = context.user_data.get('delete_file')
    if not date:
        await update.message.reply_text("❌ আগে `/deletefile` দিন।")
        return
    
    success, msg = hf_manager.delete_csv_file(date)
    await update.message.reply_text(msg)
    context.user_data['delete_file'] = None

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = fix_date_format(context.args[0]) if context.args else bot.current_date
    status_msg = await update.message.reply_text(f"⏳ `{date}.csv` ফাইল থেকে সিম্বল খুঁজছি...", parse_mode='Markdown')
    
    data = hf_manager.read_csv_file(date)
    
    if data is None:
        dates = hf_manager.get_all_csv_files()
        if dates:
            file_list = "\n".join([f"• `{d}.csv`" for d in dates])
            await status_msg.edit_text(
                f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।\n\n"
                f"📁 **আপনার ফাইলগুলি:**\n{file_list}",
                parse_mode='Markdown'
            )
        else:
            await status_msg.edit_text(f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।", parse_mode='Markdown')
        return
    
    if not data:
        await status_msg.edit_text(f"📭 `{date}.csv` ফাইলটি খালি।", parse_mode='Markdown')
        return
    
    # Check if first row is header
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and ('symbol' in data[0][0].lower() or 'সিম্বল' in data[0][0]):
        start_idx = 1
    
    symbols = [row[0] for row in data[start_idx:] if row and len(row) > 0]
    symbol_list = "\n".join([f"• `{s}`" for s in symbols])
    
    await status_msg.edit_text(
        f"📋 **{date}.csv - সিম্বল লিস্ট ({len(symbols)} টি):**\n\n{symbol_list}\n\n"
        f"💡 সিম্বল ডিলিট: `/deletesymbol {date} [সিম্বল]`",
        parse_mode='Markdown'
    )

async def deletesymbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ তারিখ এবং সিম্বল দিন। উদাহরণ: `/deletesymbol 25-03-2026 BDCOM`",
            parse_mode='Markdown'
        )
        return
    
    date = fix_date_format(context.args[0])
    symbol = context.args[1].upper()
    
    await update.message.reply_text(f"⏳ '{symbol}' ডিলিট করা হচ্ছে...")
    success, msg = hf_manager.delete_symbol_from_file(date, symbol)
    await update.message.reply_text(msg)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব ফাইলে সিম্বল খুঁজুন - উন্নত ভার্সন"""
    if not context.args:
        await update.message.reply_text("❌ সিম্বল দিন। উদাহরণ: `/search BDCOM`")
        return
    
    search_symbol = context.args[0].upper()
    status_msg = await update.message.reply_text(f"🔍 '{search_symbol}' খুঁজছি... দয়া করে অপেক্ষা করুন।")
    
    try:
        dates = hf_manager.get_all_csv_files()
        
        if not dates:
            await status_msg.edit_text("📭 কোনো CSV ফাইল নেই। প্রথমে কিছু ডাটা যোগ করুন।")
            return
        
        results = hf_manager.search_symbol_all_files(search_symbol)
        
        if not results:
            await status_msg.edit_text(f"❌ '{search_symbol}' কোনো ফাইলে পাওয়া যায়নি।")
            return
        
        result_text = f"🔍 **'{search_symbol}' পাওয়া গেছে {len(results)} টি ফাইলে:**\n\n"
        for r in results:
            result_text += f"📄 **{r['date']}.csv** (লাইন {r['line']}):\n"
            full_row = ' | '.join(r['row'][:8])
            if len(r['row']) > 8:
                full_row += "..."
            result_text += f"   {full_row}\n\n"
        
        await status_msg.edit_text(result_text, parse_mode='Markdown')
        
    except Exception as e:
        await status_msg.edit_text(f"❌ ত্রুটি: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dates = hf_manager.get_all_csv_files()
    
    status_text = f"""
📊 **বট স্ট্যাটাস**

📁 Hugging Face: `{HF_REPO}/{HF_FOLDER}/`
🔑 HF_TOKEN: {'✅ সেট আছে' if HF_TOKEN else '❌ সেট নেই'}

📅 আজকের তারিখ: `{bot.current_date}`
📝 আজকের রেকর্ড: `{len(bot.current_data)}` টি

📂 মোট CSV ফাইল: `{len(dates)}` টি
"""
    
    if dates:
        status_text += f"\n📄 সর্বশেষ ৫টি ফাইল:\n"
        for date in dates[:5]:
            status_text += f"   • `{date}.csv`\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ অপারেশন বাতিল করা হয়েছে।")

# ==================== FLASK ROUTES ====================

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

# ==================== MAIN ====================

async def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    try:
        application = Application.builder().token(token).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
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