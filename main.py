import os
import csv
import json
import threading
import asyncio
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
        
        # Use /tmp for Render (temporary storage)
        self.base_path = "/tmp"
        self.stock_folder = os.path.join(self.base_path, "stock")
        
        # Load existing data
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stock_data = data.get('stock_data', [])
                    print(f"✅ Loaded {len(self.stock_data)} records")
            else:
                self.stock_data = []
                print("ℹ️ No existing data file found. Starting fresh.")
        except Exception as e:
            print(f"⚠️ Error loading data: {e}")
            self.stock_data = []
    
    def save_data_to_json(self):
        """Save data to JSON file"""
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
            print(f"❌ Error saving to JSON: {e}")
            return False
    
    def ensure_directory(self):
        """Create stock directory if it doesn't exist"""
        if not os.path.exists(self.stock_folder):
            os.makedirs(self.stock_folder)
            print(f"✅ Created directory: {self.stock_folder}")
    
    def save_to_csv(self):
        """Save stock data to CSV file"""
        self.ensure_directory()
        
        if not self.stock_data:
            return "⚠️ No data available to save. Please add data first using /add command."
        
        current_date = datetime.now().strftime("%d-%m-%Y")
        filename = os.path.join(self.stock_folder, f"{current_date}.csv")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(self.headers)
                writer.writerows(self.stock_data)
            
            self.save_data_to_json()
            return f"✅ Data saved successfully to:\n{filename}\n📊 Total records: {len(self.stock_data)}"
        except Exception as e:
            return f"❌ Error saving file: {str(e)}"
    
    def add_stock_data(self, row_data):
        """Add new stock data"""
        if len(row_data) != len(self.headers):
            return f"❌ Invalid data. Expected {len(self.headers)} columns, got {len(row_data)}"
        
        self.stock_data.append(row_data)
        self.save_data_to_json()
        return f"✅ Stock data added successfully. Total records: {len(self.stock_data)}"
    
    def delete_stock_data(self, index):
        """Delete stock data by index"""
        if index < 0 or index >= len(self.stock_data):
            return "❌ Invalid index"
        
        deleted = self.stock_data.pop(index)
        self.save_data_to_json()
        return f"✅ Deleted: {deleted[0]}"
    
    def clear_all_data(self):
        """Clear all data"""
        count = len(self.stock_data)
        self.stock_data = []
        self.save_data_to_json()
        return f"✅ Cleared all {count} records"
    
    def get_data_preview(self):
        """Get preview of current data"""
        if not self.stock_data:
            return "No data available"
        
        preview = f"📊 Current Data ({len(self.stock_data)} records):\n\n"
        
        for i, row in enumerate(self.stock_data[:5]):
            preview += f"{i+1}. {row[0]} - {row[1]} - {row[-1]}\n"
        
        if len(self.stock_data) > 5:
            preview += f"\n... and {len(self.stock_data) - 5} more records"
        
        return preview

# Global bot instance
bot_instance = StockDataBot()

# Telegram bot handlers (async for new version)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to Stock Data Bot!\n\n"
        "Commands:\n"
        "/save - Save to CSV\n"
        "/add symbol|wave|subwave|entry|stop|tp1|tp2|rrr|score|conf|action\n"
        "/delete index\n"
        "/list - Show data\n"
        "/clear - Clear all\n"
        "/status - Check status\n"
        "/help - Detailed help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 **Help Guide**

**Add Data:**
/add BDCOM|Impulse (Wave 4)|Sub-wave C|25.80-26.30|24.90|27.50|29.00|1:1.8|72|High|Accumulate

**Delete:**
/delete 0

**Data Format (11 columns):**
1. Symbol
2. Elliott Wave
3. Sub-wave
4. Entry Zone
5. Stop Loss
6. Take Profit 1
7. Take Profit 2
8. Risk-Reward Ratio
9. Score (0-100)
10. Confidence Level
11. Action Recommendation
"""
    await update.message.reply_text(help_text)

async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💾 Saving...")
    result = bot_instance.save_to_csv()
    await update.message.reply_text(result)

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: /add symbol|wave|subwave|entry|stop|tp1|tp2|rrr|score|confidence|action\n"
            "Example: /add BDCOM|Impulse (Wave 4)|Sub-wave C|25.80-26.30|24.90|27.50|29.00|1:1.8|72|High|Accumulate"
        )
        return
    
    data_str = ' '.join(context.args)
    row_data = [item.strip() for item in data_str.split('|')]
    result = bot_instance.add_stock_data(row_data)
    await update.message.reply_text(result)

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delete index")
        return
    
    try:
        index = int(context.args[0])
        result = bot_instance.delete_stock_data(index)
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("Invalid index")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    preview = bot_instance.get_data_preview()
    await update.message.reply_text(preview)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = bot_instance.clear_all_data()
    await update.message.reply_text(result)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = f"/tmp/stock/{current_date}.csv"
    
    status_text = f"""
📊 **Status**
Records: {len(bot_instance.stock_data)}
Date: {current_date}
File: {filename}
"""
    if os.path.exists(filename):
        size = os.path.getsize(filename)
        status_text += f"✅ File exists ({size} bytes)"
    else:
        status_text += "⏳ No file saved yet"
    
    await update.message.reply_text(status_text)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /start for commands")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    print(f"Update {update} caused error {context.error}")

def run_telegram_bot():
    """Run Telegram bot"""
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("save", save_command))
        application.add_handler(CommandHandler("add", add_command))
        application.add_handler(CommandHandler("delete", delete_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        application.add_error_handler(error_handler)
        
        print("🤖 Telegram Bot is starting...")
        # Start polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

# Flask routes for uptime monitoring
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
        "file_exists": file_exists,
        "file_path": filename if file_exists else None
    })

def main():
    """Main function to run both Flask and Telegram bot"""
    # Start Telegram bot in a separate thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 10000))
    
    # Run Flask app
    print(f"🌐 Flask server starting on port {port}...")
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()