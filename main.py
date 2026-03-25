import os
import csv
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import platform

class StockDataBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.data_file = "stock_data.json"
        self.stock_data = []
        self.headers = ["symbol", "এলিয়ট ওয়েব (বর্তমান অবস্থান)", "সাব-ওয়েব (বর্তমান অবস্থান)", 
                       "এন্ট্রি জোন (টাকা)", "স্টপ লস (টাকা)", "টেক প্রফিট ১ (টাকা)", 
                       "টেক প্রফিট ২ (টাকা)", "রিস্ক-রিওয়ার্ড অনুপাত (RRR)", 
                       "স্কোর (১০০ এর মধ্যে)", "কনফিডেন্স লেভেল", "অ্যাকশন রিকমেন্ডেশন"]
        
        # Detect mobile storage path
        self.base_path = self.get_base_path()
        self.stock_folder = os.path.join(self.base_path, "stock")
        
        self.load_data()
    
    def get_base_path(self):
        """Detect the appropriate base path for the device"""
        # Android (Termux)
        if os.path.exists("/storage/emulated/0"):
            return "/storage/emulated/0"
        elif os.path.exists("/sdcard"):
            return "/sdcard"
        
        # iOS (Pythonista/Pyto)
        elif platform.system() == "iOS":
            import appex
            try:
                return os.path.expanduser("~/Documents")
            except:
                return os.getcwd()
        
        # Windows/Mac/Linux (for testing)
        elif platform.system() == "Windows":
            return os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        elif platform.system() == "Darwin":  # macOS
            return os.path.join(os.path.expanduser("~"), "Desktop")
        else:  # Linux and others
            return os.getcwd()
    
    def ensure_directory(self):
        """Create stock directory if it doesn't exist"""
        if not os.path.exists(self.stock_folder):
            os.makedirs(self.stock_folder)
            print(f"✅ Created directory: {self.stock_folder}")
    
    def save_to_csv(self):
        """Save stock data to CSV file"""
        self.ensure_directory()
        
        if not self.stock_data:
            return "⚠️ No data available to save. Please add data first using /add_data command."
        
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
    
    def get_storage_info(self):
        """Get storage information"""
        self.ensure_directory()
        
        info = f"📁 **Storage Information**\n\n"
        info += f"📍 Base Path: {self.base_path}\n"
        info += f"📂 Stock Folder: {self.stock_folder}\n"
        
        if os.path.exists(self.stock_folder):
            info += f"✅ Folder exists\n"
            
            # Get folder size and file count
            files = os.listdir(self.stock_folder)
            csv_files = [f for f in files if f.endswith('.csv')]
            info += f"📄 CSV Files: {len(csv_files)}\n"
            
            # Show today's file if exists
            current_date = datetime.now().strftime("%d-%m-%Y")
            today_file = os.path.join(self.stock_folder, f"{current_date}.csv")
            if os.path.exists(today_file):
                size = os.path.getsize(today_file)
                info += f"✅ Today's file exists: {size} bytes\n"
        
        return info

# Global bot instance
bot_instance = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with storage info"""
    storage_info = bot_instance.get_storage_info()
    await update.message.reply_text(
        f"🤖 Welcome to Dynamic Stock Data Bot!\n\n"
        f"{storage_info}\n\n"
        f"**Available Commands:**\n"
        f"/save - Save current data to CSV\n"
        f"/add - Add new stock data\n"
        f"/update - Update existing stock data\n"
        f"/delete - Delete stock data\n"
        f"/list - Show current data\n"
        f"/clear - Clear all data\n"
        f"/status - Check status\n"
        f"/storage - Show storage location\n"
        f"/help - Show this help",
        parse_mode='Markdown'
    )

async def storage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show storage information"""
    storage_info = bot_instance.get_storage_info()
    await update.message.reply_text(storage_info, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check status with file location"""
    current_date = datetime.now().strftime("%d-%m-%Y")
    filename = os.path.join(bot_instance.stock_folder, f"{current_date}.csv")
    
    status_text = f"""
📊 **Bot Status**

**Date:** {current_date}
**Records:** {len(bot_instance.stock_data)}
**Headers:** {len(bot_instance.headers)} columns

**File Location:**
📍 Folder: `{bot_instance.stock_folder}`
📄 File: `{current_date}.csv`

**File Status:**
"""
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        status_text += f"✅ CSV File exists\n📦 Size: {file_size} bytes\n🔗 Full path: `{filename}`"
    else:
        status_text += f"⏳ No CSV file saved yet for today\n💾 Will be saved to: `{filename}`"
    
    if os.path.exists(bot_instance.data_file):
        status_text += f"\n💾 JSON Data file: `{bot_instance.data_file}`"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

# [Previous add_command, update_command, delete_command, list_command, clear_command functions remain same]
# Add them here as before...

def main():
    """Start the bot"""
    BOT_TOKEN = "YOUR_BOT_TOKEN"  # Replace with your token
    
    global bot_instance
    bot_instance = StockDataBot(BOT_TOKEN)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("save", save_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("storage", storage_command))  # New command
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("🤖 Dynamic Stock Data Bot is starting...")
    print(f"📁 Files will be saved to: {bot_instance.stock_folder}")
    print(f"💾 Persistent storage: {bot_instance.data_file}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
