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
        """Add multiple stock data at once from CSV format text"""
        lines = csv_text.strip().split('\n')
        added = 0
        errors = []
        
        for i, line in enumerate(lines):
            if i == 0:  # Skip header line
                continue
            if not line.strip():
                continue
            
            row_data = [item.strip() for item in line.split(',')]
            
            # Handle Bengali text properly
            if len(row_data) != len(self.headers):
                errors.append(f"লাইন {i+1}: {len(row_data)} টি কলাম (প্রয়োজন {len(self.headers)})")
                continue
            
            # Check if symbol already exists
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

# Global bot instance
bot_instance = StockDataBot()

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **স্টক ডাটা বট**\n\n"
        "**কমান্ড:**\n"
        "/bulk - একসাথে সব ডাটা যোগ করুন\n"
        "/add - একটি ডাটা যোগ করুন\n"
        "/list - সব ডাটা দেখুন\n"
        "/save - CSV ফাইলে সেভ করুন\n"
        "/delete [নম্বর] - ডাটা ডিলিট\n"
        "/clear - সব ডাটা মুছুন\n"
        "/status - স্ট্যাটাস দেখুন\n"
        "/help - সাহায্য\n\n"
        "**একসাথে ডাটা যোগ করতে:**\n"
        "/bulk কমান্ডের পর আপনার CSV ফরম্যাটে ডাটা পেস্ট করুন।",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **সাহায্য গাইড**

**একসাথে ডাটা যোগ করুন:**