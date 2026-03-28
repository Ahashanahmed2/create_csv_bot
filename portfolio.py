# portfolio.py - পোর্টফোলিও অ্যানালাইটিক্স মডিউল (ইনলাইন বাটন সহ)

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import re

class PortfolioAnalyzer:
    """পোর্টফোলিও অ্যানালাইসিস ম্যানেজার"""

    def __init__(self, hf_manager, bot_instance):
        self.hf_manager = hf_manager
        self.bot = bot_instance

    def parse_rrr(self, rrr_str):
        """RRR স্ট্রিং থেকে সংখ্যাসূচক মান বের করুন"""
        try:
            if ':' in rrr_str:
                parts = rrr_str.split(':')
                if len(parts) == 2:
                    risk = float(parts[0])
                    reward = float(parts[1])
                    return reward / risk if risk > 0 else 0
            return 0
        except:
            return 0

    def get_wave_type(self, wave_text):
        """ওয়েভ টাইপ নির্ধারণ করুন (ইম্পালস বা করেকটিভ)"""
        wave_lower = wave_text.lower()
        if 'impulse' in wave_lower or 'ইম্পালস' in wave_lower:
            return 'impulse'
        elif 'corrective' in wave_lower or 'করেকটিভ' in wave_lower:
            return 'corrective'
        else:
            return 'impulse'

    def categorize_by_score(self, score_str):
        """স্কোর অনুযায়ী ক্যাটাগরি নির্ধারণ"""
        try:
            score = int(score_str)
            if score >= 80:
                return "very_strong"
            elif score >= 60:
                return "good"
            elif score >= 40:
                return "medium"
            else:
                return "weak"
        except:
            return "medium"

    def get_score_emoji(self, score):
        """স্কোর অনুযায়ী ইমোজি"""
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

    def analyze_portfolio(self, data):
        """পোর্টফোলিও ডাটা অ্যানালাইসিস করুন"""
        if not data:
            return None

        stats = {
            'total': len(data),
            'very_strong': {'count': 0, 'symbols': [], 'scores': []},
            'good': {'count': 0, 'symbols': [], 'scores': []},
            'medium': {'count': 0, 'symbols': [], 'scores': []},
            'weak': {'count': 0, 'symbols': [], 'scores': []},
            'impulse': {'count': 0, 'symbols': []},
            'corrective': {'count': 0, 'symbols': []},
            'best_rrr': {'value': 0, 'symbol': '', 'rrr': ''},
            'highest_score': {'value': 0, 'symbol': '', 'score': ''},
            'top_recommendations': [],
            'avoid_symbols': []
        }

        for row in data:
            if not row or len(row) < 10:
                continue

            symbol = row[0]
            score_str = row[9] if len(row) > 9 else "0"
            rrr_str = row[8] if len(row) > 8 else "1:0"
            wave_text = row[1] if len(row) > 1 else ""

            # স্কোর অনুযায়ী ক্যাটাগরি
            category = self.categorize_by_score(score_str)
            try:
                score_val = int(score_str)
            except:
                score_val = 0

            if category == "very_strong":
                stats['very_strong']['count'] += 1
                stats['very_strong']['symbols'].append(symbol)
                stats['very_strong']['scores'].append(score_val)
            elif category == "good":
                stats['good']['count'] += 1
                stats['good']['symbols'].append(symbol)
                stats['good']['scores'].append(score_val)
            elif category == "medium":
                stats['medium']['count'] += 1
                stats['medium']['symbols'].append(symbol)
                stats['medium']['scores'].append(score_val)
            else:
                stats['weak']['count'] += 1
                stats['weak']['symbols'].append(symbol)
                stats['weak']['scores'].append(score_val)

            # ওয়েভ টাইপ
            wave_type = self.get_wave_type(wave_text)
            if wave_type == 'impulse':
                stats['impulse']['count'] += 1
                stats['impulse']['symbols'].append(symbol)
            else:
                stats['corrective']['count'] += 1
                stats['corrective']['symbols'].append(symbol)

            # সেরা RRR
            rrr_value = self.parse_rrr(rrr_str)
            if rrr_value > stats['best_rrr']['value']:
                stats['best_rrr']['value'] = rrr_value
                stats['best_rrr']['symbol'] = symbol
                stats['best_rrr']['rrr'] = rrr_str

            # সর্বোচ্চ স্কোর
            if score_val > stats['highest_score']['value']:
                stats['highest_score']['value'] = score_val
                stats['highest_score']['symbol'] = symbol
                stats['highest_score']['score'] = score_str

        # টপ রিকমেন্ডেশন (স্কোর 80+ এবং RRR ভালো)
        for i, sym in enumerate(stats['very_strong']['symbols'][:5]):
            stats['top_recommendations'].append(sym)

        # এড়িয়ে চলুন (স্কোর 50 এর নিচে)
        for sym in stats['weak']['symbols']:
            stats['avoid_symbols'].append(sym)

        return stats

    def format_portfolio_report_with_buttons(self, stats, date):
        """পোর্টফোলিও রিপোর্ট ইনলাইন বাটন সহ"""
        if not stats:
            return "❌ পোর্টফোলিও ডাটা পাওয়া যায়নি।", None

        very_strong_pct = (stats['very_strong']['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        good_pct = (stats['good']['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        medium_pct = (stats['medium']['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        weak_pct = (stats['weak']['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        impulse_pct = (stats['impulse']['count'] / stats['total'] * 100) if stats['total'] > 0 else 0
        corrective_pct = (stats['corrective']['count'] / stats['total'] * 100) if stats['total'] > 0 else 0

        report = f"📊 **পোর্টফোলিও রিপোর্ট - {date}**\n\n"
        report += "```\n"
        report += "┌─────────────────────────────────────────────────────────────────────────────┐\n"
        report += "│ 📈 মার্কেট সামারি                                                          │\n"
        report += "├─────────────────────────────────────────────────────────────────────────────┤\n"
        report += f"│ 📊 মোট স্টক      : {stats['total']} টি                                        │\n"
        report += f"│ 🔥 খুব শক্তিশালী (80+) : {stats['very_strong']['count']} টি ({very_strong_pct:.0f}%)     │\n"
        report += f"│ ✅ ভাল (60-79)     : {stats['good']['count']} টি ({good_pct:.0f}%)          │\n"
        report += f"│ ⚠️ মধ্যম (40-59)   : {stats['medium']['count']} টি ({medium_pct:.0f}%)        │\n"
        report += f"│ ❌ দুর্বল (<40)    : {stats['weak']['count']} টি ({weak_pct:.0f}%)           │\n"
        report += "├─────────────────────────────────────────────────────────────────────────────┤\n"
        report += f"│ 🎯 সেরা RRR       : {stats['best_rrr']['rrr']} ({stats['best_rrr']['symbol']})    │\n"
        report += f"│ 💎 সর্বোচ্চ স্কোর  : {stats['highest_score']['score']} ({stats['highest_score']['symbol']})         │\n"
        report += f"│ 📈 ইম্পালস ওয়েভ   : {stats['impulse']['count']} টি ({impulse_pct:.0f}%)               │\n"
        report += f"│ 🔄 করেকটিভ ওয়েভ   : {stats['corrective']['count']} টি ({corrective_pct:.0f}%)            │\n"
        report += "└─────────────────────────────────────────────────────────────────────────────┘\n"
        report += "```\n\n"

        if stats['top_recommendations']:
            top_rec = ", ".join(stats['top_recommendations'][:3])
            report += f"💡 **টপ রিকমেন্ডেশন:** {top_rec}\n"

        if stats['avoid_symbols']:
            avoid_list = [sym for sym in stats['avoid_symbols'][:3]]
            if len(stats['avoid_symbols']) > 3:
                avoid_list.append("...")
            avoid_text = ", ".join(avoid_list)
            report += f"⚠️ **এড়িয়ে চলুন:** {avoid_text} (স্কোর <50)\n"

        report += "\n🔽 **নিচের বাটনে ক্লিক করে বিস্তারিত দেখুন**"

        keyboard = [
            [
                InlineKeyboardButton(f"🔥 খুব শক্তিশালী ({stats['very_strong']['count']})", callback_data=f"vs_{date}_1"),
                InlineKeyboardButton(f"✅ ভাল ({stats['good']['count']})", callback_data=f"vg_{date}_1")
            ],
            [
                InlineKeyboardButton(f"⚠️ মধ্যম ({stats['medium']['count']})", callback_data=f"vm_{date}_1"),
                InlineKeyboardButton(f"❌ দুর্বল ({stats['weak']['count']})", callback_data=f"vw_{date}_1")
            ],
            [
                InlineKeyboardButton(f"📈 ইম্পালস ওয়েভ ({stats['impulse']['count']})", callback_data=f"iw_{date}_1"),
                InlineKeyboardButton(f"🔄 করেকটিভ ওয়েভ ({stats['corrective']['count']})", callback_data=f"cw_{date}_1")
            ],
            [
                InlineKeyboardButton("🏆 সেরা RRR", callback_data=f"brrr_{date}"),
                InlineKeyboardButton("💎 সর্বোচ্চ স্কোর", callback_data=f"hscore_{date}")
            ],
            [
                InlineKeyboardButton("💡 টপ রিকমেন্ডেশন", callback_data=f"trec_{date}"),
                InlineKeyboardButton("⚠️ এড়িয়ে চলুন", callback_data=f"avoid_{date}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        return report, reply_markup

    def format_symbols_with_buttons(self, symbols_with_scores, title, date, category, page, total_pages, items_per_page=10):
        """সিম্বল লিস্ট ইনলাইন বাটন সহ"""
        if not symbols_with_scores:
            return f"📭 {title} - কোনো সিম্বল নেই।", None

        total = len(symbols_with_scores)
        start = (page - 1) * items_per_page
        end = min(start + items_per_page, total)
        page_data = symbols_with_scores[start:end]

        result = f"📊 **{title}**  |  📋 {total} টি সিম্বল  |  📄 পৃষ্ঠা {page}/{total_pages}\n\n"
        result += "```\n"
        result += f"{'ক্রম':<6} {'সিম্বল':<15} {'স্কোর':<10} {'রেটিং'}\n"
        result += "-" * 45 + "\n"

        for i, (symbol, score) in enumerate(page_data):
            serial = start + i + 1
            emoji = self.get_score_emoji(score) if score != "-" else "📊"
            if score != "-":
                try:
                    s = int(score)
                    if s >= 80:
                        rating = "খুব শক্তিশালী"
                    elif s >= 60:
                        rating = "ভাল"
                    elif s >= 40:
                        rating = "মধ্যম"
                    else:
                        rating = "দুর্বল"
                except:
                    rating = "অজানা"
            else:
                rating = "ওয়েভ টাইপ"

            if score != "-":
                result += f"{serial:<6} {symbol:<15} {score}/100 {emoji:<5} {rating}\n"
            else:
                result += f"{serial:<6} {symbol:<15} {'':<10} {emoji:<5} {rating}\n"

        result += "```\n\n"

        keyboard = []
        
        # সিম্বল বাটন (প্রতি লাইনে ৩টি)
        row = []
        for symbol, score in page_data[:9]:  # সর্বোচ্চ ৯টি সিম্বল
            button = InlineKeyboardButton(symbol, callback_data=f"sym_{date}_{symbol}")
            row.append(button)
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        # পেজিনেশন বাটন
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("◀️ আগের", callback_data=f"{category}_{date}_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("পরবর্তী ▶️", callback_data=f"{category}_{date}_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # ব্যাক বাটন
        keyboard.append([InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return result, reply_markup

    def format_symbol_detail_with_buttons(self, symbol_data, date):
        """একক সিম্বলের বিস্তারিত তথ্য বাটন সহ"""
        result = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ #{symbol_data['rank']} {symbol_data['symbol']} {symbol_data['status_icon']}
╠══════════════════════════════════════════════════════════════════════════════╣
║ 🌊 ওয়েভ    : {symbol_data['wave_type']} → {symbol_data['wave_detail']}
║ 📈 এন্ট্রি  : {symbol_data['entry']}  |  🛑 স্টপ: {symbol_data['stop_loss']}
║ 🎯 টার্গেট  : {symbol_data['targets']}  |  📊 RRR: {symbol_data['rrr']}
║ 🏆 স্কোর    : {symbol_data['score']} {symbol_data['score_icon']}  |  {symbol_data['rating']}
║ 💡 ইনসাইট  : {symbol_data['insight']}
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        keyboard = [
            [InlineKeyboardButton("📊 পোর্টফোলিও রিপোর্ট", callback_data=f"report_{date}")],
            [InlineKeyboardButton("🔙 আগের পৃষ্ঠায় ফিরুন", callback_data=f"back_{date}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return result, reply_markup

    def get_symbol_detail(self, date, symbol, all_data):
        """সিম্বলের বিস্তারিত তথ্য সংগ্রহ করুন"""
        for idx, row in enumerate(all_data):
            if row[0] == symbol:
                score_str = row[9] if len(row) > 9 else "0"
                score_val = int(score_str) if score_str.isdigit() else 0
                
                return {
                    'rank': idx + 1,
                    'symbol': symbol,
                    'status_icon': self.get_score_emoji(score_str),
                    'wave_type': row[1] if len(row) > 1 else "-",
                    'wave_detail': row[2] if len(row) > 2 else "-",
                    'entry': row[3] if len(row) > 3 else "-",
                    'stop_loss': row[4] if len(row) > 4 else "-",
                    'targets': row[5] if len(row) > 5 else "-",
                    'rrr': row[8] if len(row) > 8 else "-",
                    'score': score_str,
                    'score_icon': self.get_score_emoji(score_str),
                    'rating': "খুব শক্তিশালী" if score_val >= 80 else "ভাল" if score_val >= 60 else "মধ্যম" if score_val >= 40 else "দুর্বল",
                    'insight': row[10] if len(row) > 10 else "তথ্য নেই"
                }
        return None

# ==================== টেলিগ্রাম হ্যান্ডলার ====================

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """/portfolio কমান্ড হ্যান্ডলার (ইনলাইন বাটন সহ)"""
    args = context.args

    if args:
        date_input = args[0]
        date = bot.fix_date_format(date_input) if hasattr(bot, 'fix_date_format') else date_input
    else:
        if bot.current_data:
            date = bot.current_date
        else:
            files = portfolio_analyzer.hf_manager.get_all_csv_files()
            if files:
                date = files[0]
            else:
                await update.message.reply_text("❌ কোনো CSV ফাইল নেই।")
                return

    status_msg = await update.message.reply_text(f"⏳ পোর্টফোলিও অ্যানালাইসিস করা হচ্ছে ({date})...")

    data = portfolio_analyzer.hf_manager.read_csv_file(date)

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

async def category_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """ক্যাটাগরি বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    
    category = parts[0]
    date = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 1
    
    # ডাটা লোড করুন
    csv_data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
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
    
    # ক্যাটাগরি অনুযায়ী ডাটা তৈরি
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
    if page > total_pages:
        page = total_pages
    
    result, reply_markup = portfolio_analyzer.format_symbols_with_buttons(
        symbols_with_scores, title, date, category, page, total_pages
    )
    
    await query.edit_message_text(result, parse_mode='Markdown', reply_markup=reply_markup)

async def symbol_detail_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """সিম্বল ডিটেইল বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    
    if parts[0] == "sym":
        date = parts[1]
        symbol = parts[2]
        
        # ডাটা লোড করুন
        csv_data = portfolio_analyzer.hf_manager.read_csv_file(date)
        
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

async def report_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """রিপোর্ট ব্যাক বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    
    if parts[0] == "report":
        date = parts[1]
        
        csv_data = portfolio_analyzer.hf_manager.read_csv_file(date)
        
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

async def back_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot, last_category=None, last_date=None, last_page=1):
    """ব্যাক বাটনের কলব্যাক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    
    # কন্টেক্সট থেকে শেষ ক্যাটাগরি এবং পৃষ্ঠা নিন
    last_data = context.user_data.get('last_view', {})
    category = last_data.get('category', 'vs')
    date = last_data.get('date', '')
    page = last_data.get('page', 1)
    
    if date:
        # আগের ক্যাটাগরি পৃষ্ঠায় ফিরুন
        csv_data = portfolio_analyzer.hf_manager.read_csv_file(date)
        
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
                else:
                    symbols_with_scores = list(zip(stats['very_strong']['symbols'], stats['very_strong']['scores']))
                    title = "🔥 খুব শক্তিশালী সিম্বল (স্কোর 80+)"
                
                total_pages = (len(symbols_with_scores) + 9) // 10
                result, reply_markup = portfolio_analyzer.format_symbols_with_buttons(
                    symbols_with_scores, title, date, category, page, total_pages
                )
                await query.edit_message_text(result, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ ডাটা লোড করতে ব্যর্থ হয়েছে।")
        else:
            await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
    else:
        # ডিফল্ট রিপোর্ট
        await report_callback_handler(update, context, portfolio_analyzer, bot)

async def special_command_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot, command_type):
    """বিশেষ কমান্ডের কলব্যাক হ্যান্ডলার (brrr, hscore, trec, avoid)"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    parts = data.split('_')
    date = parts[1] if len(parts) > 1 else None
    
    if not date:
        await query.edit_message_text("❌ তারিখ পাওয়া যায়নি।")
        return
    
    csv_data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
    if csv_data is None:
        await query.edit_message_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if csv_data and csv_data[0] and len(csv_data[0]) > 0 and csv_data[0][0] == "symbol":
        start_idx = 1
    
    all_data = csv_data[start_idx:]
    
    if command_type == "brrr":
        # সেরা RRR দেখান
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
            emoji = portfolio_analyzer.get_score_emoji(best_rrr['score'])
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
        # সর্বোচ্চ স্কোর দেখান
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
            emoji = portfolio_analyzer.get_score_emoji(highest['score'])
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
        # টপ রিকমেন্ডেশন
        stats = portfolio_analyzer.analyze_portfolio(all_data)
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
                emoji = portfolio_analyzer.get_score_emoji(score)
                result += f"{i+1:<6} {sym:<15} {score}/100 {emoji:<5} {rrr}\n"
            result += "```"
            keyboard = [[InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")]]
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(f"📭 {date} তারিখে কোনো টপ রিকমেন্ডেশন নেই।")
    
    elif command_type == "avoid":
        # এড়িয়ে চলুন
        stats = portfolio_analyzer.analyze_portfolio(all_data)
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
                emoji = portfolio_analyzer.get_score_emoji(score)
                result += f"{i+1:<6} {sym:<15} {score}/100 {emoji:<5} খুব দুর্বল\n"
            result += "```"
            keyboard = [[InlineKeyboardButton("🔙 পোর্টফোলিওতে ফিরুন", callback_data=f"report_{date}")]]
            await query.edit_message_text(result, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(f"📭 {date} তারিখে কোনো দুর্বল সিম্বল নেই।")