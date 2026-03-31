# advanced_features.py - চার্ট, কম্পেয়ার, নোটিফিকেশন, ব্যাকটেস্ট, এক্সপোর্ট (সম্পূর্ণ আপডেটেড)

import io
import os
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# matplotlib ব্যাকএন্ড সেট করুন
plt.switch_backend('Agg')

class AdvancedFeatures:
    """অ্যাডভান্সড ফিচারস - চার্ট, কম্পেয়ার, নোটিফিকেশন, ব্যাকটেস্ট, এক্সপোর্ট"""

    def __init__(self, hf_manager, bot):
        self.hf_manager = hf_manager
        self.bot = bot

    def get_score_value(self, score_str):
        """স্কোর স্ট্রিং থেকে সংখ্যাসূচক মান বের করুন"""
        try:
            if not score_str or score_str == '-' or score_str == '':
                return None
            score_str = str(score_str).replace('%', '').strip()
            return int(score_str)
        except:
            return None

    def generate_score_distribution_chart(self, all_data: List, date: str) -> io.BytesIO:
        """স্কোর ডিস্ট্রিবিউশন চার্ট তৈরি করুন"""
        scores = []
        for row in all_data:
            if len(row) > 9:
                score = self.get_score_value(row[9])
                if score is not None:
                    scores.append(score)

        if not scores:
            return None

        # চার্টের সাইজ
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # স্কোর ক্যাটাগরি অনুযায়ী রং
        bins = [0, 40, 50, 60, 70, 80, 90, 100]
        colors = ['#F44336', '#FF9800', '#FFC107', '#8BC34A', '#4CAF50', '#2196F3', '#9C27B0']
        
        n, bins, patches = ax.hist(scores, bins=bins, edgecolor='black', alpha=0.7)
        
        # প্রতিটি বার এর রং সেট করুন
        for patch, color in zip(patches, colors[:len(patches)]):
            patch.set_facecolor(color)
        
        # লেবেল এবং টাইটেল
        ax.set_xlabel('স্কোর রেঞ্জ', fontsize=12, fontweight='bold')
        ax.set_ylabel('সিম্বল সংখ্যা', fontsize=12, fontweight='bold')
        ax.set_title(f'📊 স্কোর ডিস্ট্রিবিউশন - {date}', fontsize=14, fontweight='bold')
        
        # গ্রিড
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # ক্যাটাগরি লাইন
        ax.axvline(x=70, color='darkgreen', linestyle='--', linewidth=2, label='শক্তিশালী (70+)', alpha=0.8)
        ax.axvline(x=50, color='orange', linestyle='--', linewidth=2, label='মধ্যম (50)', alpha=0.8)
        ax.axvline(x=40, color='darkred', linestyle='--', linewidth=2, label='দুর্বল (40)', alpha=0.8)
        
        ax.legend(loc='upper left', fontsize=10)
        
        # স্ট্যাটিস্টিক্স টেক্সট
        stats_text = f"📈 মোট: {len(scores)} | 🎯 গড়: {np.mean(scores):.1f} | 📍 মধ্যমা: {np.median(scores):.1f}"
        stats_text2 = f"🔝 সর্বোচ্চ: {max(scores)} | 📉 সর্বনিম্ন: {min(scores)}"
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        ax.text(0.02, 0.92, stats_text2, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf

    def calculate_portfolio_stats(self, all_data: List) -> Dict:
        """পোর্টফোলিও স্ট্যাটিস্টিক্স ক্যালকুলেট করুন"""
        scores = []
        symbols = []
        impulse_count = 0
        corrective_count = 0
        high_score_symbols = []
        
        for row in all_data:
            if not row or len(row) < 1:
                continue
            
            if len(row) > 0 and row[0]:
                symbols.append(row[0])
            
            if len(row) > 9:
                score = self.get_score_value(row[9])
                if score is not None:
                    scores.append(score)
                    if score >= 70:
                        high_score_symbols.append(row[0])
            
            # ওয়েভ টাইপ চেক
            if len(row) > 1:
                wave_text = row[1].lower() if row[1] else ''
                if 'impulse' in wave_text or 'মোটিভ' in wave_text:
                    impulse_count += 1
                elif 'corrective' in wave_text or 'করেকটিভ' in wave_text:
                    corrective_count += 1
        
        # স্কোর ক্যাটাগরি ভাগ
        strong = len([s for s in scores if s >= 70])
        good = len([s for s in scores if 60 <= s < 70])
        medium = len([s for s in scores if 50 <= s < 60])
        weak = len([s for s in scores if 40 <= s < 50])
        very_weak = len([s for s in scores if s < 40])
        
        return {
            'total': len(symbols),
            'avg_score': np.mean(scores) if scores else 0,
            'median_score': np.median(scores) if scores else 0,
            'max_score': max(scores) if scores else 0,
            'min_score': min(scores) if scores else 0,
            'impulse_count': impulse_count,
            'corrective_count': corrective_count,
            'strong_count': strong,
            'good_count': good,
            'medium_count': medium,
            'weak_count': weak,
            'very_weak_count': very_weak,
            'high_score_symbols': high_score_symbols[:10]
        }

    def compare_portfolios(self, date1: str, date2: str, hf_manager) -> str:
        """দুটি তারিখের পোর্টফোলিও তুলনা করুন"""
        data1 = hf_manager.read_csv_file(date1)
        data2 = hf_manager.read_csv_file(date2)

        if not data1 or not data2:
            return "❌ একটি বা উভয় ফাইল পাওয়া যায়নি।"

        start_idx = 0
        if data1 and data1[0] and len(data1[0]) > 0 and data1[0][0] == "symbol":
            start_idx = 1
        all_data1 = data1[start_idx:]

        start_idx = 0
        if data2 and data2[0] and len(data2[0]) > 0 and data2[0][0] == "symbol":
            start_idx = 1
        all_data2 = data2[start_idx:]

        # স্ট্যাটিস্টিক্স
        stats1 = self.calculate_portfolio_stats(all_data1)
        stats2 = self.calculate_portfolio_stats(all_data2)

        # সিম্বল ট্র্যাক
        symbols1 = set([row[0] for row in all_data1 if row and len(row) > 0])
        symbols2 = set([row[0] for row in all_data2 if row and len(row) > 0])

        new_symbols = symbols2 - symbols1
        removed_symbols = symbols1 - symbols2
        common_symbols = symbols1 & symbols2

        # কমন সিম্বলের স্কোর পরিবর্তন
        score_changes = []
        for sym in common_symbols:
            score1 = None
            score2 = None
            for row in all_data1:
                if row and len(row) > 0 and row[0] == sym and len(row) > 9:
                    score1 = self.get_score_value(row[9])
                    break
            for row in all_data2:
                if row and len(row) > 0 and row[0] == sym and len(row) > 9:
                    score2 = self.get_score_value(row[9])
                    break
            if score1 is not None and score2 is not None:
                score_changes.append(score2 - score1)

        result = f"""
📊 **পোর্টফোলিও কম্পেয়ার**

📅 {date1}  →  {date2}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **{date1} স্ট্যাটিস্টিক্স:**
• মোট সিম্বল: {stats1['total']}
• গড় স্কোর: {stats1['avg_score']:.1f}
• সর্বোচ্চ স্কোর: {stats1['max_score']}
• সর্বনিম্ন স্কোর: {stats1['min_score']}
• ইম্পালস ওয়েভ: {stats1['impulse_count']}
• করেকটিভ ওয়েভ: {stats1['corrective_count']}

📈 **{date2} স্ট্যাটিস্টিক্স:**
• মোট সিম্বল: {stats2['total']}
• গড় স্কোর: {stats2['avg_score']:.1f}
• সর্বোচ্চ স্কোর: {stats2['max_score']}
• সর্বনিম্ন স্কোর: {stats2['min_score']}
• ইম্পালস ওয়েভ: {stats2['impulse_count']}
• করেকটিভ ওয়েভ: {stats2['corrective_count']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆕 **নতুন যোগ হয়েছে ({len(new_symbols)}):**
{', '.join(list(new_symbols)[:15]) if new_symbols else 'কোনো নতুন নেই'}

❌ **বাদ পড়েছে ({len(removed_symbols)}):**
{', '.join(list(removed_symbols)[:15]) if removed_symbols else 'কোনো বাদ নেই'}

🔄 **কমন সিম্বল ({len(common_symbols)}):**
• গড় স্কোর পরিবর্তন: {np.mean(score_changes):+.1f if score_changes else 0} পয়েন্ট
• সর্বোচ্চ বৃদ্ধি: {max(score_changes) if score_changes else 0:+.1f}
• সর্বোচ্চ পতন: {min(score_changes) if score_changes else 0:+.1f}

💡 **সুপারিশ:**
{self.get_comparison_recommendation(stats1, stats2)}
"""
        return result

    def get_comparison_recommendation(self, stats1: Dict, stats2: Dict) -> str:
        """কম্পেয়ার রেজাল্টের ভিত্তিতে সুপারিশ"""
        avg_change = stats2['avg_score'] - stats1['avg_score']
        if avg_change > 5:
            return f"🔥 পোর্টফোলিওর মান উল্লেখযোগ্যভাবে উন্নত হয়েছে! (+{avg_change:.1f} পয়েন্ট)"
        elif avg_change > 0:
            return f"✅ পোর্টফোলিওর মান সামান্য উন্নত হয়েছে। (+{avg_change:.1f} পয়েন্ট)"
        elif avg_change > -5:
            return f"⚠️ পোর্টফোলিওর মান সামান্য কমেছে। ({avg_change:+.1f} পয়েন্ট)"
        else:
            return f"❌ পোর্টফোলিওর মান উল্লেখযোগ্যভাবে কমেছে! ({avg_change:+.1f} পয়েন্ট)"

    def backtest_strategy(self, start_date: str, end_date: str, min_score: int = 70, hf_manager=None) -> str:
        """ব্যাকটেস্টিং - পুরোনো ডাটা টেস্ট করুন"""
        if hf_manager is None:
            hf_manager = self.hf_manager
            
        dates = hf_manager.get_all_csv_files()
        filtered_dates = [d for d in dates if start_date <= d <= end_date]

        if not filtered_dates:
            return "❌ এই সময়ের মধ্যে কোনো ডাটা নেই।"

        results = {
            'total_signals': 0,
            'avg_score': 0,
            'best_symbol': None,
            'best_score': 0,
            'scores_by_date': {},
            'symbol_performance': {}
        }

        all_scores = []

        for date in filtered_dates:
            data = hf_manager.read_csv_file(date)
            if data:
                start_idx = 0
                if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                    start_idx = 1
                all_data = data[start_idx:]

                daily_scores = []
                for row in all_data:
                    if len(row) > 9:
                        score = self.get_score_value(row[9])
                        symbol = row[0] if len(row) > 0 else 'Unknown'
                        if score is not None and score >= min_score:
                            results['total_signals'] += 1
                            all_scores.append(score)
                            daily_scores.append(score)
                            
                            if score > results['best_score']:
                                results['best_score'] = score
                                results['best_symbol'] = symbol
                            
                            # সিম্বল পারফরম্যান্স ট্র্যাক
                            if symbol not in results['symbol_performance']:
                                results['symbol_performance'][symbol] = {'count': 0, 'scores': []}
                            results['symbol_performance'][symbol]['count'] += 1
                            results['symbol_performance'][symbol]['scores'].append(score)
                
                if daily_scores:
                    results['scores_by_date'][date] = np.mean(daily_scores)

        results['avg_score'] = np.mean(all_scores) if all_scores else 0
        
        # টপ পারফর্মিং সিম্বল
        top_symbols = sorted(results['symbol_performance'].items(), 
                            key=lambda x: np.mean(x[1]['scores']), reverse=True)[:5]

        result = f"""
📊 **ব্যাকটেস্ট রিপোর্ট**

📅 সময়কাল: {start_date} → {end_date}
🎯 মিনিমাম স্কোর: {min_score}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **সারাংশ:**
• মোট সিগন্যাল: {results['total_signals']}
• গড় স্কোর: {results['avg_score']:.1f}
• বেস্ট সিম্বল: {results['best_symbol']} ({results['best_score']}/100)

🏆 **টপ পারফর্মিং সিম্বল:**
{chr(10).join([f"  • {sym}: {np.mean(data['scores']):.1f}/100 ({data['count']}x)" for sym, data in top_symbols])}

💡 **সুপারিশ:**
{self.get_backtest_recommendation(results['total_signals'], results['avg_score'])}
"""
        return result

    def get_backtest_recommendation(self, signals: int, avg_score: float) -> str:
        """ব্যাকটেস্ট রেজাল্টের ভিত্তিতে সুপারিশ"""
        if signals > 50 and avg_score > 70:
            return "🔥 এক্সেলেন্ট! এই স্কোর ফিল্টার ব্যবহার করুন।"
        elif signals > 30 and avg_score > 65:
            return "📈 ভালো ফলাফল। স্কোর >=70 টার্গেট করুন।"
        elif signals > 10 and avg_score > 60:
            return "⚠️ মধ্যম ফলাফল। স্কোর বাড়ানোর চেষ্টা করুন।"
        elif signals > 0:
            return "❌ দুর্বল ফলাফল। স্কোর ফিল্টার কমানোর চেষ্টা করুন।"
        else:
            return "❌ পর্যাপ্ত সিগন্যাল নেই। স্কোর কমিয়ে চেষ্টা করুন।"

    def export_to_csv(self, date: str) -> io.BytesIO:
        """পোর্টফোলিও CSV এক্সপোর্ট করুন"""
        data = self.hf_manager.read_csv_file(date)
        if not data:
            return None

        output = io.StringIO()
        writer = csv.writer(output)
        
        for row in data:
            writer.writerow(row)

        output.seek(0)
        
        bytes_io = io.BytesIO()
        bytes_io.write(output.getvalue().encode('utf-8-sig'))
        bytes_io.seek(0)
        
        return bytes_io

    def generate_weekly_report(self, dates: List[str], hf_manager) -> str:
        """সাপ্তাহিক রিপোর্ট জেনারেট করুন"""
        weekly_stats = []
        
        for date in dates:
            data = hf_manager.read_csv_file(date)
            if data:
                start_idx = 0
                if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
                    start_idx = 1
                all_data = data[start_idx:]
                stats = self.calculate_portfolio_stats(all_data)
                weekly_stats.append({
                    'date': date,
                    'avg_score': stats['avg_score'],
                    'total': stats['total'],
                    'strong': stats['strong_count']
                })
        
        if not weekly_stats:
            return "❌ কোনো ডাটা পাওয়া যায়নি।"
        
        result = f"""
📊 **সাপ্তাহিক রিপোর্ট**

📅 {dates[0]} → {dates[-1]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **দিন অনুযায়ী পারফরম্যান্স:**
"""
        for stat in weekly_stats:
            result += f"• {stat['date']}: {stat['avg_score']:.1f} avg ({stat['total']} সিম্বল)\n"
        
        result += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **ট্রেন্ড:**
• গড় স্কোর প্রবণতা: {self.get_trend_direction([s['avg_score'] for s in weekly_stats])}
• সিম্বল সংখ্যা প্রবণতা: {self.get_trend_direction([s['total'] for s in weekly_stats])}

💡 **সাপ্তাহিক সুপারিশ:**
{self.get_weekly_recommendation(weekly_stats)}
"""
        return result

    def get_trend_direction(self, values: List[float]) -> str:
        """ট্রেন্ড ডিরেকশন নির্ণয় করুন"""
        if len(values) < 2:
            return "স্থির"
        
        first = values[0]
        last = values[-1]
        
        if last > first * 1.05:
            return "🔼 ঊর্ধ্বমুখী"
        elif last < first * 0.95:
            return "🔽 নিম্নমুখী"
        else:
            return "➡️ স্থির"

    def get_weekly_recommendation(self, weekly_stats: List[Dict]) -> str:
        """সাপ্তাহিক সুপারিশ"""
        latest = weekly_stats[-1]['avg_score']
        if latest >= 70:
            return "🔥 মার্কেট শক্তিশালী অবস্থানে। ট্রেডিং চালিয়ে যান।"
        elif latest >= 60:
            return "📈 মার্কেট মধ্যম অবস্থানে। সিলেক্টিভ ট্রেডিং করুন।"
        elif latest >= 50:
            return "⚠️ মার্কেট দুর্বল। রিস্ক ম্যানেজমেন্ট গুরুত্ব দিন।"
        else:
            return "❌ মার্কেট খুব দুর্বল। ক্যাশে থাকুন।"


# ==================== টেলিগ্রাম হ্যান্ডলার ====================

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE, hf_manager=None, bot=None):
    """চার্ট জেনারেট করুন"""
    args = context.args
    date = args[0] if args else datetime.now().strftime("%d-%m-%Y")
    
    # context.bot_data থেকে নিন
    if hf_manager is None:
        hf_manager = context.bot_data.get('hf_manager')
    if bot is None:
        bot = context.bot_data.get('bot')

    await update.message.reply_text(f"⏳ চার্ট জেনারেট হচ্ছে ({date})...")

    data = hf_manager.read_csv_file(date)
    if not data:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return

    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    all_data = data[start_idx:]

    if not all_data:
        await update.message.reply_text(f"📭 {date}.csv ফাইলে কোনো ডাটা নেই।")
        return

    adv = AdvancedFeatures(hf_manager, bot)
    chart = adv.generate_score_distribution_chart(all_data, date)
    
    if chart:
        await update.message.reply_photo(
            photo=chart,
            caption=f"📊 স্কোর ডিস্ট্রিবিউশন - {date}\nমোট সিম্বল: {len(all_data)}"
        )
    else:
        await update.message.reply_text("❌ চার্ট জেনারেট করতে ব্যর্থ হয়েছে। পর্যাপ্ত ডাটা নেই।")

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE, hf_manager=None, bot=None):
    """দুটি তারিখের পোর্টফোলিও তুলনা করুন"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ দুটি তারিখ দিন। উদাহরণ: `/compare 25-03-2026 26-03-2026`"
        )
        return

    date1 = context.args[0]
    date2 = context.args[1]
    
    if hf_manager is None:
        hf_manager = context.bot_data.get('hf_manager')

    adv = AdvancedFeatures(hf_manager, bot)
    result = adv.compare_portfolios(date1, date2, hf_manager)
    
    # মেসেজ খুব লম্বা হলে ভাগ করে পাঠান
    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(result, parse_mode='Markdown')

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নোটিফিকেশন সিস্টেম সেটআপ"""
    await update.message.reply_text(
        "🔔 **নোটিফিকেশন সিস্টেম**\n\n"
        "নতুন সিগন্যাল এলে আমি জানাবো!\n\n"
        "📌 **সেটআপ করতে:** `/setalert [স্কোর]`\n"
        "উদাহরণ: `/setalert 70` (70+ স্কোরের সিম্বল এলে নোটিফিকেশন)\n\n"
        "📌 **অ্যালার্ট বন্ধ করতে:** `/stopalert`\n\n"
        "⚠️ বর্তমানে এই ফিচারটি টেস্টিং মোডে আছে।",
        parse_mode='Markdown'
    )

async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যালার্ট সেট করুন"""
    if not context.args:
        await update.message.reply_text("❌ স্কোর দিন। উদাহরণ: `/setalert 70`")
        return

    try:
        min_score = int(context.args[0])
        context.user_data['alert_score'] = min_score
        context.user_data['alert_active'] = True
        await update.message.reply_text(
            f"✅ **অ্যালার্ট সেট করা হয়েছে!**\n\n"
            f"📊 মিনিমাম স্কোর: {min_score}+\n"
            f"🔔 নতুন সিম্বল এলে আমি আপনাকে জানাবো।\n\n"
            f"🛑 বন্ধ করতে: `/stopalert`",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ ভ্যালিড স্কোর দিন (সংখ্যা)।")

async def stopalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যালার্ট বন্ধ করুন"""
    context.user_data['alert_active'] = False
    context.user_data['alert_score'] = None
    await update.message.reply_text(
        "✅ **অ্যালার্ট বন্ধ করা হয়েছে!**\n\n"
        "আবার চালু করতে: `/setalert [স্কোর]`",
        parse_mode='Markdown'
    )

async def backtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE, hf_manager=None):
    """ব্যাকটেস্ট রান করুন"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ স্টার্ট এবং এন্ড তারিখ দিন।\n"
            "উদাহরণ: `/backtest 01-03-2026 29-03-2026`\n"
            "অথবা স্কোরসহ: `/backtest 01-03-2026 29-03-2026 70`"
        )
        return

    start_date = args[0]
    end_date = args[1]
    min_score = int(args[2]) if len(args) > 2 else 70

    if hf_manager is None:
        hf_manager = context.bot_data.get('hf_manager')

    await update.message.reply_text(f"⏳ ব্যাকটেস্ট রান হচ্ছে... ({start_date} → {end_date})")

    adv = AdvancedFeatures(hf_manager, None)
    result = adv.backtest_strategy(start_date, end_date, min_score, hf_manager)
    
    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(result, parse_mode='Markdown')

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE, hf_manager=None):
    """CSV এক্সপোর্ট করুন"""
    args = context.args
    date = args[0] if args else datetime.now().strftime("%d-%m-%Y")

    if hf_manager is None:
        hf_manager = context.bot_data.get('hf_manager')

    await update.message.reply_text(f"⏳ এক্সপোর্ট হচ্ছে ({date})...")

    adv = AdvancedFeatures(hf_manager, None)
    csv_file = adv.export_to_csv(date)
    
    if csv_file:
        await update.message.reply_document(
            document=csv_file,
            filename=f"portfolio_{date}.csv",
            caption=f"📁 পোর্টফোলিও রিপোর্ট - {date}\n📅 এক্সপোর্ট সময়: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        )
    else:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")

async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE, hf_manager=None):
    """সাপ্তাহিক রিপোর্ট দেখান"""
    if hf_manager is None:
        hf_manager = context.bot_data.get('hf_manager')
    
    dates = hf_manager.get_all_csv_files()
    if len(dates) < 5:
        await update.message.reply_text("❌ সাপ্তাহিক রিপোর্টের জন্য পর্যাপ্ত ডাটা নেই।")
        return
    
    last_7_days = dates[:7]
    adv = AdvancedFeatures(hf_manager, None)
    result = adv.generate_weekly_report(last_7_days, hf_manager)
    
    await update.message.reply_text(result, parse_mode='Markdown')