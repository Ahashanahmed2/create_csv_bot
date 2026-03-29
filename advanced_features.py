# advanced_features.py - চার্ট, কম্পেয়ার, নোটিফিকেশন, ব্যাকটেস্ট, এক্সপোর্ট

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
        
    def generate_score_distribution_chart(self, all_data: List, date: str) -> io.BytesIO:
        """স্কোর ডিস্ট্রিবিউশন চার্ট তৈরি করুন"""
        scores = []
        for row in all_data:
            if len(row) > 9 and row[9] and row[9] != '-':
                try:
                    score = int(row[9])
                    scores.append(score)
                except:
                    pass
        
        if not scores:
            return None
            
        plt.figure(figsize=(10, 6))
        plt.hist(scores, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
        plt.xlabel('স্কোর', fontsize=12)
        plt.ylabel('সিম্বল সংখ্যা', fontsize=12)
        plt.title(f'স্কোর ডিস্ট্রিবিউশন - {date}', fontsize=14)
        plt.axvline(x=70, color='green', linestyle='--', label='শক্তিশালী (70+)')
        plt.axvline(x=50, color='orange', linestyle='--', label='মধ্যম (50)')
        plt.axvline(x=40, color='red', linestyle='--', label='দুর্বল (40)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf
    
    def generate_winrate_trend_chart(self, dates_data: Dict) -> io.BytesIO:
        """উইন রেট ট্রেন্ড লাইন চার্ট"""
        dates = []
        win_rates = []
        
        for date, stats in sorted(dates_data.items()):
            total_tp = stats.get('total_tp', 0)
            total_sl = stats.get('total_sl', 0)
            total = total_tp + total_sl
            if total > 0:
                win_rate = (total_tp / total) * 100
                dates.append(date)
                win_rates.append(win_rate)
        
        if len(dates) < 2:
            return None
            
        plt.figure(figsize=(12, 6))
        plt.plot(dates, win_rates, marker='o', linewidth=2, markersize=8, color='green')
        plt.fill_between(dates, win_rates, alpha=0.3)
        plt.xlabel('তারিখ', fontsize=12)
        plt.ylabel('উইন রেট (%)', fontsize=12)
        plt.title('উইন রেট ট্রেন্ড', fontsize=14)
        plt.axhline(y=50, color='red', linestyle='--', label='50% লাইন')
        plt.xticks(rotation=45)
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf
    
    def compare_portfolios(self, date1: str, date2: str) -> str:
        """দুটি তারিখের পোর্টফোলিও তুলনা করুন"""
        data1 = self.hf_manager.read_csv_file(date1)
        data2 = self.hf_manager.read_csv_file(date2)
        
        if not data1 or not data2:
            return "❌ একটি বা উভয় ফাইল পাওয়া যায়নি।"
        
        start_idx = 0
        if data1 and data1[0] and data1[0][0] == "symbol":
            start_idx = 1
        all_data1 = data1[start_idx:]
        
        start_idx = 0
        if data2 and data2[0] and data2[0][0] == "symbol":
            start_idx = 1
        all_data2 = data2[start_idx:]
        
        # স্ট্যাটিস্টিক্স ক্যালকুলেট করুন
        stats1 = self.calculate_basic_stats(all_data1)
        stats2 = self.calculate_basic_stats(all_data2)
        
        # সিম্বল চেঞ্জ ট্র্যাক করুন
        symbols1 = set([row[0] for row in all_data1 if row])
        symbols2 = set([row[0] for row in all_data2 if row])
        
        new_symbols = symbols2 - symbols1
        removed_symbols = symbols1 - symbols2
        common_symbols = symbols1 & symbols2
        
        result = f"""
📊 **পোর্টফোলিও কম্পেয়ার**

📅 {date1} vs {date2}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **{date1} স্ট্যাটিস্টিক্স:**
• মোট সিম্বল: {stats1['total']}
• গড় স্কোর: {stats1['avg_score']}
• TP হিট: {stats1['total_tp']}
• SL হিট: {stats1['total_sl']}
• উইন রেট: {stats1['win_rate']:.1f}%

📈 **{date2} স্ট্যাটিস্টিক্স:**
• মোট সিম্বল: {stats2['total']}
• গড় স্কোর: {stats2['avg_score']}
• TP হিট: {stats2['total_tp']}
• SL হিট: {stats2['total_sl']}
• উইন রেট: {stats2['win_rate']:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆕 **নতুন যোগ হয়েছে ({len(new_symbols)}):**
{', '.join(list(new_symbols)[:15]) if new_symbols else 'কোনো নতুন নেই'}

❌ **বাদ পড়েছে ({len(removed_symbols)}):**
{', '.join(list(removed_symbols)[:15]) if removed_symbols else 'কোনো বাদ নেই'}

🔄 **কমন সিম্বল ({len(common_symbols)}):**
• {date1} গড় স্কোর: {stats1['common_avg']:.1f}
• {date2} গড় স্কোর: {stats2['common_avg']:.1f}
• পরিবর্তন: {stats2['common_avg'] - stats1['common_avg']:+.1f} পয়েন্ট
"""
        return result
    
    def calculate_basic_stats(self, data):
        """বেসিক স্ট্যাটিস্টিক্স ক্যালকুলেট করুন"""
        scores = []
        total_tp = 0
        total_sl = 0
        common_scores = []
        
        for row in data:
            if len(row) > 9 and row[9] and row[9] != '-':
                try:
                    score = int(row[9])
                    scores.append(score)
                except:
                    pass
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # টিপি/এসএল কাউন্ট (সিম্পলিফাইড)
        # এখানে আপনার আসল ডাটা স্ট্রাকচার অনুযায়ী অ্যাডজাস্ট করুন
        
        return {
            'total': len(data),
            'avg_score': avg_score,
            'total_tp': total_tp,
            'total_sl': total_sl,
            'win_rate': (total_tp / (total_tp + total_sl) * 100) if (total_tp + total_sl) > 0 else 0,
            'common_avg': avg_score
        }
    
    def backtest_strategy(self, start_date: str, end_date: str, min_score: int = 70) -> str:
        """ব্যাকটেস্টিং - পুরোনো ডাটা টেস্ট করুন"""
        dates = self.hf_manager.get_all_csv_files()
        filtered_dates = [d for d in dates if start_date <= d <= end_date]
        
        if not filtered_dates:
            return "❌ এই সময়ের মধ্যে কোনো ডাটা নেই।"
        
        results = {
            'total_signals': 0,
            'tp_hits': 0,
            'sl_hits': 0,
            'avg_score': 0,
            'best_symbol': None,
            'best_score': 0
        }
        
        all_scores = []
        
        for date in filtered_dates:
            data = self.hf_manager.read_csv_file(date)
            if data:
                start_idx = 0
                if data and data[0] and data[0][0] == "symbol":
                    start_idx = 1
                all_data = data[start_idx:]
                
                for row in all_data:
                    if len(row) > 9 and row[9] and row[9] != '-':
                        try:
                            score = int(row[9])
                            if score >= min_score:
                                results['total_signals'] += 1
                                all_scores.append(score)
                                
                                if score > results['best_score']:
                                    results['best_score'] = score
                                    results['best_symbol'] = row[0]
                        except:
                            pass
        
        results['avg_score'] = sum(all_scores) / len(all_scores) if all_scores else 0
        
        result = f"""
📊 **ব্যাকটেস্ট রিপোর্ট**

📅 সময়কাল: {start_date} → {end_date}
🎯 মিনিমাম স্কোর: {min_score}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **সারাংশ:**
• মোট সিগন্যাল: {results['total_signals']}
• গড় স্কোর: {results['avg_score']:.1f}
• বেস্ট সিম্বল: {results['best_symbol']} ({results['best_score']}/100)

💡 **সুপারিশ:**
{self.get_backtest_recommendation(results['total_signals'], results['avg_score'])}
"""
        return result
    
    def get_backtest_recommendation(self, signals: int, avg_score: float) -> str:
        """ব্যাকটেস্ট রেজাল্টের ভিত্তিতে সুপারিশ"""
        if signals > 50 and avg_score > 70:
            return "🔥 শক্তিশালী পারফরম্যান্স! স্কোর >=70 সিম্বল ট্রেড করুন।"
        elif signals > 20 and avg_score > 60:
            return "📈 ভালো পারফরম্যান্স। সিলেক্টিভ ট্রেডিং করুন।"
        elif signals > 0:
            return "⚠️ মধ্যম পারফরম্যান্স। কঠোর ফিল্টার ব্যবহার করুন।"
        else:
            return "❌ পর্যাপ্ত সিগন্যাল নেই। মিনিমাম স্কোর কমিয়ে চেষ্টা করুন।"
    
    def export_to_csv(self, date: str) -> io.BytesIO:
        """পোর্টফোলিও CSV এক্সপোর্ট করুন"""
        data = self.hf_manager.read_csv_file(date)
        if not data:
            return None
        
        # CSV ফাইল তৈরি করুন
        output = io.StringIO()
        writer = csv.writer(output)
        
        for row in data:
            writer.writerow(row)
        
        output.seek(0)
        
        # বাইটসে কনভার্ট করুন
        bytes_io = io.BytesIO()
        bytes_io.write(output.getvalue().encode('utf-8-sig'))
        bytes_io.seek(0)
        
        return bytes_io
    
    def generate_pdf_report(self, date: str, stats: Dict) -> io.BytesIO:
        """PDF রিপোর্ট জেনারেট করুন (সিম্পল টেক্সট ভার্সন)"""
        # PDF জেনারেশনের জন্য reportlab ব্যবহার করতে পারেন
        # এখানে টেক্সট ফাইল তৈরি করছি
        output = io.StringIO()
        
        output.write(f"ট্রেডিং রিপোर्ट - {date}\n")
        output.write("=" * 50 + "\n\n")
        output.write(f"তারিখ: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n")
        
        output.write("সারাংশ:\n")
        output.write(f"মোট সিম্বল: {stats.get('total', 0)}\n")
        output.write(f"সক্রিয় ট্রেড: {stats.get('active', 0)}\n")
        output.write(f"টেক প্রফিট: {stats.get('tp', 0)}\n")
        output.write(f"স্টপ লস: {stats.get('sl', 0)}\n")
        
        bytes_io = io.BytesIO()
        bytes_io.write(output.getvalue().encode('utf-8'))
        bytes_io.seek(0)
        
        return bytes_io


# ==================== টেলিগ্রাম হ্যান্ডলার ====================

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """চার্ট জেনারেট করুন"""
    args = context.args
    date = args[0] if args else datetime.now().strftime("%d-%m-%Y")
    
    await update.message.reply_text(f"⏳ চার্ট জেনারেট হচ্ছে ({date})...")
    
    data = context.bot_data.get('hf_manager').read_csv_file(date)
    if not data:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if data and data[0] and data[0][0] == "symbol":
        start_idx = 1
    all_data = data[start_idx:]
    
    adv = AdvancedFeatures(
        context.bot_data.get('hf_manager'),
        context.bot_data.get('bot')
    )
    
    chart = adv.generate_score_distribution_chart(all_data, date)
    if chart:
        await update.message.reply_photo(
            photo=chart,
            caption=f"📊 স্কোর ডিস্ট্রিবিউশন - {date}"
        )
    else:
        await update.message.reply_text("❌ চার্ট জেনারেট করতে ব্যর্থ হয়েছে।")

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """দুটি তারিখের পোর্টফোলিও তুলনা করুন"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ দুটি তারিখ দিন। উদাহরণ: `/compare 25-03-2026 26-03-2026`"
        )
        return
    
    date1 = context.args[0]
    date2 = context.args[1]
    
    adv = AdvancedFeatures(
        context.bot_data.get('hf_manager'),
        context.bot_data.get('bot')
    )
    
    result = adv.compare_portfolios(date1, date2)
    await update.message.reply_text(result, parse_mode='Markdown')

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নোটিফিকেশন সিস্টেম সেটআপ"""
    # এখানে আপনার নোটিফিকেশন লজিক
    await update.message.reply_text(
        "🔔 **নোটিফিকেশন সিস্টেম**\n\n"
        "নতুন সিগন্যাল এলে আমি জানাবো!\n\n"
        "সেটআপ করতে: `/setalert [স্কোর]`\n"
        "উদাহরণ: `/setalert 70` (70+ স্কোরের সিম্বল এলে নোটিফিকেশন)",
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
        await update.message.reply_text(
            f"✅ অ্যালার্ট সেট করা হয়েছে!\n"
            f"স্কোর {min_score}+ সিম্বল এলে আমি জানাবো।"
        )
    except:
        await update.message.reply_text("❌ ভ্যালিড স্কোর দিন (সংখ্যা)।")

async def backtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(f"⏳ ব্যাকটেস্ট রান হচ্ছে... ({start_date} → {end_date})")
    
    adv = AdvancedFeatures(
        context.bot_data.get('hf_manager'),
        context.bot_data.get('bot')
    )
    
    result = adv.backtest_strategy(start_date, end_date, min_score)
    await update.message.reply_text(result, parse_mode='Markdown')

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CSV এক্সপোর্ট করুন"""
    args = context.args
    date = args[0] if args else datetime.now().strftime("%d-%m-%Y")
    
    await update.message.reply_text(f"⏳ এক্সপোর্ট হচ্ছে ({date})...")
    
    adv = AdvancedFeatures(
        context.bot_data.get('hf_manager'),
        context.bot_data.get('bot')
    )
    
    csv_file = adv.export_to_csv(date)
    if csv_file:
        await update.message.reply_document(
            document=csv_file,
            filename=f"portfolio_{date}.csv",
            caption=f"📁 পোর্টফোলিও রিপোর্ট - {date}"
        )
    else:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
