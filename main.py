import os
import csv
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
                    print(f"✅ Loaded {len(self.stock_data)} records from {self.data_file}")
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
            print(f"✅ Data saved to {self.data_file}")
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
        return f"✅ Deleted: {deleted[0]} (Symbol: {deleted[0]})"
    
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
        
        for i, row in enumerate(self.stock_data[:5]):  # Show first 5 records
            preview += f"{i+1}. {row[0]} - {row[1]} - {row[-1]}\n"
        
        if len(self.stock_data) > 5:
            preview += f"\n... and {len(self.stock_data) - 5} more records"
        
        return preview
    
    def get_storage_info(self):
        """Get storage information"""
        self.ensure_directory()
        
        info = f"📁 Storage Information\n\n"
        info += f"Base Path: {self.base_path}\n"
        info += f"Stock Folder: {self.stock_folder}\n"
        
        if os.path.exists(self.stock_folder):
            files = os.listdir(self.stock_folder)
            csv_files = [f for f in files if f.endswith('.csv')]
            info += f"CSV Files: {len(csv_files)}\n"
            
            # Show today's file if exists
            current_date = datetime.now().strftime("%d-%m-%Y")
            today_file = os.path.join(self.stock_folder, f"{current_date}.csv")
            if os.path.exists(today_file):
                size = os.path.getsize(today_file)
                info += f"Today's file exists: {size} bytes"
        
        return info

# Global bot instance
bot_instance = StockDataBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "🤖 Welcome to Stock Data Bot!\n\n"
        "Available Commands:\n"
        "/save - Save current data to CSV\n"
        "/add - Add new stock data\n"
        "/delete - Delete stock data\n"
        "/list - Show current data\n"
        "/clear - Clear all data\n"
        "/status - Check status\n"
        "/storage - Show storage location\n"
        "/help - Show detailed help\n\n"
        "To add data, use: /add symbol|wave|subwave|entry|stop|tp1|tp2|rrr|score|confidence|action"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📚 **Help Guide**

**How to add data:**
Use pipe (|) separator:
`/add BDCOM|Impulse (Wave 4)|Sub-wave C|25.80-26.30|24.90|27.50|29.00|1:1.8|72|High|Accumulate`

**How to delete:**
`/delete 0` (deletes record at index 0)

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
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save data to CSV"""
    await update.message.reply_text("💾 Saving stock data...")
    result = bot_instance.save_to_csv()
    await update.message.reply_text(result)

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new stock data"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide data in this format:\n"
            "/add symbol|wave|subwave|entry|stop|tp1|tp2|rrr|score|confidence|action\n\n"
            "Example:\n"
            "/add BDCOM|Impulse (Wave 4)|Sub-wave C|25.80-26.30|24.90|27.50|29.00|1:1.8|72|High|Accumulate"
        )
        return
    
    # Join all args and split by pipe
    data_str = ' '.join(context.args)
    row_data = [item.strip() for item in data_str.split('|')]
    
    result = bot_instance.add_stock_data(row_data)
    await update.message.reply_text(result)

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete stock data by index"""
    if not context.args:
        await update.message.reply_text("❌ Please provide index to delete\nExample: /delete 0")
        return
    
    try:
        index = int(context.args[0])
        result = bot_instance.delete_stock_data(index)
        await update.message.reply_text(result)
    except ValueError:
        await update.message.reply_text("❌ Invalid index. Please provide a number.")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List current data"""
    preview = bot_instance.get_data_preview()
    await update.message.reply_text(preview)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all data"""
    result = bot_instance.clear_all_data()
    await update.message.reply_text(result)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check status"""
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = f"/tmp/stock/{current_date}.csv"
    
    status_text = f"""
📊 **Bot Status**

**Date:** {current_date}
**Records:** {len(bot_instance.stock_data)}
**Headers:** {len(bot_instance.headers)} columns

**File Location:**
📍 Folder: `/tmp/stock`
📄 File: `{current_date}.csv`

**File Status:**
"""
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        status_text += f"✅ CSV File exists\n📦 Size: {file_size} bytes"
    else:
        status_text += f"⏳ No CSV file saved yet for today"
    
    if os.path.exists(bot_instance.data_file):
        status_text += f"\n💾 JSON Data file exists"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def storage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show storage information"""
    storage_info = bot_instance.get_storage_info()
    await update.message.reply_text(storage_info)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages"""
    await update.message.reply_text(
        "Please use available commands: /start, /save, /add, /delete, /list, /clear, /status, /storage, /help"
    )

def main():
    """Start the bot"""
    # Get bot token from environment variable
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
        print("Please set it in Render dashboard: Environment Variables")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("save", save_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("storage", storage_command))
    
    # Message handler for non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Start the bot
    print("🤖 Stock Data Bot is starting on Render...")
    print(f"📁 Files will be saved to: /tmp/stock/")
    print("📝 Commands available: /start, /add, /delete, /list, /save, /clear, /status, /storage, /help")
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()