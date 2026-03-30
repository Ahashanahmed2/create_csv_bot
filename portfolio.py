# portfolio.py - পোর্টফোলিও অ্যানালাইটিক্স মডিউল (সাব-ওয়েব সহ)

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
        if 'impulse' in wave_lower or 'impuls' in wave_lower or 'মোটিভ' in wave_lower:
            return 'impulse'
        elif 'corrective' in wave_lower or 'করেকটিভ' in wave_lower:
            return 'corrective'
        else:
            return 'impulse'

    def categorize_by_score(self, score_str):
        """স্কোর অনুযায়ী ক্যাটাগরি নির্ধারণ"""
        try:
            # Remove % sign if present
            score_str = str(score_str).replace('%', '')
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
            score_str = str(score).replace('%', '')
            score_num = int(score_str)
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
        """পোর্টফোলিও ডাটা অ্যানালাইসিস করুন - সাব-ওয়েব সহ"""
        if not data:
            return None

        stats = {
            'total': len(data),
            'very_strong': {'count': 0, 'symbols': [], 'scores': [], 'subwaves': []},
            'good': {'count': 0, 'symbols': [], 'scores': [], 'subwaves': []},
            'medium': {'count': 0, 'symbols': [], 'scores': [], 'subwaves': []},
            'weak': {'count': 0, 'symbols': [], 'scores': [], 'subwaves': []},
            'impulse': {'count': 0, 'symbols': [], 'subwaves': []},
            'corrective': {'count': 0, 'symbols': [], 'subwaves': []},
            'best_rrr': {'value': 0, 'symbol': '', 'rrr': ''},
            'highest_score': {'value': 0, 'symbol': '', 'score': ''},
            'top_recommendations': [],
            'avoid_symbols': []
        }

        print(f"🔍 Analyzing {len(data)} records for portfolio...")

        for idx, row in enumerate(data):
            if not row or len(row) < 3:
                print(f"⚠️ Row {idx} has insufficient columns: {len(row) if row else 0}")
                continue

            symbol = row[0] if len(row) > 0 else "Unknown"
            score_str = row[9] if len(row) > 9 else "0"
            rrr_str = row[8] if len(row) > 8 else "1:0"
            wave_text = row[1] if len(row) > 1 else ""
            
            # সাব-ওয়েব সঠিকভাবে নিন - কলাম 2 (index 2)
            sub_wave = "-"
            if len(row) > 2:
                raw_subwave = row[2]
                if raw_subwave and raw_subwave.strip():
                    # Remove any emoji or special characters
                    clean_subwave = raw_subwave.strip()
                    # Keep meaningful subwave like "Wave 3", "Wave 5 of 3", etc.
                    if clean_subwave not in ["✅", "❌", "⚠️", "⭐", "🔥", "💎", "📈", "-"]:
                        sub_wave = clean_subwave
                    else:
                        sub_wave = "-"
                else:
                    sub_wave = "-"
            else:
                sub_wave = "-"
            
            print(f"📊 {symbol}: wave={wave_text}, subwave='{sub_wave}', score={score_str}")

            # স্কোর অনুযায়ী ক্যাটাগরি
            category = self.categorize_by_score(score_str)
            try:
                score_val = int(str(score_str).replace('%', ''))
            except:
                score_val = 0

            if category == "very_strong":
                stats['very_strong']['count'] += 1
                stats['very_strong']['symbols'].append(symbol)
                stats['very_strong']['scores'].append(score_val)
                stats['very_strong']['subwaves'].append(sub_wave)
            elif category == "good":
                stats['good']['count'] += 1
                stats['good']['symbols'].append(symbol)
                stats['good']['scores'].append(score_val)
                stats['good']['subwaves'].append(sub_wave)
            elif category == "medium":
                stats['medium']['count'] += 1
                stats['medium']['symbols'].append(symbol)
                stats['medium']['scores'].append(score_val)
                stats['medium']['subwaves'].append(sub_wave)
            else:
                stats['weak']['count'] += 1
                stats['weak']['symbols'].append(symbol)
                stats['weak']['scores'].append(score_val)
                stats['weak']['subwaves'].append(sub_wave)

            # ওয়েভ টাইপ
            wave_type = self.get_wave_type(wave_text)
            if wave_type == 'impulse':
                stats['impulse']['count'] += 1
                stats['impulse']['symbols'].append(symbol)
                stats['impulse']['subwaves'].append(sub_wave)
            else:
                stats['corrective']['count'] += 1
                stats['corrective']['symbols'].append(symbol)
                stats['corrective']['subwaves'].append(sub_wave)

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

        # টপ রিকমেন্ডেশন (স্কোর 80+)
        for i, sym in enumerate(stats['very_strong']['symbols'][:5]):
            stats['top_recommendations'].append(sym)

        # এড়িয়ে চলুন (স্কোর 50 এর নিচে)
        for sym in stats['weak']['symbols']:
            stats['avoid_symbols'].append(sym)
            
        print(f"✅ Analysis complete: Very Strong={stats['very_strong']['count']}, Good={stats['good']['count']}, Medium={stats['medium']['count']}, Weak={stats['weak']['count']}")

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

    def format_symbols_with_buttons(self, symbols_data, title, date, category, page, total_pages, items_per_page=10):
        """সিম্বল লিস্ট ইনলাইন বাটন সহ - সাব-ওয়েব সহ"""
        if not symbols_data:
            return f"📭 {title} - কোনো সিম্বল নেই।", None

        total = len(symbols_data)
        start = (page - 1) * items_per_page
        end = min(start + items_per_page, total)
        page_data = symbols_data[start:end]

        # title থেকে ক্যাটাগরি টাইপ বের করুন
        if "দুর্বল" in title:
            category_name = "দুর্বল"
            emoji = "❌"
        elif "মধ্যম" in title:
            category_name = "মধ্যম"
            emoji = "⚠️"
        elif "ভাল" in title:
            category_name = "ভাল"
            emoji = "✅"
        elif "শক্তিশালী" in title:
            category_name = "খুব শক্তিশালী"
            emoji = "🔥"
        else:
            category_name = title.split("(")[0].strip()
            emoji = "📊"

        result = f"{emoji} **{category_name} সিম্বল ({title.split('(')[-1].replace(')', '')})** | 📋 {total} টি সিম্বল | 📄 পৃষ্ঠা {page}/{total_pages}\n\n"
        result += "```\n"
        result += f"{'ক্রম':<6} {'সিম্বল':<15} {'স্কোর':<10} {'সাব-ওয়েব':<25}\n"
        result += "-" * 56 + "\n"

        for i, item in enumerate(page_data):
            serial = start + i + 1
            if len(item) == 3:  # (symbol, score, subwave)
                symbol, score, subwave = item
            elif len(item) == 2:  # (symbol, score) fallback
                symbol, score = item
                subwave = "-"
            else:
                symbol, score = item, "-"
                subwave = "-"

            # Clean subwave
            if subwave in ["✅", "❌", "⚠️", "⭐", "🔥", "💎", "📈", "-"]:
                subwave = "-"

            # Clean score (remove %)
            score_display = str(score).replace('%', '') if score != "-" else "-"
            emoji_score = self.get_score_emoji(score) if score != "-" else "📊"
            
            if score != "-":
                result += f"{serial:<6} {symbol:<15} {score_display}/100 {emoji_score:<5} {subwave:<25}\n"
            else:
                result += f"{serial:<6} {symbol:<15} {'':<10} {emoji_score:<5} {subwave:<25}\n"

        result += "```\n\n"

        keyboard = []

        # সিম্বল বাটন (প্রতি লাইনে ৩টি)
        row = []
        for item in page_data[:9]:
            symbol = item[0] if len(item) > 0 else ""
            if symbol:
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
║ 🌊 এলিয়ট ওয়েব : {symbol_data['wave_type']}
║ 📍 সাব-ওয়েব    : {symbol_data['wave_detail']}
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
                # Remove % from score
                score_str_clean = str(score_str).replace('%', '')
                try:
                    score_val = int(score_str_clean)
                except:
                    score_val = 0
                
                # সাব-ওয়েব নিন
                sub_wave = "-"
                if len(row) > 2 and row[2] and row[2].strip():
                    clean_subwave = row[2].strip()
                    if clean_subwave not in ["✅", "❌", "⚠️", "⭐", "🔥", "💎", "📈", "-"]:
                        sub_wave = clean_subwave
                    else:
                        sub_wave = "-"

                return {
                    'rank': idx + 1,
                    'symbol': symbol,
                    'status_icon': self.get_score_emoji(score_str),
                    'wave_type': row[1] if len(row) > 1 else "-",
                    'wave_detail': sub_wave,
                    'entry': row[3] if len(row) > 3 else "-",
                    'stop_loss': row[4] if len(row) > 4 else "-",
                    'targets': f"{row[5]} → {row[6]} → {row[7]}" if len(row) > 7 else "-",
                    'rrr': row[8] if len(row) > 8 else "-",
                    'score': score_str,
                    'score_icon': self.get_score_emoji(score_str),
                    'rating': "খুব শক্তিশালী" if score_val >= 80 else "ভাল" if score_val >= 60 else "মধ্যম" if score_val >= 40 else "দুর্বল",
                    'insight': row[10] if len(row) > 10 else "তথ্য নেই"
                }
        return None