import os
import csv
import json
import threading
import asyncio
import io
import tempfile
import re
import logging
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from huggingface_hub import HfApi, upload_file, list_repo_files, delete_file, hf_hub_download

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
        logger.info(f"🔧 HF Manager initialized")
        logger.info(f"   Repo: {self.repo_id}")
        logger.info(f"   Token: {'✅ Yes' if self.token else '❌ No'}")

    def get_all_csv_files(self):
        """সব CSV ফাইলের তালিকা"""
        if not self.token:
            logger.error("❌ No HF_TOKEN!")
            return []

        try:
            logger.info(f"🔍 Fetching files from {self.repo_id}...")
            files = list_repo_files(self.repo_id, token=self.token, repo_type=self.repo_type)
            logger.info(f"📁 Total files in repo: {len(files)}")

            csv_files = [f for f in files if f.startswith(f"{self.folder}/") and f.endswith('.csv')]
            logger.info(f"📄 CSV files in {self.folder}: {len(csv_files)}")

            dates = [f.replace(f"{self.folder}/", "").replace(".csv", "") for f in csv_files]
            return sorted(dates, reverse=True)

        except Exception as e:
            logger.error(f"❌ Error getting files: {e}")
            return []

    def read_csv_file(self, date):
        """নির্দিষ্ট তারিখের CSV ফাইল পড়ুন"""
        if not self.token:
            logger.error("❌ No HF_TOKEN!")
            return None

        # Clean date - remove .csv if present
        date = date.replace('.csv', '').strip()
        filename = f"{self.folder}/{date}.csv"
        logger.info(f"🔍 Looking for: {filename}")

        try:
            files = list_repo_files(self.repo_id, token=self.token, repo_type=self.repo_type)
            if filename not in files:
                logger.error(f"❌ File not found: {filename}")
                logger.info(f"Available files: {[f for f in files if f.startswith(self.folder)]}")
                return None

            logger.info(f"✅ File found, downloading...")

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
            logger.info(f"✅ Loaded {len(data)} records from {filename}")
            return data

        except Exception as e:
            logger.error(f"❌ Error reading file: {e}")
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

        start_idx = 0
        if data and data[0] and len(data[0]) > 0:
            first_cell = data[0][0].lower() if data[0][0] else ''
            if 'symbol' in first_cell or 'সিম্বল' in first_cell:
                start_idx = 1

        new_data = data[:start_idx]
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
            return True, f"✅ {symbol} ডিলিট করা হয়েছে। (ডিলিট: {deleted_count} টি)"
        return False, msg

    def search_symbol_all_files(self, symbol):
        """সব ফাইলে সিম্বল খুঁজুন"""
        dates = self.get_all_csv_files()
        results = []

        for date in dates:
            data = self.read_csv_file(date)
            if data and len(data) > 0:
                start_idx = 0
                if data[0] and len(data[0]) > 0:
                    first_cell = data[0][0].lower() if data[0][0] else ''
                    if 'symbol' in first_cell or 'সিম্বল' in first_cell:
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
            start_idx = 0
            if data and data[0] and len(data[0]) > 0:
                first_cell = data[0][0].lower() if data[0][0] else ''
                if 'symbol' in first_cell or 'সিম্বল' in first_cell:
                    start_idx = 1
            self.current_data = data[start_idx:]
            logger.info(f"Loaded {len(self.current_data)} records for {self.current_date}")
        else:
            self.current_data = []
            logger.info(f"No data for {self.current_date}")

    def add_csv_data(self, csv_text):
        """আজকের ডাটায় যোগ করুন"""
        lines = csv_text.strip().split('\n')
        added = 0
        duplicate_skipped = 0

        for line in lines:
            if not line.strip():
                continue
            row = [item.strip() for item in line.split(',')]
            if len(row) >= 2:
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
            headers = ["symbol", "এলিয়ট ওয়েব (বর্তমান অবস্থান)", "সাব-ওয়েব (বর্তমান অবস্থান)", 
                      "এন্ট্রি জোন (টাকা)", "স্টপ লস (টাকা)", "টেক প্রফিট ১ (টাকা)", 
                      "টেক প্রফিট ২ (টাকা)", "রিস্ক-রিওয়ার্ড অনুপাত (RRR)", 
                      "স্কোর (১০০ এর মধ্যে)", "কনফিডেন্স লেভেল", "অ্যাকশন রিকমেন্ডেশন"]
            data_to_save = [headers] + self.current_data

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

bot = StockDataBot()

# ==================== HELPER FUNCTIONS ====================

def fix_date_format(date_str):
    """তারিখ ফরম্যাট ঠিক করা: 25-3-2026 -> 25-03-2026"""
    # Remove .csv if present
    date_str = date_str.replace('.csv', '').strip()
    pattern = r'^(\d{1,2})-(\d{1,2})-(\d{4})$'
    match = re.match(pattern, date_str)
    if match:
        day = match.group(1).zfill(2)
        month = match.group(2).zfill(2)
        year = match.group(3)
        return f"{day}-{month}-{year}"
    return date_str

def format_as_table(data, title, page=0, items_per_page=15):
    """সব কলাম সহ সুন্দর টেবিল আকারে ফরম্যাট করা"""
    if not data:
        return f"📭 {title} - কোনো ডাটা নেই।"

    total_items = len(data)
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_data = data[start_idx:end_idx]
    total_pages = (total_items + items_per_page - 1) // items_per_page

    headers = [
        "#", "সিম্বল", "এলিয়ট ওয়েব", "সাব-ওয়েব",
        "এন্ট্রি", "স্টপ লস", "TP1", "TP2", "RRR", "স্কোর", "কনফিডেন্স", "অ্যাকশন"
    ]

    # Simplified column widths for better display
    col_widths = [4, 12, 20, 15, 12, 10, 12, 12, 6, 6, 12, 12]

    page_info = f" (পৃষ্ঠা {page+1}/{total_pages})" if total_pages > 1 else ""
    table = f"📊 **{title}{page_info} - মোট {total_items} টি:**\n\n```\n"
    
    # Header
    for i, header in enumerate(headers):
        table += f"{header:<{col_widths[i]}}"
        if i < len(headers) - 1:
            table += " │ "
    table += "\n"
    
    # Separator
    for i, width in enumerate(col_widths):
        table += "─" * width
        if i < len(col_widths) - 1:
            table += "─┼─"
    table += "\n"

    # Data rows
    for idx, row in enumerate(page_data):
        global_idx = start_idx + idx + 1
        row_data = [
            str(global_idx),
            row[0][:10] if len(row[0]) > 10 else row[0],
            row[1][:18] if len(row[1]) > 18 else row[1],
            row[2][:13] if len(row[2]) > 13 else row[2],
            row[3][:10] if len(row[3]) > 10 else row[3],
            row[4][:8] if len(row[4]) > 8 else row[4],
            row[5][:10] if len(row[5]) > 10 else row[5],
            row[6][:10] if len(row[6]) > 10 else row[6],
            row[7][:4] if len(row[7]) > 4 else row[7],
            row[8][:4] if len(row[8]) > 4 else row[8],
            row[9][:10] if len(row[9]) > 10 else row[9],
            row[10][:10] if len(row[10]) > 10 else row[10]
        ]
        
        for i, val in enumerate(row_data):
            table += f"{val:<{col_widths[i]}}"
            if i < len(col_widths) - 1:
                table += " │ "
        table += "\n"

    table += "```"
    
    if total_pages > 1:
        table += f"\n\n📄 পৃষ্ঠা {page+1}/{total_pages}"
    
    return table

# ==================== TELEGRAM HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 আজকের ডাটা", callback_data="list")],
        [InlineKeyboardButton("📁 ফাইলের তালিকা", callback_data="files")],
        [InlineKeyboardButton("🔍 সিম্বল সার্চ", callback_data="search_prompt")],
        [InlineKeyboardButton("❓ সাহায্য", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট**\n\n"
        "স্টক ডাটা ম্যানেজ করতে নিচের বাটন ব্যবহার করুন:\n\n"
        "📝 **ডাটা যোগ করুন:**\n"
        "CSV ফরম্যাটে ডাটা পাঠান:\n"
        "`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **স্টক ডাটা বট - সাহায্য**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **ডাটা যোগ করুন:**
CSV ফরম্যাটে ডাটা পাঠান:
`BDCOM,Impulse (Wave 4),Sub-wave C,25.80-26.30,24.90,27.50,29.00,1:1.8,72,High,Accumulate`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **কমান্ড:**
• `/list` - আজকের ডাটা দেখুন
• `/files` - সব CSV ফাইলের তালিকা
• `/view 25-03-2026` - নির্দিষ্ট ফাইল দেখুন
• `/search BDCOM` - সিম্বল খুঁজুন
• `/deletesymbol 25-03-2026 BDCOM` - সিম্বল ডিলিট
• `/deletefile 25-03-2026` - ফাইল ডিলিট
• `/clear` - আজকের ডাটা ক্লিয়ার
• `/status` - স্ট্যাটাস দেখুন

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **টিপস:**
• ফাইলের তালিকা থেকে ক্লিক করেই ফাইল দেখুন
• তারিখ ফরম্যাট: DD-MM-YYYY (যেমন: 25-03-2026)
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব CSV ফাইলের তালিকা - ক্লিকযোগ্য বাটন সহ"""
    dates = hf_manager.get_all_csv_files()

    if not dates:
        await update.message.reply_text("📭 কোনো CSV ফাইল নেই।")
        return

    # Create inline keyboard with file buttons
    keyboard = []
    for date in dates:
        keyboard.append([InlineKeyboardButton(f"📄 {date}.csv", callback_data=f"view_{date}")])
    
    keyboard.append([InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📁 **CSV ফাইলের তালিকা ({len(dates)} টি):**\n\nনিচের বাটনে ক্লিক করুন:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট ফাইল দেখান"""
    if not context.args:
        await update.message.reply_text("❌ তারিখ দিন। উদাহরণ: `/view 25-03-2026`")
        return

    date = fix_date_format(context.args[0])
    await show_file(update, context, date)

async def show_file(update, context, date, message_to_edit=None):
    """ফাইল দেখানোর ফাংশন"""
    data = hf_manager.read_csv_file(date)
    
    if message_to_edit:
        status_msg = message_to_edit
    else:
        status_msg = await update.message.reply_text(f"⏳ `{date}.csv` খুঁজছি...", parse_mode='Markdown')

    if data is None:
        dates = hf_manager.get_all_csv_files()
        if dates:
            keyboard = []
            for d in dates:
                keyboard.append([InlineKeyboardButton(f"📄 {d}.csv", callback_data=f"view_{d}")])
            keyboard.append([InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await status_msg.edit_text(
                f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।\n\n"
                f"📁 **আপনার ফাইলগুলি:**\nনিচের বাটনে ক্লিক করুন:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await status_msg.edit_text(f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।", parse_mode='Markdown')
        return

    if not data:
        await status_msg.edit_text(f"📭 `{date}.csv` ফাইলটি খালি।", parse_mode='Markdown')
        return

    # Skip header if exists
    start_idx = 0
    if data and data[0] and len(data[0]) > 0:
        first_cell = data[0][0].lower() if data[0][0] else ''
        if 'symbol' in first_cell or 'সিম্বল' in first_cell:
            start_idx = 1

    actual_data = data[start_idx:]
    
    # Store for pagination
    context.user_data['current_view_data'] = actual_data
    context.user_data['current_view_date'] = date
    
    table = format_as_table(actual_data, f"{date}.csv")
    
    keyboard = [
        [InlineKeyboardButton("🔙 ফাইলের তালিকা", callback_data="files")],
        [InlineKeyboardButton("🏠 মেনুতে ফিরুন", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await status_msg.edit_text(table, parse_mode='Markdown', reply_markup=reply_markup)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আজকের ডাটা দেখান"""
    if not bot.current_data:
        await update.message.reply_text(f"📭 {bot.current_date} তারিখের কোনো ডাটা নেই।")
        return

    table = format_as_table(bot.current_data, f"{bot.current_date} - আজকের ডাটা")
    
    keyboard = [[InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(table, parse_mode='Markdown', reply_markup=reply_markup)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব ফাইলে সিম্বল খুঁজুন"""
    if not context.args:
        await update.message.reply_text("❌ সিম্বল দিন। উদাহরণ: `/search BDCOM`")
        return

    search_symbol = context.args[0].upper()
    status_msg = await update.message.reply_text(f"🔍 '{search_symbol}' খুঁজছি...")

    try:
        results = hf_manager.search_symbol_all_files(search_symbol)

        if not results:
            await status_msg.edit_text(f"❌ '{search_symbol}' কোনো ফাইলে পাওয়া যায়নি।")
            return
        
        result_text = f"🔍 **'{search_symbol}' পাওয়া গেছে {len(results)} টি ফাইলে:**\n\n```\n"
        result_text += f"{'#':<3} {'তারিখ':<12} {'সিম্বল':<12} {'এলিয়ট ওয়েব':<25} {'অ্যাকশন':<20}\n"
        result_text += "-" * 80 + "\n"

        for i, r in enumerate(results[:20]):
            date = r['date'][:12]
            symbol = r['row'][0][:12] if len(r['row'][0]) > 12 else r['row'][0]
            wave = r['row'][1][:25] if len(r['row'][1]) > 25 else r['row'][1]
            action = r['row'][10][:20] if len(r['row'][10]) > 20 else r['row'][10]
            result_text += f"{i+1:<3} {date:<12} {symbol:<12} {wave:<25} {action:<20}\n"

        result_text += "```"
        
        if len(results) > 20:
            result_text += f"\n\n... এবং {len(results) - 20} টি বেশি"

        keyboard = [[InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text(f"❌ ত্রুটি: {str(e)}")

async def deletesymbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ তারিখ এবং সিম্বল দিন। উদাহরণ: `/deletesymbol 25-03-2026 BDCOM`")
        return

    date = fix_date_format(context.args[0])
    symbol = context.args[1].upper()

    await update.message.reply_text(f"⏳ '{symbol}' ডিলিট করা হচ্ছে...")
    success, msg = hf_manager.delete_symbol_from_file(date, symbol)
    await update.message.reply_text(msg)

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

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ আজকের সব ডাটা মুছে যাবে। `/yesclear` দিয়ে কনফার্ম করুন。")
    context.user_data['confirm'] = True

async def yesclear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('confirm'):
        result = bot.clear_current_data()
        await update.message.reply_text(result)
        context.user_data['confirm'] = False
    else:
        await update.message.reply_text("❌ আগে `/clear` দিন।")

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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "list":
        if not bot.current_data:
            await query.edit_message_text(f"📭 {bot.current_date} তারিখের কোনো ডাটা নেই।")
            return
        
        table = format_as_table(bot.current_data, f"{bot.current_date} - আজকের ডাটা")
        
        keyboard = [[InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(table, parse_mode='Markdown', reply_markup=reply_markup)
    
    elif data == "files":
        dates = hf_manager.get_all_csv_files()
        
        if not dates:
            await query.edit_message_text("📭 কোনো CSV ফাইল নেই।")
            return
        
        keyboard = []
        for date in dates:
            keyboard.append([InlineKeyboardButton(f"📄 {date}.csv", callback_data=f"view_{date}")])
        keyboard.append([InlineKeyboardButton("🔙 মেনুতে ফিরুন", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📁 **CSV ফাইলের তালিকা ({len(dates)} টি):**\n\nনিচের বাটনে ক্লিক করুন:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data == "search_prompt":
        await query.edit_message_text(
            "🔍 **সিম্বল সার্চ**\n\n"
            "যে সিম্বল খুঁজতে চান তা টাইপ করুন:\n"
            "উদাহরণ: `BDCOM`\n\n"
            "অথবা কমান্ড ব্যবহার করুন: `/search BDCOM`",
            parse_mode='Markdown'
        )
    
    elif data == "help":
        await query.edit_message_text(
            "📚 **সাহায্য**\n\n"
            "• `/list` - আজকের ডাটা\n"
            "• `/files` - ফাইলের তালিকা\n"
            "• `/view 25-03-2026` - ফাইল দেখুন\n"
            "• `/search BDCOM` - সিম্বল খুঁজুন\n"
            "• `/deletesymbol 25-03-2026 BDCOM` - সিম্বল ডিলিট\n"
            "• `/deletefile 25-03-2026` - ফাইল ডিলিট\n"
            "• `/clear` - আজকের ডাটা ক্লিয়ার\n"
            "• `/status` - স্ট্যাটাস\n\n"
            "💡 ফাইলের তালিকা থেকে ক্লিক করেই ফাইল দেখুন!",
            parse_mode='Markdown'
        )
    
    elif data == "back_to_menu":
        keyboard = [
            [InlineKeyboardButton("📊 আজকের ডাটা", callback_data="list")],
            [InlineKeyboardButton("📁 ফাইলের তালিকা", callback_data="files")],
            [InlineKeyboardButton("🔍 সিম্বল সার্চ", callback_data="search_prompt")],
            [InlineKeyboardButton("❓ সাহায্য", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 **স্টক ডাটা বট**\n\nস্টক ডাটা ম্যানেজ করতে নিচের বাটন ব্যবহার করুন:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    elif data.startswith("view_"):
        date = data.replace("view_", "")
        await show_file(update, context, date, query.message)

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

# ==================== MAIN ====================

async def run_bot():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return

    try:
        application = Application.builder().token(token).build()

        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("files", files_command))
        application.add_handler(CommandHandler("view", view_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CommandHandler("deletesymbol", deletesymbol_command))
        application.add_handler(CommandHandler("deletefile", deletefile_command))
        application.add_handler(CommandHandler("confirmdelete", confirmdelete_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("yesclear", yesclear_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        
        # Message and callback handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_callback))

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