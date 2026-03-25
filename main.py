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