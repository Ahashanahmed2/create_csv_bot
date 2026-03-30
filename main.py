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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from huggingface_hub import HfApi, upload_file, list_repo_files, delete_file, hf_hub_download

# Portfolio মডিউল ইম্পোর্ট করুন
from portfolio import PortfolioAnalyzer
# Trade Analytics মডিউল ইম্পোর্ট করুন
from trade_analytics import add_trade_analytics_handlers
# Advanced Features মডিউল ইম্পোর্ট করুন
from advanced_features import (
    AdvancedFeatures, chart_command, compare_command, 
    notify_command, setalert_command, backtest_command, export_command
)

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
    "টেক প্রফিট ৩ (টাকা)",
    "রিস্ক-রিওয়ার্ড অনুপাত (RRR)",
    "স্কোর (১০০ এর মধ্যে)",
    "কুইক ইনসাইট"
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
            print(f"📁 Total files: {len(files)}")

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
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
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
        if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
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
        """আজকের ডাটা লোড করুন - শুধুমাত্র আজকের ফাইল"""
        print(f"📂 Loading data for {self.current_date}...")
        data = hf_manager.read_csv_file(self.current_date)
        if data:
            start_idx = 0
            if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                start_idx = 1
            self.current_data = data[start_idx:]
            print(f"✅ Loaded {len(self.current_data)} records for {self.current_date}")
        else:
            # আজকের ডাটা না থাকলে খালি লিস্ট রাখুন (কোনো ফাইল লোড করবেন না)
            self.current_data = []
            print(f"⚠️ No data for {self.current_date}, starting with empty list")

    def get_data_for_date(self, date):
        """নির্দিষ্ট তারিখের ডাটা লোড করুন - অন্য তারিখের ডাটা মিক্স করবেন না"""
        data = hf_manager.read_csv_file(date)
        if data:
            start_idx = 0
            if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                start_idx = 1
            return data[start_idx:]
        return []

    def parse_csv_line(self, line):
        """CSV লাইন পার্স করে 11টি কলামে রূপান্তর"""
        items = [item.strip() for item in line.split(',')]

        if len(items) < len(COLUMNS):
            items.extend([''] * (len(COLUMNS) - len(items)))
        elif len(items) > len(COLUMNS):
            items = items[:len(COLUMNS)]

        return items

    def add_csv_data(self, csv_text):
        """শুধু আজকের ডাটায় যোগ করুন - অন্য তারিখের সাথে মিক্স করবেন না"""
        lines = csv_text.strip().split('\n')
        added = 0
        duplicate_skipped = 0

        for line in lines:
            if not line.strip():
                continue

            row = self.parse_csv_line(line)

            if len(row) >= 1 and row[0]:
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
        """শুধু আজকের ডাটা ক্লিয়ার করুন"""
        count = len(self.current_data)
        self.current_data = []
        success, msg = hf_manager.save_csv_file(self.current_date, [COLUMNS])
        if success:
            return f"✅ {count} টি ডাটা মুছে ফেলা হয়েছে।"
        return f"⚠️ ডাটা ক্লিয়ার হয়েছে কিন্তু সেভ করতে পারেনি: {msg}"

bot = StockDataBot()

# পোর্টফোলিও অ্যানালাইজার তৈরি করুন
portfolio_analyzer = PortfolioAnalyzer(hf_manager, bot)

# Advanced Features অবজেক্ট
advanced_features = AdvancedFeatures(hf_manager, bot)

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

def get_score_emoji(score):
    """স্কোর অনুযায়ী ইমোজি রিটার্ন করুন"""
    try:
        score_num = int(score)
        if score_num >= 85:
            return "💎"
        elif score_num >= 80:
            return "🔥"
        elif score_num >= 70:
            return "⭐"
        elif score_num >= 60:
            return "✅"
        elif score_num >= 50:
            return "📈"
        elif score_num >= 40:
            return "⚠️"
        else:
            return "❌"
    except:
        return "⭐"

def get_score_text(score):
    """স্কোর অনুযায়ী টেক্সট রিটার্ন করুন"""
    try:
        score_num = int(score)
        if score_num >= 85:
            return "💎 এক্সট্রিম শক্তিশালী"
        elif score_num >= 80:
            return "🔥 খুব শক্তিশালী"
        elif score_num >= 70:
            return "⭐ শক্তিশালী"
        elif score_num >= 60:
            return "✅ ভাল"
        elif score_num >= 50:
            return "📈 মধ্যম"
        elif score_num >= 40:
            return "⚠️ দুর্বল"
        else:
            return "❌ খুব দুর্বল"
    except:
        return "⭐ সাধারণ"

# ==================== ADVANCED FEATURES WRAPPERS ====================

async def chart_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """চার্ট জেনারেট করুন - র‍্যাপার ফাংশন"""
    await chart_command(update, context, hf_manager, bot)

async def compare_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """কম্পেয়ার - র‍্যাপার ফাংশন"""
    await compare_command(update, context, hf_manager, bot)

async def notify_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নোটিফিকেশন - র‍্যাপার ফাংশন"""
    await notify_command(update, context)

async def setalert_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যালার্ট সেট - র‍্যাপার ফাংশন"""
    await setalert_command(update, context)

async def backtest_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্যাকটেস্ট - র‍্যাপার ফাংশন"""
    await backtest_command(update, context, hf_manager)

async def export_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """এক্সপোর্ট - র‍্যাপার ফাংশন"""
    await export_command(update, context, hf_manager)

# ==================== PORTFOLIO HANDLERS WITH INLINE BUTTONS ====================

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """পোর্টফোলিও রিপোর্ট ইনলাইন বাটন সহ দেখান"""
    args = context.args

    if args:
        date_input = args[0]
        date = fix_date_format(date_input)
    else:
        files = hf_manager.get_all_csv_files()
        if files:
            date = files[0]
        else:
            await update.message.reply_text("❌ কোনো CSV ফাইল নেই।")
            return

    status_msg = await update.message.reply_text(f"⏳ পোর্টফোলিও অ্যানালাইসিস করা হচ্ছে ({date})...")

    data = hf_manager.read_csv_file(date)

    if data is None:
        await status_msg.edit_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return

    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1

    all_data = data[start_idx:]

    if not all_data:
        await status_msg.edit_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return

    stats = portfolio_analyzer.analyze_portfolio(all_data)

    if not stats:
        await status_msg.edit_text("❌ অ্যানালাইসিস করতে ব্যর্থ হয়েছে।")
        return

    report, reply_markup = portfolio_analyzer.format_portfolio_report_with_buttons(stats, date)

    await status_msg.edit_text(report, parse_mode='Markdown', reply_markup=reply_markup)

async def category_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ক্যাটাগরি বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')

    category = parts[0]
    date = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1

    context.user_data['last_view'] = {'category': category, 'date': date, 'page': page}

    csv_data = hf_manager.read_csv_file(date)

    if csv_data is None:
        await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return

    start_idx = 0
    if csv_data and csv_data[0] and len(csv_data[0]) > 0 and csv_data[0][0] == "symbol":
        start_idx = 1

    all_data = csv_data[start_idx:]

    if not all_data:
        await query.edit_message_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return

    stats = portfolio_analyzer.analyze_portfolio(all_data)

    if not stats:
        await query.edit_message_text("❌ অ্যানালাইসিস করতে ব্যর্থ হয়েছে।")
        return

    if category == "vs":
        symbols_with_scores = list(zip(stats['very_strong']['symbols'], stats['very_strong']['scores']))
        title = "🔥 খুব শক্তিশালী সিম্বল (স্কোর 80+)"
    elif category == "vg":
        symbols_with_scores = list(zip(stats['good']['symbols'], stats['good']['scores']))
        title = "✅ ভাল সিম্বল (স্কোর 60-79)"
    elif category == "vm":
        symbols_with_scores = list(zip(stats['medium']['symbols'], stats['medium']['scores']))
        title = "⚠️ মধ্যম সিম্বল (স্কোর 40-59)"
    elif category == "vw":
        symbols_with_scores = list(zip(stats['weak']['symbols'], stats['weak']['scores']))
        title = "❌ দুর্বল সিম্বল (স্কোর <40)"
    elif category == "iw":
        symbols_with_scores = [(sym, "-") for sym in stats['impulse']['symbols']]
        title = "📈 ইম্পালস ওয়েভ সিম্বল"
    elif category == "cw":
        symbols_with_scores = [(sym, "-") for sym in stats['corrective']['symbols']]
        title = "🔄 করেকটিভ ওয়েভ সিম্বল"
    else:
        await query.edit_message_text("❌ ভুল ক্যাটাগরি।")
        return

    total_pages = (len(symbols_with_scores) + 9) // 10
    if page > total_pages and total_pages > 0:
        page = total_pages

    result, reply_markup = portfolio_analyzer.format_symbols_with_buttons(
        symbols_with_scores, title, date, category, page, total_pages
    )

    await query.edit_message_text(result, parse_mode='Markdown', reply_markup=reply_markup)

async def symbol_detail_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সিম্বল ডিটেইল বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')

    if parts[0] == "sym":
        date = parts[1]
        symbol = parts[2]

        csv_data = hf_manager.read_csv_file(date)

        if csv_data is None:
            await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
            return

        start_idx = 0
        if csv_data and csv_data[0] and len(csv_data[0]) > 0 and csv_data[0][0] == "symbol":
            start_idx = 1

        all_data = csv_data[start_idx:]

        symbol_detail = portfolio_analyzer.get_symbol_detail(date, symbol, all_data)

        if symbol_detail:
            result, reply_markup = portfolio_analyzer.format_symbol_detail_with_buttons(symbol_detail, date)
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            await query.edit_message_text(f"❌ {symbol} সিম্বলের ডাটা পাওয়া যায়নি।")

async def report_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """রিপোর্ট ব্যাক বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')

    if parts[0] == "report":
        date = parts[1]

        csv_data = hf_manager.read_csv_file(date)

        if csv_data is None:
            await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
            return

        start_idx = 0
        if csv_data and csv_data[0] and len(csv_data[0]) > 0 and csv_data[0][0] == "symbol":
            start_idx = 1

        all_data = csv_data[start_idx:]

        stats = portfolio_analyzer.analyze_portfolio(all_data)

        if stats:
            report, reply_markup = portfolio_analyzer.format_portfolio_report_with_buttons(stats, date)
            await query.edit_message_text(report, parse_mode='Markdown', reply_markup=reply_markup)

async def back_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্যাক বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')

    if parts[0] == "back":
        date = parts[1]

        last_data = context.user_data.get('last_view', {})
        category = last_data.get('category', 'vs')
        page = last_data.get('page', 1)

        csv_data = hf_manager.read_csv_file(date)

        if csv_data:
            start_idx = 0
            if csv_data and csv_data[0] and len(csv_data[0]) > 0 and csv_data[0][0] == "symbol":
                start_idx = 1

            all_data = csv_data[start_idx:]
            stats = portfolio_analyzer.analyze_portfolio(all_data)

            if stats:
                if category == "vs":
                    symbols_with_scores = list(zip(stats['very_strong']['symbols'], stats['very_strong']['scores']))
                    title = "🔥 খুব শক্তিশালী সিম্বল (স্কোর 80+)"
                elif category == "vg":
                    symbols_with_scores = list(zip(stats['good']['symbols'], stats['good']['scores']))
                    title = "✅ ভাল সিম্বল (স্কোর 60-79)"
                elif category == "vm":
                    symbols_with_scores = list(zip(stats['medium']['symbols'], stats['medium']['scores']))
                    title = "⚠️ মধ্যম সিম্বল (স্কোর 40-59)"
                elif category == "vw":
                    symbols_with_scores = list(zip(stats['weak']['symbols'], stats['weak']['scores']))
                    title = "❌ দুর্বল সিম্বল (স্কোর <40)"
                elif category == "iw":
                    symbols_with_scores = [(sym, "-") for sym in stats['impulse']['symbols']]
                    title = "📈 ইম্পালস ওয়েভ সিম্বল"
                elif category == "cw":
                    symbols_with_scores = [(sym, "-") for sym in stats['corrective']['symbols']]
                    title = "🔄 করেকটিভ ওয়েভ সিম্বল"
                else:
                    symbols_with_scores = list(zip(stats['very_strong']['symbols'], stats['very_strong']['scores']))
                    title = "🔥 খুব শক্তিশালী সিম্বল (স্কোর 80+)"

                total_pages = (len(symbols_with_scores) + 9) // 10
                if page > total_pages:
                    page = total_pages

                result, reply_markup = portfolio_analyzer.format_symbols_with_buttons(
                    symbols_with_scores, title, date, category, page, total_pages
                )
                await query.edit_message_text(result, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ ডাটা লোড করতে ব্যর্থ হয়েছে।")
        else:
            await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")

async def special_command_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বিশেষ কমান্ডের কলব্যাক হ্যান্ডলার (brrr, hscore, trec, avoid)"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')
    command_type = parts[0]
    date = parts[1] if len(parts) > 1 else None

    if not date:
        await query.edit_message_text("❌ তারিখ পাওয়া যায়নি।")
        return

    csv_data = hf_manager.read_csv_file(date)

    if csv_data is None:
        await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return

    start_idx = 0
    if csv_data and csv_data[0] and len(csv_data[0]) > 0 and csv_data[0][0] == "symbol":
        start_idx = 1

    all_data = csv_data[start_idx:]
    stats = portfolio_analyzer.analyze_portfolio(all_data)

    if command_type == "brrr":
        best_rrr = {'value': 0, 'symbol': '', 'rrr': '', 'score': ''}
        for row in all_data:
            if len(row) > 8:
                symbol = row[0]
                rrr_str = row[8]
                score = row[9] if len(row) > 9 else "-"
                rrr_value = portfolio_analyzer.parse_rrr(rrr_str)
                if rrr_value > best_rrr['value']:
                    best_rrr['value'] = rrr_value
                    best_rrr['symbol'] = symbol
                    best_rrr['rrr'] = rrr_str
                    best_rrr['score'] = score

        if best_rrr['value'] > 0:
            emoji = get_score_emoji(best_rrr['score'])
            result = f"🏆 **সেরা RRR - {date}**\n\n"
            result += f"```\n"
            result += f"সিম্বল      : {best_rrr['symbol']}\n"
            result += f"RRR         : {best_rrr['rrr']}\n"
            result += f"স্কোর       : {best_rrr['score']}/100 {emoji}\n"
            result += f"```"
            keyboard = [[InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")]]
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("❌ কোনো RRR ডাটা পাওয়া যায়নি।")

    elif command_type == "hscore":
        highest = {'value': 0, 'symbol': '', 'score': ''}
        for row in all_data:
            if len(row) > 9:
                symbol = row[0]
                score_str = row[9]
                try:
                    score_val = int(score_str)
                    if score_val > highest['value']:
                        highest['value'] = score_val
                        highest['symbol'] = symbol
                        highest['score'] = score_str
                except:
                    continue

        if highest['value'] > 0:
            emoji = get_score_emoji(highest['score'])
            result = f"💎 **সর্বোচ্চ স্কোর - {date}**\n\n"
            result += f"```\n"
            result += f"সিম্বল      : {highest['symbol']}\n"
            result += f"স্কোর       : {highest['score']}/100 {emoji}\n"
            result += f"```"
            keyboard = [[InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")]]
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("❌ কোনো স্কোর ডাটা পাওয়া যায়নি।")

    elif command_type == "trec":
        if stats and stats['top_recommendations']:
            result = f"💡 **টপ রিকমেন্ডেশন - {date}**\n\n"
            result += "```\n"
            result += f"{'ক্রম':<6} {'সিম্বল':<15} {'স্কোর':<10} {'RRR'}\n"
            result += "-" * 45 + "\n"
            for i, sym in enumerate(stats['top_recommendations'][:10]):
                score = "-"
                rrr = "-"
                for row in all_data:
                    if row[0] == sym:
                        if len(row) > 9:
                            score = row[9]
                        if len(row) > 8:
                            rrr = row[8]
                        break
                emoji = get_score_emoji(score)
                result += f"{i+1:<6} {sym:<15} {score}/100 {emoji:<5} {rrr}\n"
            result += "```"
            keyboard = [[InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")]]
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(f"📭 {date} তারিখে কোনো টপ রিকমেন্ডেশন নেই।")

    elif command_type == "avoid":
        if stats and stats['avoid_symbols']:
            result = f"⚠️ **এড়িয়ে চলুন - {date}**\n\n"
            result += "```\n"
            result += f"{'ক্রম':<6} {'সিম্বল':<15} {'স্কোর':<10} {'রেটিং'}\n"
            result += "-" * 45 + "\n"
            for i, sym in enumerate(stats['avoid_symbols'][:10]):
                score = "-"
                for row in all_data:
                    if row[0] == sym and len(row) > 9:
                        score = row[9]
                        break
                emoji = get_score_emoji(score)
                result += f"{i+1:<6} {sym:<15} {score}/100 {emoji:<5} খুব দুর্বল\n"
            result += "```"
            keyboard = [[InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")]]
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(f"📭 {date} তারিখে কোনো দুর্বল সিম্বল নেই।")

# ==================== TELEGRAM HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট - Hugging Face স্টোরেজ**\n\n"
        "📝 **ডাটা যোগ করুন (11 কলাম):**\n"
        "`ADVENT,Impulse (Up),Wave 5 of 3,13.8-14.2,13.2,15.0,16.0,17.5,1:2.5,68,মূল্য 13.0 টাকার নিচে ব্রেক করতে পারেনি...`\n\n"
        "📚 **বেসিক কমান্ড:**\n"
        "`/help` - সব কমান্ড দেখুন\n"
        "`/list` - আজকের ডাটা দেখুন\n"
        "`/portfolio` - পোর্টফোলিও অ্যানালাইসিস (ইনলাইন বাটন সহ)\n"
        "`/trademenu` - ট্রেডিং অ্যানালাইটিক্স (ইনলাইন বাটন সহ)\n"
        "`/insight [সিম্বল] [তারিখ]` - সম্পূর্ণ ইনসাইট দেখুন\n"
        "`/files` - সব CSV ফাইলের তালিকা\n"
        "`/view [তারিখ] [পৃষ্ঠা]` - কার্ড স্টাইলে ফাইল দেখুন\n"
        "`/symbols [তারিখ]` - ফাইলের সিম্বল দেখুন\n"
        "`/search [সিম্বল]` - সব ফাইলে সিম্বল খুঁজুন\n"
        "`/searchsymbol [সিম্বল]` - ট্রেড ডাটাবেজে সিম্বল খুঁজুন\n"
        "`/deletesymbol [তারিখ] [সিম্বল]` - সিম্বল ডিলিট\n"
        "`/deletefile [তারিখ]` - ফাইল ডিলিট\n"
        "`/clear` - আজকের ডাটা ক্লিয়ার\n"
        "`/status` - স্ট্যাটাস দেখুন\n"
        "`/reload` - ডাটা রিলোড করুন\n\n"
        "📊 **অ্যাডভান্সড কমান্ড:**\n"
        "`/chart [তারিখ]` - স্কোর ডিস্ট্রিবিউশন চার্ট\n"
        "`/compare [তারিখ1] [তারিখ2]` - পোর্টফোলিও তুলনা\n"
        "`/backtest [স্টার্ট] [এন্ড] [স্কোর]` - ব্যাকটেস্টিং\n"
        "`/export [তারিখ]` - CSV এক্সপোর্ট\n"
        "`/setalert [স্কোর]` - অ্যালার্ট সেট করুন\n\n"
        "📊 **স্কোর রেটিং:**\n"
        "💎 85+ এক্সট্রিম | 🔥 80-84 খুব শক্তিশালী | ⭐ 70-79 শক্তিশালী\n"
        "✅ 60-69 ভাল | 📈 50-59 মধ্যম | ⚠️ 40-49 দুর্বল | ❌ <40 খুব দুর্বল",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **স্টক ডাটা বট - সম্পূর্ণ গাইড**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 **ডাটা যোগ করার নিয়ম (11 কলাম)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`ADVENT,Impulse (Up),Wave 5 of 3,13.8-14.2,13.2,15.0,16.0,17.5,1:2.5,68,মূল্য 13.0 টাকার নিচে ব্রেক করতে পারেনি...`

**কলামের ক্রম:**
1. symbol | 2. এলিয়ট ওয়েব | 3. সাব-ওয়েব | 4. এন্ট্রি | 5. স্টপ
6. TP1 | 7. TP2 | 8. TP3 | 9. RRR | 10. স্কোর | 11. কুইক ইনসাইট

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **অ্যাডভান্সড ফিচার**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/chart 29-03-2026` - স্কোর ডিস্ট্রিবিউশন চার্ট
• `/compare 25-03-2026 29-03-2026` - পোর্টফোলিও তুলনা
• `/backtest 01-03-2026 29-03-2026 70` - ব্যাকটেস্টিং
• `/export 29-03-2026` - CSV এক্সপোর্ট
• `/setalert 70` - 70+ স্কোরের অ্যালার্ট

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **ইনসাইট দেখার নিয়ম**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/insight ADVENT` - সর্বশেষ ফাইল থেকে দেখাবে
• `/insight ADVENT 25-03-2026` - নির্দিষ্ট তারিখের ফাইল থেকে দেখাবে

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 **ফাইল ম্যানেজমেন্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/files` - সব CSV ফাইলের তালিকা (ক্রম, ফাইল নাম, সিম্বল সংখ্যা)
• `/view 25-03-2026` - প্রথম পৃষ্ঠা দেখাবে
• `/view 25-03-2026 2` - দ্বিতীয় পৃষ্ঠা দেখাবে
• `/deletefile 25-03-2026` - ফাইল ডিলিট

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **সিম্বল ম্যানেজমেন্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/symbols 25-03-2026` - সিম্বল লিস্ট
• `/deletesymbol 25-03-2026 ADVENT` - সিম্বল ডিলিট
• `/search ADVENT` - সব ফাইলে খুঁজুন

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **আজকের ডাটা**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/list` - আজকের ডাটা দেখুন
• `/clear` - আজকের সব ডাটা মুছুন
• `/yesclear` - ক্লিয়ার কনফার্ম

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **পোর্টফোলিও অ্যানালাইসিস (ইনলাইন বাটন সহ)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/portfolio [তারিখ]` - সম্পূর্ণ পোর্টফোলিও রিপোর্ট (বাটন সহ)
• বাটনে ক্লিক করে বিস্তারিত দেখুন
• সিম্বলের নামে ক্লিক করে সম্পূর্ণ ইনসাইট দেখুন

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **ট্রেডিং অ্যানালাইটিক্স (ইনলাইন বাটন সহ)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/trademenu` - ট্রেডিং অ্যানালাইটিক্স মেনু (বাটন সহ)
• সক্রিয় ট্রেড, টিপি, এসএল লিস্ট দেখুন
• ওয়েভ, গ্যাপ, টিপি লেভেল, স্কোর অনুযায়ী বিশ্লেষণ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 **স্কোর রেটিং চার্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 85-100 : এক্সট্রিম শক্তিশালী
🔥 80-84  : খুব শক্তিশালী
⭐ 70-79  : শক্তিশালী
✅ 60-69  : ভাল
📈 50-59  : মধ্যম
⚠️ 40-49  : দুর্বল
❌ <40    : খুব দুর্বল
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def insight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট সিম্বলের সম্পূর্ণ কুইক ইনসাইট দেখান"""
    if not context.args:
        await update.message.reply_text("❌ সিম্বল দিন। উদাহরণ: `/insight ADVENT` অথবা `/insight ADVENT 25-03-2026`")
        return

    symbol = context.args[0].upper()

    if len(context.args) > 1:
        date = fix_date_format(context.args[1])
    else:
        files = hf_manager.get_all_csv_files()
        if files:
            date = files[0]
        else:
            await update.message.reply_text("❌ কোনো CSV ফাইল নেই।")
            return

    status_msg = await update.message.reply_text(f"⏳ '{symbol}' এর ইনসাইট খুঁজছি ({date})...")

    data = hf_manager.read_csv_file(date)

    if data is None:
        await status_msg.edit_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return

    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1

    for row in data[start_idx:]:
        if row and len(row) > 0 and row[0].upper() == symbol:
            insight = row[10] if len(row) > 10 else "কোনো ইনসাইট নেই"
            score = row[9] if len(row) > 9 else "-"
            score_emoji = get_score_emoji(score)
            score_text = get_score_text(score)

            tp1 = row[5] if len(row) > 5 else "-"
            tp2 = row[6] if len(row) > 6 else "-"
            tp3 = row[7] if len(row) > 7 else "-"
            
            main_wave = row[1] if len(row) > 1 else "-"
            sub_wave = row[2] if len(row) > 2 and row[2].strip() else "-"

            message = f"""
📊 **{symbol} - সম্পূর্ণ বিশ্লেষণ**

📅 তারিখ: `{date}`

🌊 **এলিয়ট ওয়েব অবস্থান:**
• এলিয়ট ওয়েব: `{main_wave}`
• সাব-ওয়েব: `{sub_wave}`

📈 **ট্রেডিং প্যারামিটারস:**
• এন্ট্রি জোন: `{row[3]}`
• স্টপ লস: `{row[4]}`
• TP1: `{tp1}`
• TP2: `{tp2}`
• TP3: `{tp3}`
• RRR: `{row[8]}`
• স্কোর: `{score}/100 {score_emoji}` - {score_text}

🔍 **টেকনিক্যাল ইনসাইট:**
{insight}
"""
            await status_msg.edit_text(message, parse_mode='Markdown')
            return

    await status_msg.edit_text(f"❌ '{symbol}' সিম্বলটি {date}.csv ফাইলে পাওয়া যায়নি।")

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
            "❌ CSV ফরম্যাটে 11টি কলাম পাঠান। সাহায্যের জন্য `/help` দেখুন।\n\n"
            "উদাহরণ:\n"
            "`ADVENT,Impulse (Up),Wave 5 of 3,13.8-14.2,13.2,15.0,16.0,17.5,1:2.5,68,মূল্য 13.0 টাকার নিচে ব্রেক করতে পারেনি...`",
            parse_mode='Markdown'
        )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আজকের ডাটা দেখান - শুধু আজকের"""
    if not bot.current_data:
        await update.message.reply_text(f"📭 {bot.current_date} তারিখের কোনো ডাটা নেই।")
        return

    table = format_as_table(bot.current_data, f"{bot.current_date} - আজকের ডাটা", 0, len(bot.current_data), 1, 1)

    if len(table) > 4000:
        parts = [table[i:i+4000] for i in range(0, len(table), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(table, parse_mode='Markdown')

def format_as_table(data, title, offset=0, total_records=0, current_page=1, total_pages=1):
    """কার্ড ডিজাইন - সম্পূর্ণ ডিটেইলস + আলাদা সাব-ওয়েব"""
    if not data:
        return f"📭 {title} - কোনো ডাটা নেই।"

    result = f"📊 **{title}**  |  📋 {total_records} টি রেকর্ড  |  📄 পৃষ্ঠা {current_page}/{total_pages}\n\n"
    result += "```\n"

    for i, row in enumerate(data):
        serial = i + 1 + offset

        score = row[9] if len(row) > 9 else "-"
        score_emoji = get_score_emoji(score)
        symbol_emoji = score_emoji

        # এলিয়ট ওয়েব এবং সাব-ওয়েব আলাদা
        main_wave = row[1] if len(row) > 1 else "-"
        sub_wave = row[2] if len(row) > 2 and row[2].strip() else "-"

        entry = row[3] if len(row) > 3 else "-"
        stop = row[4] if len(row) > 4 else "-"
        tp1 = row[5] if len(row) > 5 else "-"
        tp2 = row[6] if len(row) > 6 else "-"
        tp3 = row[7] if len(row) > 7 else "-"
        rrr = row[8] if len(row) > 8 else "-"
        insight = row[10] if len(row) > 10 else "কোনো ইনসাইট নেই"

        result += f"╔══════════════════════════════════════════════════════════════════════════════╗\n"
        result += f"║ #{serial} {row[0]} {symbol_emoji}\n"
        result += f"╠══════════════════════════════════════════════════════════════════════════════╣\n"
        result += f"║ 🌊 এলিয়ট ওয়েব : {main_wave}\n"
        
        # সাব-ওয়েব দেখান (যদি থাকে)
        if sub_wave != "-":
            result += f"║ 📍 সাব-ওয়েব    : {sub_wave}\n"
        
        result += f"║ 📈 এন্ট্রি  : {entry}  |  🛑 স্টপ: {stop}\n"
        result += f"║ 🎯 টার্গেট  : {tp1} → {tp2} → {tp3}  |  📊 RRR: {rrr}\n"
        result += f"║ 🏆 স্কোর    : {score}/100 {score_emoji}  |  {get_score_text(score)}\n"

        insight_lines = []
        for j in range(0, len(insight), 70):
            insight_lines.append(insight[j:j+70])

        for idx, line in enumerate(insight_lines):
            if idx == 0:
                result += f"║ 💡 ইনসাইট  : {line}\n"
            else:
                result += f"║              {line}\n"

        result += f"╚══════════════════════════════════════════════════════════════════════════════╝\n\n"

    result += "```"
    return result

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
    """সব CSV ফাইলের তালিকা দেখান - ক্রম, ফাইল নাম, সিম্বল সংখ্যা"""
    dates = hf_manager.get_all_csv_files()

    if not dates:
        await update.message.reply_text("📭 কোনো CSV ফাইল নেই।")
        return

    table = format_files_table(dates)
    await update.message.reply_text(table, parse_mode='Markdown')

def format_files_table(dates):
    """ফাইলের তালিকা দেখান - ক্রম, ফাইল নাম, সিম্বল সংখ্যা"""
    if not dates:
        return "📭 কোনো CSV ফাইল নেই।"

    # প্রথমে প্রতিটি ফাইলের জন্য সিম্বল কাউন্ট গণনা করুন
    file_stats = []
    for date in dates:
        data = hf_manager.read_csv_file(date)
        symbol_count = 0
        
        if data and len(data) > 0:
            start_idx = 0
            if data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                start_idx = 1
            
            all_data = data[start_idx:]
            symbol_count = len(all_data)
        
        file_stats.append({
            'date': date,
            'symbols': symbol_count
        })

    table = f"📁 **CSV ফাইলের তালিকা ({len(dates)} টি):**\n\n```\n"
    table += f"{'ক্রম':<6} {'ফাইলের নাম':<20} {'সিম্বল':<10}\n"
    table += "-" * 36 + "\n"

    for i, stats in enumerate(file_stats):
        table += f"{i+1:<6} {stats['date']}.csv{' ':<{20-len(stats['date'])-4}} {stats['symbols']:<10}\n"

    table += "```"
    
    # সামারি যোগ করুন
    total_symbols = sum(s['symbols'] for s in file_stats)
    table += f"\n📊 **মোট সিম্বল:** {total_symbols} টি"
    
    return table

async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট তারিখের CSV ফাইল দেখান - শুধু সেই তারিখের ডাটা"""
    if not context.args:
        await update.message.reply_text(
            "❌ 📅 তারিখ দিন। উদাহরণ: `/view 25-03-2026` অথবা `/view 25-03-2026 2`\n\n"
            "📌 পৃষ্ঠা নম্বর না দিলে 1 নম্বর পৃষ্ঠা দেখাবে।",
            parse_mode='Markdown'
        )
        return

    date_input = context.args[0].strip()
    date = fix_date_format(date_input)

    page = 1
    if len(context.args) > 1:
        try:
            page = int(context.args[1])
            if page < 1:
                page = 1
        except:
            page = 1

    items_per_page = 5

    status_msg = await update.message.reply_text(f"⏳ 🔍 `{date}.csv` ফাইল খুঁজছি...", parse_mode='Markdown')

    try:
        data = hf_manager.read_csv_file(date)

        if data is None:
            await status_msg.edit_text(f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।\n\n💡 `/files` দেখে উপলব্ধ ফাইল চেক করুন।", parse_mode='Markdown')
            return

        if not data:
            await status_msg.edit_text(f"📭 `{date}.csv` ফাইলটি খালি।", parse_mode='Markdown')
            return

        start_idx = 0
        if len(data) > 0 and len(data[0]) > 0 and data[0][0] == "symbol":
            start_idx = 1

        all_data = data[start_idx:]

        if not all_data:
            await status_msg.edit_text(f"📭 `{date}.csv` ফাইলে কোনো ডাটা নেই।", parse_mode='Markdown')
            return

        total_records = len(all_data)
        total_pages = (total_records + items_per_page - 1) // items_per_page

        if page > total_pages:
            page = total_pages

        start = (page - 1) * items_per_page
        end = start + items_per_page
        page_data = all_data[start:end]

        offset = start

        table = format_as_table(page_data, f"{date}.csv", offset, total_records, page, total_pages)

        nav_parts = []

        if page > 1:
            nav_parts.append(f"[◀️](/view {date} {page-1})")
        else:
            nav_parts.append("◀️")

        if total_pages <= 7:
            for p in range(1, total_pages + 1):
                if p == page:
                    nav_parts.append(f"**{p}**")
                else:
                    nav_parts.append(f"[{p}](/view {date} {p})")
        else:
            if page <= 4:
                for p in range(1, 6):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/view {date} {p})")
                nav_parts.append("...")
                nav_parts.append(f"[{total_pages}](/view {date} {total_pages})")
            elif page >= total_pages - 3:
                nav_parts.append(f"[1](/view {date} 1)")
                nav_parts.append("...")
                for p in range(total_pages - 4, total_pages + 1):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/view {date} {p})")
            else:
                nav_parts.append(f"[1](/view {date} 1)")
                nav_parts.append("...")
                for p in range(page - 1, page + 2):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/view {date} {p})")
                nav_parts.append("...")
                nav_parts.append(f"[{total_pages}](/view {date} {total_pages})")

        if page < total_pages:
            nav_parts.append(f"[▶️](/view {date} {page+1})")
        else:
            nav_parts.append("▶️")

        nav_bar = " ".join(nav_parts)

        final_message = table + f"\n\n{nav_bar}"

        if len(final_message) > 4000:
            await status_msg.delete()
            parts = [final_message[i:i+4000] for i in range(0, len(final_message), 4000)]
            for part in parts:
                await update.message.reply_text(part, parse_mode='Markdown')
        else:
            await status_msg.edit_text(final_message, parse_mode='Markdown')

    except Exception as e:
        print(f"❌ View command error: {e}")
        import traceback
        traceback.print_exc()
        await status_msg.edit_text(f"❌ ত্রুটি: {str(e)[:200]}")

async def deletefile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট তারিখের CSV ফাইল ডিলিট করুন"""
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
    """ফাইল ডিলিট কনফার্ম"""
    date = context.user_data.get('delete_file')
    if not date:
        await update.message.reply_text("❌ আগে `/deletefile` দিন।")
        return

    success, msg = hf_manager.delete_csv_file(date)
    await update.message.reply_text(msg)
    context.user_data['delete_file'] = None

async def symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ফাইলের সিম্বল লিস্ট দেখান"""
    if context.args:
        date = fix_date_format(context.args[0])
    else:
        date = bot.current_date

    status_msg = await update.message.reply_text(f"⏳ `{date}.csv` ফাইল থেকে সিম্বল খুঁজছি...", parse_mode='Markdown')

    data = hf_manager.read_csv_file(date)

    if data is None:
        dates = hf_manager.get_all_csv_files()
        if dates:
            file_list = "\n".join([f"• `{d}.csv`" for d in dates[:10]])
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

    symbols_with_scores = []
    for row in data[start_idx:]:
        if row and len(row) > 0:
            symbol = row[0]
            score = row[9] if len(row) > 9 else "-"
            score_emoji = get_score_emoji(score)
            symbols_with_scores.append(f"{symbol} {score_emoji}")

    if not symbols_with_scores:
        await status_msg.edit_text(f"📭 `{date}.csv` ফাইলে কোনো সিম্বল নেই।", parse_mode='Markdown')
        return

    symbol_lines = []
    for i in range(0, len(symbols_with_scores), 4):
        batch = symbols_with_scores[i:i+4]
        symbol_lines.append(" | ".join(batch))

    symbol_list = "\n".join([f"{i+1:3}. {line}" for i, line in enumerate(symbol_lines)])

    await status_msg.edit_text(
        f"📋 **{date}.csv - সিম্বল লিস্ট ({len(symbols_with_scores)} টি):**\n\n{symbol_list}\n\n"
        f"💡 সিম্বল ডিলিট: `/deletesymbol {date} [সিম্বল]`\n"
        f"💡 সম্পূর্ণ ইনসাইট: `/insight [সিম্বল] {date}`\n\n"
        f"📊 **স্কোর রেটিং:** 💎85+ 🔥80-84 ⭐70-79 ✅60-69 📈50-59 ⚠️40-49 ❌<40",
        parse_mode='Markdown'
    )

async def deletesymbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট সিম্বল ডিলিট করুন"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ তারিখ এবং সিম্বল দিন। উদাহরণ: `/deletesymbol 25-03-2026 ADVENT`",
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
        await update.message.reply_text("❌ সিম্বল দিন। উদাহরণ: `/search ADVENT`")
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

def get_search_results_table(results, search_symbol):
    """সার্চ রেজাল্ট দেখান"""
    if not results:
        return f"❌ '{search_symbol}' কোনো ফাইলে পাওয়া যায়নি।"

    headers = ["#", "তারিখ", "সিম্বল", "এলিয়ট ওয়েব", "সাব-ওয়েব", "এন্ট্রি", "স্কোর"]
    col_widths = [4, 12, 12, 18, 15, 12, 6]

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
        line += f"{r['row'][1][:col_widths[3]]:<{col_widths[3]}}" if len(r['row']) > 1 else f"{'':<{col_widths[3]}}"
        
        # সাব-ওয়েব দেখান
        sub_wave = r['row'][2] if len(r['row']) > 2 else "-"
        line += f"{sub_wave[:col_widths[4]]:<{col_widths[4]}}"
        
        line += f"{r['row'][3][:col_widths[5]]:<{col_widths[5]}}" if len(r['row']) > 3 else f"{'':<{col_widths[5]}}"

        score = r['row'][9] if len(r['row']) > 9 else "-"
        score_emoji = get_score_emoji(score)
        line += f"{score}/100 {score_emoji}"
        table += line + "\n"

    table += "```"
    return table

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বটের স্ট্যাটাস দেখান"""
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
    """অপারেশন বাতিল করুন"""
    context.user_data.clear()
    await update.message.reply_text("✅ অপারেশন বাতিল করা হয়েছে।")

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hugging Face থেকে আজকের ডাটা রিলোড করুন"""
    await update.message.reply_text("⏳ ডাটা রিলোড করা হচ্ছে...")
    bot.load_current_data()
    if bot.current_data:
        await update.message.reply_text(f"✅ {len(bot.current_data)} টি রেকর্ড রিলোড হয়েছে।")
    else:
        await update.message.reply_text("✅ আজকের ডাটা খালি করা হয়েছে।")

# ==================== FLASK ROUTES ====================

@app.route('/')
def home():
    return jsonify({
        "status": "active",
        "bot": "Stock Data Bot with Portfolio Analytics, Trade Analytics & Advanced Features",
        "hf_repo": HF_REPO,
        "today_records": len(bot.current_data),
        "columns": len(COLUMNS),
        "columns_list": COLUMNS,
        "features": ["Chart", "Compare", "Backtest", "Export", "Alert"],
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

        # বেসিক কমান্ড
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("insight", insight_command))
        application.add_handler(CommandHandler("reload", reload_command))
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

        # পোর্টফোলিও কমান্ড (ইনলাইন বাটন সহ)
        application.add_handler(CommandHandler("portfolio", portfolio_command))

        # অ্যাডভান্সড ফিচার কমান্ড
        application.add_handler(CommandHandler("chart", chart_command_wrapper))
        application.add_handler(CommandHandler("compare", compare_command_wrapper))
        application.add_handler(CommandHandler("notify", notify_command_wrapper))
        application.add_handler(CommandHandler("setalert", setalert_command_wrapper))
        application.add_handler(CommandHandler("backtest", backtest_command_wrapper))
        application.add_handler(CommandHandler("export", export_command_wrapper))

        # ইনলাইন বাটন কলব্যাক হ্যান্ডলার
        application.add_handler(CallbackQueryHandler(category_callback_handler, pattern='^(vs|vg|vm|vw|iw|cw)_'))
        application.add_handler(CallbackQueryHandler(symbol_detail_callback_handler, pattern='^sym_'))
        application.add_handler(CallbackQueryHandler(report_callback_handler, pattern='^report_'))
        application.add_handler(CallbackQueryHandler(back_callback_handler, pattern='^back_'))
        application.add_handler(CallbackQueryHandler(special_command_callback_handler, pattern='^(brrr|hscore|trec|avoid)_'))

        # ট্রেড অ্যানালাইটিক্স হ্যান্ডলার যোগ করুন
        add_trade_analytics_handlers(application)

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("🤖 Telegram Bot starting with Inline Buttons, Trade Analytics & Advanced Features...")
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