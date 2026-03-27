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

# 11 columns: full data
COLUMNS = [
    "symbol",
    "এলিয়ট ওয়েব (বর্তমান অবস্থান)",
    "সাব-ওয়েব (বর্তমান অবস্থান)",
    "এন্ট্রি জোন (টাকা)",
    "স্টপ লস (টাকা)",
    "টেক প্রফিট ১ (টাকা)",
    "টেক প্রফিট ২ (টাকা)",
    "রিস্ক-রিওয়ার্ড অনুপাত (RRR)",
    "স্কোর (১০০ এর মধ্যে)",
    "কনফিডেন্স লেভেল",
    "অ্যাকশন রিকমেন্ডেশন"
]

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
        print(f"   Columns: {len(COLUMNS)} columns")

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
        if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
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
        """সব ফাইলে সিম্বল খুঁজুন"""
        dates = self.get_all_csv_files()
        results = []

        for date in dates:
            data = self.read_csv_file(date)
            if data and len(data) > 0:
                # Check if first row is header
                start_idx = 0
                if data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                    start_idx = 1

                for idx, row in enumerate(data[start_idx:]):
                    if row and len(row) > 0 and row[0].upper() == symbol.upper():
                        results.append({
                            'date': date,
                            'row': row,
                            'line': start_idx + idx + 1
                        })
                        break

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
            if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                start_idx = 1
            self.current_data = data[start_idx:]
            print(f"Loaded {len(self.current_data)} records for {self.current_date}")
        else:
            self.current_data = []
            print(f"No data for {self.current_date}")

    def parse_csv_line(self, line):
        """CSV লাইন পার্স করে 11টি কলামে রূপান্তর"""
        items = [item.strip() for item in line.split(',')]
        
        # If less than 11 columns, pad with empty strings
        if len(items) < len(COLUMNS):
            items.extend([''] * (len(COLUMNS) - len(items)))
        # If more than 11 columns, take first 11
        elif len(items) > len(COLUMNS):
            items = items[:len(COLUMNS)]
        
        return items

    def add_csv_data(self, csv_text):
        """আজকের ডাটায় যোগ করুন"""
        lines = csv_text.strip().split('\n')
        added = 0
        duplicate_skipped = 0

        for line in lines:
            if not line.strip():
                continue
            
            row = self.parse_csv_line(line)
            
            if len(row) >= 1 and row[0]:  # At least symbol should be present
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
            # Save with headers
            data_to_save = [COLUMNS] + self.current_data
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
        success, msg = hf_manager.save_csv_file(self.current_date, [COLUMNS])
        if success:
            return f"✅ {count} টি ডাটা মুছে ফেলা হয়েছে।"
        return f"⚠️ ডাটা ক্লিয়ার হয়েছে কিন্তু সেভ করতে পারেনি: {msg}"

    def get_preview(self):
        """আজকের ডাটার প্রিভিউ"""
        if not self.current_data:
            return f"📭 {self.current_date} তারিখের কোনো ডাটা নেই।"

        preview = f"📊 **{self.current_date} - মোট {len(self.current_data)} টি রেকর্ড:**\n\n```\n"
        preview += f"{'#':<4} {'সিম্বল':<12} {'এলিয়ট ওয়েব':<20} {'এন্ট্রি':<12}\n"
        preview += "-" * 55 + "\n"

        for i, row in enumerate(self.current_data):
            symbol = row[0][:12] if len(row[0]) > 12 else row[0]
            wave = row[1][:20] if len(row[1]) > 20 else row[1]
            entry = row[3][:12] if len(row[3]) > 12 else row[3]
            preview += f"{i+1:<4} {symbol:<12} {wave:<20} {entry:<12}\n"

        preview += "```"
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

def format_as_table(data, title):
    """ডাটাকে সুন্দর টেবিল আকারে ফরম্যাট করা - 11 কলাম"""
    if not data:
        return f"📭 {title} - কোনো ডাটা নেই।"

    # Column headers in Bengali
    headers = ["#", "সিম্বল", "এলিয়ট ওয়েব", "সাব-ওয়েব", "এন্ট্রি", "স্টপ", "TP1", "TP2", "RRR", "স্কোর", "কনফিডেন্স", "অ্যাকশন"]

    # Calculate column widths based on content
    col_widths = [4]  # সিরিয়াল নম্বরের জন্য

    # Calculate width for each column
    for col_idx in range(1, len(headers)):
        max_width = len(headers[col_idx])
        for row in data:
            if col_idx <= len(row):
                cell_text = str(row[col_idx-1])[:30]
                max_width = max(max_width, len(cell_text))
        col_widths.append(min(max_width + 2, 20))

    # Adjust some columns manually
    col_widths[1] = min(col_widths[1], 12)   # সিম্বল
    col_widths[2] = min(col_widths[2], 18)   # এলিয়ট ওয়েব
    col_widths[3] = min(col_widths[3], 12)   # সাব-ওয়েব
    col_widths[4] = min(col_widths[4], 12)   # এন্ট্রি
    col_widths[5] = min(col_widths[5], 8)    # স্টপ
    col_widths[6] = min(col_widths[6], 8)    # TP1
    col_widths[7] = min(col_widths[7], 8)    # TP2
    col_widths[8] = min(col_widths[8], 6)    # RRR
    col_widths[9] = min(col_widths[9], 6)    # স্কোর
    col_widths[10] = min(col_widths[10], 12) # কনফিডেন্স
    col_widths[11] = min(col_widths[11], 15) # অ্যাকশন

    # Create table
    table = f"📊 **{title} - মোট {len(data)} টি রেকর্ড:**\n\n```\n"

    # Header line
    header_line = ""
    for i, header in enumerate(headers):
        header_line += f"{header:<{col_widths[i]}}"
    table += header_line + "\n"

    # Separator line
    separator = ""
    for width in col_widths:
        separator += "-" * width
    table += separator + "\n"

    # Data rows
    for i, row in enumerate(data):
        line = f"{i+1:<{col_widths[0]}}"
        
        for col_idx in range(1, len(headers)):
            if col_idx-1 < len(row):
                cell = str(row[col_idx-1])[:col_widths[col_idx]]
                line += f"{cell:<{col_widths[col_idx]}}"
            else:
                line += f"{'':<{col_widths[col_idx]}}"

        table += line + "\n"

        # Add separator every 10 rows
        if (i + 1) % 10 == 0 and i + 1 < len(data):
            table += separator + "\n"

    table += "```"
    return table

def format_files_table(dates):
    """ফাইলের তালিকা সুন্দর টেবিল আকারে দেখান"""
    if not dates:
        return "📭 কোনো CSV ফাইল নেই।"

    serial_width = 6
    name_width = 20

    table = f"📁 **CSV ফাইলের তালিকা ({len(dates)} টি):**\n\n```\n"
    table += f"{'ক্রম':<{serial_width}} {'ফাইলের নাম':<{name_width}} {'তারিখ':<12}\n"
    table += "-" * (serial_width + name_width + 15) + "\n"

    for i, date in enumerate(dates):
        table += f"{i+1:<{serial_width}} {date}.csv{' ':<{name_width-len(date)-4}} {date:<12}\n"

    table += "```"
    return table

def get_search_results_table(results, search_symbol):
    """সার্চ রেজাল্ট সুন্দর টেবিল আকারে দেখান"""
    if not results:
        return f"❌ '{search_symbol}' কোনো ফাইলে পাওয়া যায়নি।"

    headers = ["#", "তারিখ", "সিম্বল", "এলিয়ট ওয়েব", "এন্ট্রি", "অ্যাকশন"]
    col_widths = [4, 12, 12, 20, 12, 15]

    table = f"🔍 **'{search_symbol}' পাওয়া গেছে {len(results)} টি ফাইলে:**\n\n```\n"

    header_line = ""
    for i, header in enumerate(headers):
        header_line += f"{header:<{col_widths[i]}}"
    table += header_line + "\n"
    table += "-" * sum(col_widths) + "\n"

    for i, r in enumerate(results):
        line = f"{i+1:<{col_widths[0]}}"
        line += f"{r['date'][:col_widths[1]]:<{col_widths[1]}}"
        line += f"{r['row'][0][:col_widths[2]]:<{col_widths[2]}}"
        line += f"{r['row'][1][:col_widths[3]]:<{col_widths[3]}}"
        line += f"{r['row'][3][:col_widths[4]]:<{col_widths[4]}}" if len(r['row']) > 3 else f"{'':<{col_widths[4]}}"
        line += f"{r['row'][10][:col_widths[5]]:<{col_widths[5]}}" if len(r['row']) > 10 else f"{'':<{col_widths[5]}}"
        table += line + "\n"

    table += "```"
    return table

# ==================== TELEGRAM HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট - Hugging Face স্টোরেজ**\n\n"
        "📝 **ডাটা যোগ করুন:**\n"
        "CSV ফরম্যাটে ডাটা পাঠান (11টি কলাম):\n"
        "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`\n\n"
        "**কলামের ক্রম:**\n"
        "1. symbol | 2. এলিয়ট ওয়েব | 3. সাব-ওয়েব | 4. এন্ট্রি | 5. স্টপ\n"
        "6. TP1 | 7. TP2 | 8. RRR | 9. স্কোর | 10. কনফিডেন্স | 11. অ্যাকশন\n\n"
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
CSV ফরম্যাটে 11টি কলাম পাঠান:
`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`

**কলামের ক্রম:**
1. symbol
2. এলিয়ট ওয়েব (বর্তমান অবস্থান)
3. সাব-ওয়েব (বর্তমান অবস্থান)
4. এন্ট্রি জোন (টাকা)
5. স্টপ লস (টাকা)
6. টেক প্রফিট ১ (টাকা)
7. টেক প্রফিট ২ (টাকা)
8. রিস্ক-রিওয়ার্ড অনুপাত (RRR)
9. স্কোর (১০০ এর মধ্যে)
10. কনফিডেন্স লেভেল
11. অ্যাকশন রিকমেন্ডেশন

💡 **টিপ:** কম ডাটা পাঠালে বাকি ফিল্ড খালি থাকবে।

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **ফাইল ম্যানেজমেন্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/files` - সব CSV ফাইলের তালিকা
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
            "উদাহরণ (11 কলাম):\n"
            "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`",
            parse_mode='Markdown'
        )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আজকের ডাটা সুন্দর টেবিল আকারে দেখান"""
    if not bot.current_data:
        await update.message.reply_text(f"📭 {bot.current_date} তারিখের কোনো ডাটা নেই।")
        return

    table = format_as_table(bot.current_data, f"{bot.current_date} - আজকের ডাটা")

    if len(table) > 4000:
        parts = [table[i:i+4000] for i in range(0, len(table), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(table, parse_mode='Markdown')

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
    """সব CSV ফাইলের তালিকা টেবিল আকারে দেখান"""
    dates = hf_manager.get_all_csv_files()

    if not dates:
        await update.message.reply_text("📭 কোনো CSV ফাইল নেই।")
        return

    table = format_files_table(dates)
    await update.message.reply_text(table, parse_mode='Markdown')

async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ফাইল সুন্দর টেবিল আকারে দেখান"""
    if not context.args:
        await update.message.reply_text("❌ তারিখ দিন। উদাহরণ: `/view 25-03-2026`")
        return

    date = fix_date_format(context.args[0])
    status_msg = await update.message.reply_text(f"⏳ `{date}.csv` ফাইল খুঁজছি...", parse_mode='Markdown')

    data = hf_manager.read_csv_file(date)

    if data is None:
        dates = hf_manager.get_all_csv_files()
        if dates:
            file_list = "\n".join([f"• `{d}.csv`" for d in dates[:10]])
            if len(dates) > 10:
                file_list += f"\n• ... এবং {len(dates)-10} টি বেশি"
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
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1

    actual_data = data[start_idx:]

    table = format_as_table(actual_data, f"{date}.csv")

    if len(table) > 4000:
        parts = [table[i:i+4000] for i in range(0, len(table), 4000)]
        await status_msg.delete()
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await status_msg.edit_text(table, parse_mode='Markdown')

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
    """ফাইলের সিম্বল লিস্ট দেখান"""
    date = fix_date_format(context.args[0]) if context.args else bot.current_date
    status_msg = await update.message.reply_text(f"⏳ `{date}.csv` ফাইল থেকে সিম্বল খুঁজছি...", parse_mode='Markdown')

    data = hf_manager.read_csv_file(date)

    if data is None:
        dates = hf_manager.get_all_csv_files()
        if dates:
            file_list = "\n".join([f"• `{d}.csv`" for d in dates[:10]])
            if len(dates) > 10:
                file_list += f"\n• ... এবং {len(dates)-10} টি বেশি"
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

    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1

    symbols = [row[0] for row in data[start_idx:] if row and len(row) > 0]

    if not symbols:
        await status_msg.edit_text(f"📭 `{date}.csv` ফাইলে কোনো সিম্বল নেই।", parse_mode='Markdown')
        return

    symbol_list = "\n".join([f"{i+1}. `{s}`" for i, s in enumerate(symbols)])

    if len(symbol_list) > 4000:
        symbol_list = symbol_list[:4000] + "\n\n... এবং বাকি সিম্বল দেখানোর জন্য ফাইলটি ডাউনলোড করুন।"

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
    """সব ফাইলে সিম্বল খুঁজুন"""
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
        table = get_search_results_table(results, search_symbol)

        if len(table) > 4000:
            parts = [table[i:i+4000] for i in range(0, len(table), 4000)]
            await status_msg.delete()
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await status_msg.edit_text(table, parse_mode='Markdown')

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
📋 মোট কলাম: `{len(COLUMNS)}` টি

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
        "columns": len(COLUMNS),
        "columns_list": COLUMNS,
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