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
            self.current_data = []
            print(f"⚠️ No data for {self.current_date}, starting with empty list")

    def get_data_for_date(self, date):
        """নির্দিষ্ট তারিখের ডাটা লোড করুন"""
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
        """শুধু আজকের ডাটায় যোগ করুন"""
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

def get_wave_emoji(wave, subwave):
    """ওয়েভ টাইপ অনুযায়ী ইমোজি রিটার্ন করুন"""
    if "Impulse" in wave:
        return "⚡"
    elif "Corrective" in wave:
        return "🌀"
    
    if subwave != "-":
        if "Wave 1" in subwave or "Wave 3" in subwave or "Wave 5" in subwave:
            return "📈"
        elif "Wave 2" in subwave or "Wave 4" in subwave:
            return "📉"
        elif "A" in subwave or "B" in subwave or "C" in subwave:
            return "🔄"
    return "🌊"

def get_subwave_emoji(subwave):
    """সাব-ওয়েব অনুযায়ী ইমোজি রিটার্ন করুন"""
    if subwave == "-":
        return "📍"
    if "Wave 1" in subwave or "Wave 3" in subwave or "Wave 5" in subwave:
        return "📈"
    elif "Wave 2" in subwave or "Wave 4" in subwave:
        return "📉"
    elif "A" in subwave or "B" in subwave or "C" in subwave:
        return "🔄"
    return "📍"

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
            return "এক্সট্রিম শক্তিশালী"
        elif score_num >= 80:
            return "খুব শক্তিশালী"
        elif score_num >= 70:
            return "শক্তিশালী"
        elif score_num >= 60:
            return "ভাল"
        elif score_num >= 50:
            return "মধ্যম"
        elif score_num >= 40:
            return "দুর্বল"
        else:
            return "খুব দুর্বল"
    except:
        return "সাধারণ"

# ==================== UPDATED FORMAT FUNCTION WITH WAVE + SUBWAVE ====================

def format_as_table(data, title, offset=0, total_records=0, current_page=1, total_pages=1):
    """কার্ড ডিজাইন - এলিয়ট ওয়েব এবং সাব-ওয়েব আলাদাভাবে দেখানো হবে"""
    if not data:
        return f"📭 {title} - কোনো ডাটা নেই।"

    result = f"📊 **{title}**  |  📋 {total_records} টি রেকর্ড  |  📄 পৃষ্ঠা {current_page}/{total_pages}\n\n"
    result += "```\n"

    for i, row in enumerate(data):
        serial = i + 1 + offset

        # ডাটা এক্সট্রাক্ট
        symbol = row[0] if len(row) > 0 else "-"
        wave = row[1] if len(row) > 1 else "-"
        subwave = row[2] if len(row) > 2 else "-"
        entry = row[3] if len(row) > 3 else "-"
        stop = row[4] if len(row) > 4 else "-"
        tp1 = row[5] if len(row) > 5 else "-"
        tp2 = row[6] if len(row) > 6 else "-"
        tp3 = row[7] if len(row) > 7 else "-"
        rrr = row[8] if len(row) > 8 else "-"
        score = row[9] if len(row) > 9 else "-"
        insight = row[10] if len(row) > 10 else "কোনো ইনসাইট নেই"

        # ইমোজি
        score_emoji = get_score_emoji(score)
        wave_emoji = get_wave_emoji(wave, subwave)
        subwave_emoji = get_subwave_emoji(subwave)

        result += f"╔══════════════════════════════════════════════════════════════════════════════╗\n"
        result += f"║ #{serial} {symbol} {score_emoji}\n"
        result += f"╠══════════════════════════════════════════════════════════════════════════════╣\n"
        
        # এলিয়ট ওয়েব লাইন (ইমোজি সহ)
        result += f"║ {wave_emoji} এলিয়ট ওয়েব : {wave}\n"
        
        # সাব-ওয়েব লাইন (ইমোজি সহ)
        if subwave != "-":
            result += f"║ {subwave_emoji} সাব-ওয়েব    : {subwave}\n"
        else:
            result += f"║ 📍 সাব-ওয়েব    : -\n"
        
        result += f"║ ─────────────────────────────────────────────────────────────────────────────║\n"
        result += f"║ 📈 এন্ট্রি     : {entry}  |  🛑 স্টপ লস: {stop}\n"
        result += f"║ 🎯 টার্গেট     : {tp1} → {tp2} → {tp3}\n"
        result += f"║ 📊 RRR         : {rrr}  |  🏆 স্কোর: {score}/100 {score_emoji}\n"
        result += f"║ 💬 রেটিং       : {get_score_text(score)}\n"
        result += f"║ ─────────────────────────────────────────────────────────────────────────────║\n"

        # ইনসাইট লাইন ব্রেক
        insight_lines = []
        for j in range(0, len(insight), 68):
            insight_lines.append(insight[j:j+68])

        for idx, line in enumerate(insight_lines):
            if idx == 0:
                result += f"║ 💡 ইনসাইট     : {line}\n"
            else:
                result += f"║                {line}\n"

        result += f"╚══════════════════════════════════════════════════════════════════════════════╝\n\n"

    result += "```"
    return result

# ==================== UPDATED VIEW COMMAND ====================

async def view_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নির্দিষ্ট তারিখের CSV ফাইল দেখান - এলিয়ট ওয়েব এবং সাব-ওয়েব সহ"""
    if not context.args:
        await update.message.reply_text(
            "❌ 📅 তারিখ দিন। উদাহরণ: `/view 25-03-2026` অথবা `/view 25-03-2026 2`\n\n"
            "📌 পৃষ্ঠা নম্বর না দিলে 1 নম্বর পৃষ্ঠা দেখাবে।\n\n"
            "🌊 **ওয়েভ ইমোজি বুঝতে সাহায্য:**\n"
            "⚡ = ইম্পালস ওয়েভ | 🌀 = করেকটিভ ওয়েভ\n"
            "📈 = আপট্রেন্ড সাব-ওয়েব | 📉 = ডাউনট্রেন্ড সাব-ওয়েব | 🔄 = করেকটিভ সাব-ওয়েব",
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

        # নেভিগেশন বার তৈরি
        nav_parts = []

        if page > 1:
            nav_parts.append(f"[◀️ Prev](/view {date} {page-1})")
        else:
            nav_parts.append("◀️")

        if total_pages <= 10:
            for p in range(1, total_pages + 1):
                if p == page:
                    nav_parts.append(f"**{p}**")
                else:
                    nav_parts.append(f"[{p}](/view {date} {p})")
        else:
            if page <= 5:
                for p in range(1, 7):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/view {date} {p})")
                nav_parts.append("...")
                nav_parts.append(f"[{total_pages}](/view {date} {total_pages})")
            elif page >= total_pages - 4:
                nav_parts.append(f"[1](/view {date} 1)")
                nav_parts.append("...")
                for p in range(total_pages - 5, total_pages + 1):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/view {date} {p})")
            else:
                nav_parts.append(f"[1](/view {date} 1)")
                nav_parts.append("...")
                for p in range(page - 2, page + 3):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/view {date} {p})")
                nav_parts.append("...")
                nav_parts.append(f"[{total_pages}](/view {date} {total_pages})")

        if page < total_pages:
            nav_parts.append(f"[Next ▶️](/view {date} {page+1})")
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

# ==================== NEW COMMAND: WAVE SUMMARY ====================

async def wavesummary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ওয়েভ এবং সাব-ওয়েব সারাংশ দেখান"""
    if not context.args:
        await update.message.reply_text(
            "❌ 📅 তারিখ দিন। উদাহরণ: `/wavesummary 25-03-2026`\n\n"
            "এটি এলিয়ট ওয়েব এবং সাব-ওয়েবের সারাংশ দেখাবে।",
            parse_mode='Markdown'
        )
        return

    date = fix_date_format(context.args[0])
    
    status_msg = await update.message.reply_text(f"⏳ `{date}.csv` ফাইল অ্যানালাইসিস করা হচ্ছে...", parse_mode='Markdown')
    
    data = hf_manager.read_csv_file(date)
    
    if data is None:
        await status_msg.edit_text(f"❌ `{date}.csv` ফাইল পাওয়া যায়নি।", parse_mode='Markdown')
        return
    
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    
    all_data = data[start_idx:]
    
    if not all_data:
        await status_msg.edit_text(f"📭 `{date}.csv` ফাইলে কোনো ডাটা নেই।", parse_mode='Markdown')
        return
    
    # ওয়েভ এবং সাব-ওয়েব বিশ্লেষণ
    impulse_waves = []
    corrective_waves = []
    wave_patterns = {}
    subwave_patterns = {}
    wave_subwave_list = []
    
    for row in all_data:
        symbol = row[0] if len(row) > 0 else "-"
        wave = row[1] if len(row) > 1 else "-"
        subwave = row[2] if len(row) > 2 else "-"
        score = row[9] if len(row) > 9 else "-"
        
        wave_subwave_list.append({
            'symbol': symbol,
            'wave': wave,
            'subwave': subwave,
            'score': score
        })
        
        if "Impulse" in wave:
            impulse_waves.append((symbol, wave, subwave, score))
        elif "Corrective" in wave:
            corrective_waves.append((symbol, wave, subwave, score))
        
        if wave != "-":
            wave_patterns[wave] = wave_patterns.get(wave, 0) + 1
        
        if subwave != "-":
            subwave_patterns[subwave] = subwave_patterns.get(subwave, 0) + 1
    
    # রিপোর্ট তৈরি
    result = f"📊 **{date}.csv - এলিয়ট ওয়েভ অ্যানালাইসিস**\n\n"
    result += "```\n"
    result += f"{'ক্রম':<6} {'সিম্বল':<12} {'এলিয়ট ওয়েব':<28} {'সাব-ওয়েব':<28} {'স্কোর'}\n"
    result += "-" * 90 + "\n"
    
    for i, item in enumerate(wave_subwave_list[:20]):
        wave_display = item['wave'][:25] + ".." if len(item['wave']) > 27 else item['wave']
        subwave_display = item['subwave'][:25] + ".." if len(item['subwave']) > 27 else item['subwave']
        score_emoji = get_score_emoji(item['score'])
        result += f"{i+1:<6} {item['symbol']:<12} {wave_display:<28} {subwave_display:<28} {item['score']}/100 {score_emoji}\n"
    
    result += "```\n\n"
    
    # সারাংশ
    result += f"📈 **ইম্পালস ওয়েভ ({len(impulse_waves)} টি):**\n"
    if impulse_waves:
        for sym, wave, subwave, score in impulse_waves[:10]:
            score_emoji = get_score_emoji(score)
            result += f"• {sym}: {subwave} [{score}/100 {score_emoji}]\n"
        if len(impulse_waves) > 10:
            result += f"• ... এবং {len(impulse_waves) - 10} টি অন্যান্য\n"
    else:
        result += "• কোনো ইম্পালস ওয়েভ নেই\n"
    
    result += f"\n🔄 **করেকটিভ ওয়েভ ({len(corrective_waves)} টি):**\n"
    if corrective_waves:
        for sym, wave, subwave, score in corrective_waves[:10]:
            score_emoji = get_score_emoji(score)
            result += f"• {sym}: {subwave} [{score}/100 {score_emoji}]\n"
        if len(corrective_waves) > 10:
            result += f"• ... এবং {len(corrective_waves) - 10} টি অন্যান্য\n"
    else:
        result += "• কোনো করেকটিভ ওয়েভ নেই\n"
    
    if wave_patterns:
        result += f"\n🔝 **টপ ওয়েভ প্যাটার্ন:**\n"
        sorted_waves = sorted(wave_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        for pattern, count in sorted_waves:
            result += f"• {pattern}: {count} টি\n"
    
    if subwave_patterns:
        result += f"\n📍 **টপ সাব-ওয়েব প্যাটার্ন:**\n"
        sorted_subwaves = sorted(subwave_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        for pattern, count in sorted_subwaves:
            result += f"• {pattern}: {count} টি\n"
    
    await status_msg.edit_text(result, parse_mode='Markdown')

# ==================== UPDATED LIST COMMAND ====================

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আজকের ডাটা দেখান - এলিয়ট ওয়েব এবং সাব-ওয়েব সহ"""
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

# ==================== UPDATED START COMMAND ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট - Hugging Face স্টোরেজ**\n\n"
        "📝 **ডাটা যোগ করুন (11 কলাম):**\n"
        "`ADVENT,Impulse (Up),Wave 5 of 3,13.8-14.2,13.2,15.0,16.0,17.5,1:2.5,68,মূল্য 13.0 টাকার নিচে ব্রেক করতে পারেনি...`\n\n"
        "📚 **বেসিক কমান্ড:**\n"
        "`/help` - সব কমান্ড দেখুন\n"
        "`/list` - আজকের ডাটা দেখুন (ওয়েব + সাব-ওয়েব সহ)\n"
        "`/portfolio` - পোর্টফোলিও অ্যানালাইসিস (ইনলাইন বাটন সহ)\n"
        "`/trademenu` - ট্রেডিং অ্যানালাইটিক্স (ইনলাইন বাটন সহ)\n"
        "`/insight [সিম্বল] [তারিখ]` - সম্পূর্ণ ইনসাইট দেখুন\n"
        "`/files` - সব CSV ফাইলের তালিকা\n"
        "`/view [তারিখ] [পৃষ্ঠা]` - কার্ড স্টাইলে ফাইল দেখুন (ওয়েব + সাব-ওয়েব সহ)\n"
        "`/wavesummary [তারিখ]` - ওয়েভ এবং সাব-ওয়েব সারাংশ\n"
        "`/symbols [তারিখ]` - ফাইলের সিম্বল দেখুন\n"
        "`/search [সিম্বল]` - সব ফাইলে সিম্বল খুঁজুন\n"
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
        "🌊 **ওয়েভ ইমোজি বুঝতে সাহায্য:**\n"
        "⚡ = ইম্পালস ওয়েভ | 🌀 = করেকটিভ ওয়েভ\n"
        "📈 = আপট্রেন্ড সাব-ওয়েব | 📉 = ডাউনট্রেন্ড সাব-ওয়েব | 🔄 = করেকটিভ সাব-ওয়েব\n\n"
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
🌊 **ওয়েভ ভিজুয়ালাইজেশন**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/view 29-03-2026` - এলিয়ট ওয়েব + সাব-ওয়েব সহ দেখাবে
• `/wavesummary 29-03-2026` - ওয়েভ এবং সাব-ওয়েব সারাংশ
• `/list` - আজকের ডাটা ওয়েব + সাব-ওয়েব সহ দেখাবে

**ওয়েভ ইমোজি বুঝতে সাহায্য:**
⚡ = ইম্পালস ওয়েভ (আপট্রেন্ড)
🌀 = করেকটিভ ওয়েভ (ডাউনট্রেন্ড/কনসলিডেশন)
📈 = আপট্রেন্ড সাব-ওয়েব (ওয়েভ 1,3,5)
📉 = ডাউনট্রেন্ড সাব-ওয়েব (ওয়েভ 2,4)
🔄 = করেকটিভ সাব-ওয়েব (ওয়েভ A,B,C)

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
• `/files` - সব CSV ফাইলের তালিকা
• `/view 25-03-2026` - প্রথম পৃষ্ঠা দেখাবে (ওয়েব+সাব-ওয়েব সহ)
• `/view 25-03-2026 2` - দ্বিতীয় পৃষ্ঠা দেখাবে
• `/deletefile 25-03-2026` - ফাইল ডিলিট

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **সিম্বল ম্যানেজমেন্ট**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• `/symbols 25-03-2026` - সিম্বল লিস্ট
• `/deletesymbol 25-03-2026 ADVENT` - সিম্বল ডিলিট
• `/search ADVENT` - সব ফাইলে খুঁজুন

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

# Keep all other existing handlers (insight_command, handle_message, clear_command, 
# yesclear_command, files_command, symbols_command, deletesymbol_command,
# search_command, status_command, cancel_command, reload_command, portfolio_command,
# and all callback handlers, etc.) - they remain unchanged

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
        application.add_handler(CommandHandler("view", view_command))  # UPDATED
        application.add_handler(CommandHandler("wavesummary", wavesummary_command))  # NEW
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

        print("🤖 Telegram Bot starting with Wave + Subwave display...")
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