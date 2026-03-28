# portfolio.py - পোর্টফোলিও অ্যানালাইটিক্স মডিউল

from datetime import datetime
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
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
    
    def format_category_table(self, symbols_with_scores, title, page, total_pages, items_per_page=10):
        """ক্যাটাগরি অনুযায়ী সিম্বল লিস্ট ফরম্যাট করুন"""
        if not symbols_with_scores:
            return f"📭 **{title}** - কোনো সিম্বল নেই।"
        
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
            emoji = self.get_score_emoji(score)
            rating = ""
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
            
            result += f"{serial:<6} {symbol:<15} {score}/100 {emoji:<5} {rating}\n"
        
        result += "```"
        return result
    
    def format_portfolio_report(self, stats, date, page=1, category=None, category_page=1):
        """পোর্টফোলিও রিপোর্ট তৈরি করুন"""
        if not stats:
            return "❌ পোর্টফোলিও ডাটা পাওয়া যায়নি।"
        
        # যদি নির্দিষ্ট ক্যাটাগরি দেখাতে চায়
        if category:
            return self.show_category_symbols(stats, category, category_page)
        
        # পূর্ণ রিপোর্ট
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
        report += f"│ 📊 মোট স্টক      : {stats['total']} টি     /view {date}                        │\n"
        report += f"│ 🔥 খুব শক্তিশালী (80+) : {stats['very_strong']['count']} টি ({very_strong_pct:.0f}%)  /vs {date}     │\n"
        report += f"│ ✅ ভাল (60-79)     : {stats['good']['count']} টি ({good_pct:.0f}%)          /vg {date}        │\n"
        report += f"│ ⚠️ মধ্যম (40-59)   : {stats['medium']['count']} টি ({medium_pct:.0f}%)        /vm {date}        │\n"
        report += f"│ ❌ দুর্বল (<40)    : {stats['weak']['count']} টি ({weak_pct:.0f}%)           /vw {date}        │\n"
        report += "├─────────────────────────────────────────────────────────────────────────────┤\n"
        report += f"│ 🎯 সেরা RRR       : {stats['best_rrr']['rrr']} ({stats['best_rrr']['symbol']})    /brrr {date}     │\n"
        report += f"│ 💎 সর্বোচ্চ স্কোর  : {stats['highest_score']['score']} ({stats['highest_score']['symbol']})         /hscore {date}   │\n"
        report += f"│ 📈 ইম্পালস ওয়েভ   : {stats['impulse']['count']} টি ({impulse_pct:.0f}%)               /iw {date}        │\n"
        report += f"│ 🔄 করেকটিভ ওয়েভ   : {stats['corrective']['count']} টি ({corrective_pct:.0f}%)            /cw {date}        │\n"
        report += "└─────────────────────────────────────────────────────────────────────────────┘\n"
        report += "```\n\n"
        
        # টপ রিকমেন্ডেশন
        if stats['top_recommendations']:
            top_rec = ", ".join(stats['top_recommendations'][:3])
            report += f"💡 **টপ রিকমেন্ডেশন:** {top_rec}  /trec {date}\n"
        
        # এড়িয়ে চলুন
        if stats['avoid_symbols']:
            avoid_list = []
            for sym in stats['avoid_symbols'][:3]:
                avoid_list.append(sym)
            if len(stats['avoid_symbols']) > 3:
                avoid_list.append("...")
            avoid_text = ", ".join(avoid_list)
            report += f"⚠️ **এড়িয়ে চলুন:** {avoid_text} (স্কোর <50)  /avoid {date}\n"
        
        report += "\n"
        report += "📌 **কমান্ডসমূহ:**\n"
        report += "• `/vs [তারিখ] [পৃষ্ঠা]` - খুব শক্তিশালী সিম্বল দেখুন\n"
        report += "• `/vg [তারিখ] [পৃষ্ঠা]` - ভাল সিম্বল দেখুন\n"
        report += "• `/vm [তারিখ] [পৃষ্ঠা]` - মধ্যম সিম্বল দেখুন\n"
        report += "• `/vw [তারিখ] [পৃষ্ঠা]` - দুর্বল সিম্বল দেখুন\n"
        report += "• `/iw [তারিখ] [পৃষ্ঠা]` - ইম্পালস ওয়েভ সিম্বল দেখুন\n"
        report += "• `/cw [তারিখ] [পৃষ্ঠা]` - করেকটিভ ওয়েভ সিম্বল দেখুন\n"
        report += "• `/brrr [তারিখ]` - সেরা RRR দেখুন\n"
        report += "• `/hscore [তারিখ]` - সর্বোচ্চ স্কোর দেখুন\n"
        report += "• `/trec [তারিখ]` - টপ রিকমেন্ডেশন দেখুন\n"
        report += "• `/avoid [তারিখ]` - এড়িয়ে চলুন সিম্বল দেখুন"
        
        return report
    
    def show_category_symbols(self, stats, category, page=1, items_per_page=10):
        """নির্দিষ্ট ক্যাটাগরির সিম্বল দেখান"""
        if category == "very_strong":
            symbols_with_scores = list(zip(stats['very_strong']['symbols'], stats['very_strong']['scores']))
            title = "🔥 খুব শক্তিশালী সিম্বল (স্কোর 80+)"
        elif category == "good":
            symbols_with_scores = list(zip(stats['good']['symbols'], stats['good']['scores']))
            title = "✅ ভাল সিম্বল (স্কোর 60-79)"
        elif category == "medium":
            symbols_with_scores = list(zip(stats['medium']['symbols'], stats['medium']['scores']))
            title = "⚠️ মধ্যম সিম্বল (স্কোর 40-59)"
        elif category == "weak":
            symbols_with_scores = list(zip(stats['weak']['symbols'], stats['weak']['scores']))
            title = "❌ দুর্বল সিম্বল (স্কোর <40)"
        elif category == "impulse":
            symbols_with_scores = [(sym, "-") for sym in stats['impulse']['symbols']]
            title = "📈 ইম্পালস ওয়েভ সিম্বল"
        elif category == "corrective":
            symbols_with_scores = [(sym, "-") for sym in stats['corrective']['symbols']]
            title = "🔄 করেকটিভ ওয়েভ সিম্বল"
        else:
            return "❌ ভুল ক্যাটাগরি।"
        
        if not symbols_with_scores:
            return f"📭 {title} - কোনো সিম্বল নেই।"
        
        total = len(symbols_with_scores)
        total_pages = (total + items_per_page - 1) // items_per_page
        
        if page > total_pages:
            page = total_pages
        
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
            rating = ""
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
        
        result += "```"
        
        # পেজিনেশন লিংক
        nav_parts = []
        if page > 1:
            nav_parts.append(f"[◀️](/vs {category} {page-1})")
        else:
            nav_parts.append("◀️")
        
        if total_pages <= 7:
            for p in range(1, total_pages + 1):
                if p == page:
                    nav_parts.append(f"**{p}**")
                else:
                    nav_parts.append(f"[{p}](/vs {category} {p})")
        else:
            if page <= 4:
                for p in range(1, 6):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/vs {category} {p})")
                nav_parts.append("...")
                nav_parts.append(f"[{total_pages}](/vs {category} {total_pages})")
            elif page >= total_pages - 3:
                nav_parts.append(f"[1](/vs {category} 1)")
                nav_parts.append("...")
                for p in range(total_pages - 4, total_pages + 1):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/vs {category} {p})")
            else:
                nav_parts.append(f"[1](/vs {category} 1)")
                nav_parts.append("...")
                for p in range(page - 1, page + 2):
                    if p == page:
                        nav_parts.append(f"**{p}**")
                    else:
                        nav_parts.append(f"[{p}](/vs {category} {p})")
                nav_parts.append("...")
                nav_parts.append(f"[{total_pages}](/vs {category} {total_pages})")
        
        if page < total_pages:
            nav_parts.append(f"[▶️](/vs {category} {page+1})")
        else:
            nav_parts.append("▶️")
        
        nav_bar = " ".join(nav_parts)
        result += f"\n\n{nav_bar}"
        
        return result

# ==================== টেলিগ্রাম হ্যান্ডলার ====================

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """/portfolio কমান্ড হ্যান্ডলার"""
    args = context.args
    
    # তারিখ নির্ধারণ
    if args:
        date_input = args[0]
        # তারিখ ফরম্যাট ঠিক করা
        date = bot.fix_date_format(date_input) if hasattr(bot, 'fix_date_format') else date_input
    else:
        # আজকের বা সর্বশেষ ফাইল
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
    
    # ডাটা লোড করুন
    data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
    if data is None:
        await status_msg.edit_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    # হেডার চেক করুন
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    
    all_data = data[start_idx:]
    
    if not all_data:
        await status_msg.edit_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return
    
    # অ্যানালাইসিস করুন
    stats = portfolio_analyzer.analyze_portfolio(all_data)
    
    if not stats:
        await status_msg.edit_text("❌ অ্যানালাইসিস করতে ব্যর্থ হয়েছে।")
        return
    
    # রিপোর্ট তৈরি করুন
    report = portfolio_analyzer.format_portfolio_report(stats, date)
    
    await status_msg.edit_text(report, parse_mode='Markdown')

async def show_category_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot, category):
    """ক্যাটাগরি অনুযায়ী সিম্বল দেখান"""
    args = context.args
    
    # তারিখ নির্ধারণ
    if args and len(args) > 0:
        date_input = args[0]
        date = bot.fix_date_format(date_input) if hasattr(bot, 'fix_date_format') else date_input
        page = 1
        if len(args) > 1:
            try:
                page = int(args[1])
                if page < 1:
                    page = 1
            except:
                page = 1
    else:
        if bot.current_data:
            date = bot.current_date
            page = 1
        else:
            files = portfolio_analyzer.hf_manager.get_all_csv_files()
            if files:
                date = files[0]
                page = 1
            else:
                await update.message.reply_text("❌ কোনো CSV ফাইল নেই।")
                return
    
    status_msg = await update.message.reply_text(f"⏳ {category} ক্যাটাগরির ডাটা লোড করা হচ্ছে ({date})...")
    
    # ডাটা লোড করুন
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
    
    # অ্যানালাইসিস করুন
    stats = portfolio_analyzer.analyze_portfolio(all_data)
    
    if not stats:
        await status_msg.edit_text("❌ অ্যানালাইসিস করতে ব্যর্থ হয়েছে।")
        return
    
    # ক্যাটাগরি অনুযায়ী ফলাফল
    result = portfolio_analyzer.show_category_symbols(stats, category, page)
    
    await status_msg.edit_text(result, parse_mode='Markdown')

async def best_rrr_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """সেরা RRR দেখান"""
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
    
    data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
    if data is None:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    
    all_data = data[start_idx:]
    
    if not all_data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return
    
    # সেরা RRR খুঁজুন
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
        await update.message.reply_text(result, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ কোনো RRR ডাটা পাওয়া যায়নি।")

async def highest_score_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """সর্বোচ্চ স্কোর দেখান"""
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
    
    data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
    if data is None:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    
    all_data = data[start_idx:]
    
    if not all_data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return
    
    # সর্বোচ্চ স্কোর খুঁজুন
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
        await update.message.reply_text(result, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ কোনো স্কোর ডাটা পাওয়া যায়নি।")

async def top_recommendations_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """টপ রিকমেন্ডেশন দেখান"""
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
    
    data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
    if data is None:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    
    all_data = data[start_idx:]
    
    if not all_data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return
    
    stats = portfolio_analyzer.analyze_portfolio(all_data)
    
    if not stats or not stats['top_recommendations']:
        await update.message.reply_text(f"📭 {date} তারিখে কোনো টপ রিকমেন্ডেশন নেই।")
        return
    
    result = f"💡 **টপ রিকমেন্ডেশন - {date}**\n\n"
    result += "```\n"
    result += f"{'ক্রম':<6} {'সিম্বল':<15} {'স্কোর':<10} {'RRR'}\n"
    result += "-" * 45 + "\n"
    
    for i, sym in enumerate(stats['top_recommendations'][:10]):
        # সিম্বলের স্কোর এবং RRR খুঁজুন
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
    await update.message.reply_text(result, parse_mode='Markdown')

async def avoid_symbols_command(update: Update, context: ContextTypes.DEFAULT_TYPE, portfolio_analyzer, bot):
    """এড়িয়ে চলুন সিম্বল দেখান"""
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
    
    data = portfolio_analyzer.hf_manager.read_csv_file(date)
    
    if data is None:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    
    all_data = data[start_idx:]
    
    if not all_data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return
    
    stats = portfolio_analyzer.analyze_portfolio(all_data)
    
    if not stats or not stats['avoid_symbols']:
        await update.message.reply_text(f"📭 {date} তারিখে কোনো দুর্বল সিম্বল নেই।")
        return
    
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
    await update.message.reply_text(result, parse_mode='Markdown')