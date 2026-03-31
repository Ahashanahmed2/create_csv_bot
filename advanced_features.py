# advanced_features.py - চার্ট, কম্পেয়ার, নোটিফিকেশন, ব্যাকটেস্ট, এক্সপোর্ট (অটো এলার্ট সহ সম্পূর্ণ আপডেটেড)

import io
import os
import csv
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# matplotlib ব্যাকএন্ড সেট করুন
plt.switch_backend('Agg')

class AdvancedFeatures:
    """অ্যাডভান্সড ফিচারস - চার্ট, কম্পেয়ার, নোটিফিকেশন, ব্যাকটেস্ট, এক্সপোর্ট"""

    def __init__(self, hf_manager=None, bot=None):
        self.hf_manager = hf_manager
        self.bot = bot
        # ইউজার অ্যালার্ট স্টোরেজ: {user_id: {'min_score': int, 'active': bool, 'created_at': datetime, 'filters': dict}}
        self.user_alerts = {}
        # প্রসেস করা সিম্বল ট্র্যাক করার জন্য: {user_id: {symbol_date: timestamp}}
        self.processed_symbols = {}
        # নোটিফিকেশন ক্যু
        self.notification_queue = asyncio.Queue()
        # ব্যাকগ্রাউন্ড টাস্ক রানিং ফ্ল্যাগ
        self.notification_task = None

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

    def compare_portfolios(self, date1: str, date2: str, hf_manager=None) -> str:
        """দুটি তারিখের পোর্টফোলিও তুলনা করুন"""
        if hf_manager is None:
            hf_manager = self.hf_manager
            
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

    def generate_weekly_report(self, dates: List[str], hf_manager=None) -> str:
        """সাপ্তাহিক রিপোর্ট জেনারেট করুন"""
        if hf_manager is None:
            hf_manager = self.hf_manager
            
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

    # ==================== অটো এলার্ট ফাংশন ====================

    def add_user_alert(self, user_id: int, min_score: int, filters: Dict = None):
        """ইউজারের অ্যালার্ট সেটিংস যোগ করুন"""
        self.user_alerts[user_id] = {
            'min_score': min_score,
            'active': True,
            'created_at': datetime.now(),
            'filters': filters or {},
            'last_notification': None
        }
        
        # ইউজারের জন্য প্রসেসড সিম্বল ট্র্যাকার ইনিশিয়ালাইজ করুন
        if user_id not in self.processed_symbols:
            self.processed_symbols[user_id] = set()

    def remove_user_alert(self, user_id: int):
        """ইউজারের অ্যালার্ট সরান"""
        if user_id in self.user_alerts:
            self.user_alerts[user_id]['active'] = False
            del self.user_alerts[user_id]

    def update_user_alert(self, user_id: int, min_score: int = None, filters: Dict = None):
        """ইউজারের অ্যালার্ট আপডেট করুন"""
        if user_id in self.user_alerts:
            if min_score is not None:
                self.user_alerts[user_id]['min_score'] = min_score
            if filters is not None:
                self.user_alerts[user_id]['filters'].update(filters)
            self.user_alerts[user_id]['updated_at'] = datetime.now()

    def get_user_alert(self, user_id: int) -> Dict:
        """ইউজারের অ্যালার্ট সেটিংস পান"""
        return self.user_alerts.get(user_id, None)

    def get_active_alerts_count(self) -> int:
        """সক্রিয় অ্যালার্টের সংখ্যা পান"""
        return len([u for u in self.user_alerts.values() if u.get('active', False)])

    def check_and_notify_new_symbols(self, new_data: List, old_data: List, date: str):
        """নতুন সিম্বল চেক করে অ্যালার্ট সক্রিয় ইউজারদের নোটিফিকেশন পাঠান"""
        if not new_data:
            return
        
        # পুরনো সিম্বল সেট
        old_symbols = set()
        old_symbols_with_score = {}
        
        for row in old_data:
            if row and len(row) > 0:
                symbol = row[0]
                old_symbols.add(symbol)
                if len(row) > 9:
                    old_symbols_with_score[symbol] = self.get_score_value(row[9])
        
        # নতুন সিম্বল চিহ্নিত করুন
        new_symbol_entries = []
        for row in new_data:
            if row and len(row) > 0 and row[0] not in old_symbols:
                score = self.get_score_value(row[9]) if len(row) > 9 else None
                wave_type = row[1] if len(row) > 1 else 'N/A'
                price = row[2] if len(row) > 2 else 'N/A'
                pattern = row[3] if len(row) > 3 else 'N/A'
                
                new_symbol_entries.append({
                    'symbol': row[0],
                    'score': score,
                    'wave_type': wave_type,
                    'price': price,
                    'pattern': pattern,
                    'row_data': row
                })
        
        if not new_symbol_entries:
            return
        
        # প্রতিটি সক্রিয় অ্যালার্টের জন্য চেক করুন
        for user_id, alert_config in self.user_alerts.items():
            if not alert_config.get('active', False):
                continue
            
            min_score = alert_config.get('min_score', 70)
            filters = alert_config.get('filters', {})
            
            # ফিল্টার অ্যাপ্লাই করুন
            relevant_symbols = []
            for sym in new_symbol_entries:
                # স্কোর ফিল্টার
                if sym['score'] is not None and sym['score'] >= min_score:
                    # ওয়েভ টাইপ ফিল্টার
                    wave_filter = filters.get('wave_type')
                    if wave_filter and wave_filter.lower() not in sym['wave_type'].lower():
                        continue
                    
                    # প্যাটার্ন ফিল্টার
                    pattern_filter = filters.get('pattern')
                    if pattern_filter and pattern_filter.lower() not in sym['pattern'].lower():
                        continue
                    
                    relevant_symbols.append(sym)
            
            if relevant_symbols:
                # কিউতে নোটিফিকেশন যোগ করুন
                asyncio.create_task(
                    self._queue_notification(user_id, relevant_symbols, date)
                )

    async def _queue_notification(self, user_id: int, symbols: List[Dict], date: str):
        """নোটিফিকেশন কিউতে যোগ করুন"""
        await self.notification_queue.put({
            'user_id': user_id,
            'symbols': symbols,
            'date': date,
            'timestamp': datetime.now()
        })

    async def _process_notification_queue(self):
        """নোটিফিকেশন কিউ প্রসেস করুন"""
        while True:
            try:
                # কিউ থেকে নোটিফিকেশন নিন
                notification = await self.notification_queue.get()
                
                user_id = notification['user_id']
                symbols = notification['symbols']
                date = notification['date']
                
                # ডুপ্লিকেট চেক করুন
                new_symbols = []
                processed_set = self.processed_symbols.get(user_id, set())
                
                for sym in symbols:
                    unique_key = f"{sym['symbol']}_{date}"
                    if unique_key not in processed_set:
                        processed_set.add(unique_key)
                        new_symbols.append(sym)
                
                self.processed_symbols[user_id] = processed_set
                
                if new_symbols:
                    # নোটিফিকেশন পাঠান
                    await self._send_notification_to_user(user_id, new_symbols, date)
                
                # কিউ টাস্ক সম্পন্ন
                self.notification_queue.task_done()
                
                # রেট লিমিট - 1 সেকেন্ড অপেক্ষা
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"নোটিফিকেশন প্রসেস করতে ব্যর্থ: {e}")
                await asyncio.sleep(5)

    async def _send_notification_to_user(self, user_id: int, symbols: List[Dict], date: str):
        """নির্দিষ্ট ইউজারকে নোটিফিকেশন পাঠান"""
        if not self.bot:
            return
        
        # সাজান এবং লিমিট
        symbols.sort(key=lambda x: x['score'] if x['score'] else 0, reverse=True)
        symbols = symbols[:15]  # সর্বোচ্চ ১৫টি সিম্বল
        
        # নোটিফিকেশন মেসেজ তৈরি করুন
        message = f"🔔 **নতুন সিম্বল এলার্ট!**\n📅 {date}\n\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for sym in symbols:
            score_emoji = "💎" if sym['score'] and sym['score'] >= 90 else \
                         "🔥" if sym['score'] and sym['score'] >= 80 else \
                         "✅" if sym['score'] and sym['score'] >= 70 else \
                         "📊" if sym['score'] and sym['score'] >= 60 else "📌"
            
            message += f"{score_emoji} **{sym['symbol']}**\n"
            message += f"   • স্কোর: {sym['score']}/100\n"
            message += f"   • ওয়েভ টাইপ: {sym['wave_type']}\n"
            
            if sym['price'] and sym['price'] != 'N/A':
                message += f"   • মূল্য: {sym['price']}\n"
            
            message += "\n"
        
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        message += "💡 `/watchlist` দেখে বিস্তারিত জানুন।\n"
        message += "⚙️ অ্যালার্ট পরিবর্তন: `/setalert [স্কোর]`"
        
        try:
            await self.bot.send_message(user_id, message, parse_mode='Markdown')
            
            # লাস্ট নোটিফিকেশন আপডেট করুন
            if user_id in self.user_alerts:
                self.user_alerts[user_id]['last_notification'] = datetime.now()
                
        except Exception as e:
            print(f"ইউজার {user_id} কে নোটিফিকেশন পাঠাতে ব্যর্থ: {e}")

    async def start_notification_worker(self):
        """নোটিফিকেশন ওয়ার্কার শুরু করুন"""
        if self.notification_task is None:
            self.notification_task = asyncio.create_task(self._process_notification_queue())

    async def stop_notification_worker(self):
        """নোটিফিকেশন ওয়ার্কার বন্ধ করুন"""
        if self.notification_task:
            self.notification_task.cancel()
            self.notification_task = None

    def get_new_symbols_from_today(self, hf_manager=None) -> List[Dict]:
        """আজকের নতুন সিম্বল পান"""
        if hf_manager is None:
            hf_manager = self.hf_manager
        
        today = datetime.now().strftime("%d-%m-%Y")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
        
        today_data = hf_manager.read_csv_file(today)
        yesterday_data = hf_manager.read_csv_file(yesterday)
        
        if not today_data or not yesterday_data:
            return []
        
        # হেডার বাদ দিন
        start_idx = 0
        if today_data and today_data[0] and today_data[0][0] == "symbol":
            start_idx = 1
        today_content = today_data[start_idx:]
        
        start_idx = 0
        if yesterday_data and yesterday_data[0] and yesterday_data[0][0] == "symbol":
            start_idx = 1
        yesterday_content = yesterday_data[start_idx:]
        
        yesterday_symbols = set([row[0] for row in yesterday_content if row])
        new_symbols = []
        
        for row in today_content:
            if row and row[0] not in yesterday_symbols:
                score = self.get_score_value(row[9]) if len(row) > 9 else None
                wave_type = row[1] if len(row) > 1 else 'N/A'
                price = row[2] if len(row) > 2 else 'N/A'
                pattern = row[3] if len(row) > 3 else 'N/A'
                
                new_symbols.append({
                    'symbol': row[0],
                    'score': score,
                    'wave_type': wave_type,
                    'price': price,
                    'pattern': pattern
                })
        
        return new_symbols


# ==================== টেলিগ্রাম হ্যান্ডলার ====================

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """চার্ট জেনারেট করুন"""
    args = context.args
    date = args[0] if args else datetime.now().strftime("%d-%m-%Y")
    
    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')

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

    chart = advanced_features.generate_score_distribution_chart(all_data, date)
    
    if chart:
        await update.message.reply_photo(
            photo=chart,
            caption=f"📊 স্কোর ডিস্ট্রিবিউশন - {date}\nমোট সিম্বল: {len(all_data)}"
        )
    else:
        await update.message.reply_text("❌ চার্ট জেনারেট করতে ব্যর্থ হয়েছে। পর্যাপ্ত ডাটা নেই।")

async def compare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """দুটি তারিখের পোর্টফোলিও তুলনা করুন"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ দুটি তারিখ দিন। উদাহরণ: `/compare 25-03-2026 26-03-2026`"
        )
        return

    date1 = context.args[0]
    date2 = context.args[1]
    
    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')
    
    result = advanced_features.compare_portfolios(date1, date2, hf_manager)
    
    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(result, parse_mode='Markdown')

async def setalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যালার্ট সেট করুন - অটো নোটিফিকেশন"""
    advanced_features = context.bot_data.get('advanced_features')
    
    if not context.args:
        help_text = (
            "🔔 **অটো এলার্ট সেটআপ**\n\n"
            "নতুন সিম্বল এন্ট্রি হলে স্বয়ংক্রিয়ভাবে নোটিফিকেশন পাবেন।\n\n"
            "**ব্যবহার:**\n"
            "• `/setalert 70` - 70+ স্কোরের সিম্বল এলে নোটিফিকেশন\n"
            "• `/setalert 80 wave:impulse` - ইম্পালস ওয়েভের 80+ স্কোর\n"
            "• `/setalert 60 pattern:bullish` - বুলিশ প্যাটার্নের 60+ স্কোর\n\n"
            "**ফিল্টার অপশন:**\n"
            "• `wave:impulse` - শুধু ইম্পালস ওয়েভ\n"
            "• `wave:corrective` - শুধু করেকটিভ ওয়েভ\n"
            "• `pattern:bullish` - বুলিশ প্যাটার্ন\n"
            "• `pattern:bearish` - বিয়ারিশ প্যাটার্ন\n\n"
            "🛑 বন্ধ করতে: `/stopalert`\n"
            "📋 দেখতে: `/myalerts`"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')
        return

    try:
        # প্যারামিটার পার্স করুন
        min_score = None
        filters = {}
        
        for arg in context.args:
            if ':' in arg:
                key, value = arg.split(':', 1)
                filters[key] = value
            else:
                try:
                    min_score = int(arg)
                except:
                    pass
        
        if min_score is None:
            min_score = 70
            
        if min_score < 0 or min_score > 100:
            await update.message.reply_text("❌ স্কোর 0-100 এর মধ্যে হতে হবে।")
            return
        
        user_id = update.effective_user.id
        advanced_features.add_user_alert(user_id, min_score, filters)
        
        # নোটিফিকেশন ওয়ার্কার শুরু করুন (যদি না শুরু থাকে)
        await advanced_features.start_notification_worker()
        
        message = f"✅ **অটো এলার্ট সক্রিয় করা হয়েছে!**\n\n"
        message += f"📊 মিনিমাম স্কোর: {min_score}+\n"
        
        if filters:
            message += f"🎯 ফিল্টার:\n"
            for key, value in filters.items():
                message += f"   • {key}: {value}\n"
        
        message += f"\n🔔 নতুন সিম্বল এন্ট্রি হলে আমি আপনাকে জানাবো।\n"
        message += f"🛑 বন্ধ করতে: `/stopalert`\n"
        message += f"📋 পরিবর্তন করতে: `/setalert [নতুন স্কোর]`\n\n"
        message += f"💡 **টিপ:** উচ্চ স্কোরের সিম্বল পেতে 70+ ব্যবহার করুন।"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ অ্যালার্ট সেট করতে ব্যর্থ: {str(e)}")

async def stopalert_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যালার্ট বন্ধ করুন"""
    advanced_features = context.bot_data.get('advanced_features')
    
    user_id = update.effective_user.id
    alert = advanced_features.get_user_alert(user_id)
    
    if alert:
        advanced_features.remove_user_alert(user_id)
        await update.message.reply_text(
            "✅ **অটো এলার্ট বন্ধ করা হয়েছে!**\n\n"
            "আবার চালু করতে: `/setalert [স্কোর]`\n\n"
            "📌 **মনে রাখবেন:** বন্ধ করার পর নতুন সিম্বল এন্ট্রি হলে আর নোটিফিকেশন পাবেন না।",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "🔕 **আপনার কোনো সক্রিয় অ্যালার্ট নেই**\n\n"
            "অ্যালার্ট সেট করতে: `/setalert 70`",
            parse_mode='Markdown'
        )

async def myalerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সক্রিয় অ্যালার্ট লিস্ট দেখান"""
    advanced_features = context.bot_data.get('advanced_features')
    
    user_id = update.effective_user.id
    alert = advanced_features.get_user_alert(user_id)
    
    if alert:
        message = f"🔔 **আপনার সক্রিয় অ্যালার্ট**\n\n"
        message += f"📊 মিনিমাম স্কোর: {alert['min_score']}+\n"
        
        if alert.get('filters'):
            message += f"🎯 ফিল্টার:\n"
            for key, value in alert['filters'].items():
                message += f"   • {key}: {value}\n"
        
        message += f"\n📅 সেট করার সময়: {alert['created_at'].strftime('%d-%m-%Y %H:%M:%S')}\n"
        
        if alert.get('last_notification'):
            message += f"🔔 শেষ নোটিফিকেশন: {alert['last_notification'].strftime('%d-%m-%Y %H:%M:%S')}\n"
        
        message += f"\n🛑 বন্ধ করতে: `/stopalert`\n"
        message += f"✏️ পরিবর্তন করতে: `/setalert [নতুন স্কোর]`"
    else:
        message = (
            "🔕 **কোনো সক্রিয় অ্যালার্ট নেই**\n\n"
            "📌 অ্যালার্ট সেট করতে: `/setalert [স্কোর]`\n"
            "উদাহরণ: `/setalert 70`\n\n"
            "📋 বিস্তারিত জানতে: `/setalert`"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

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

    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')

    await update.message.reply_text(f"⏳ ব্যাকটেস্ট রান হচ্ছে... ({start_date} → {end_date})")

    result = advanced_features.backtest_strategy(start_date, end_date, min_score, hf_manager)
    
    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(result, parse_mode='Markdown')

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CSV এক্সপোর্ট করুন"""
    args = context.args
    date = args[0] if args else datetime.now().strftime("%d-%m-%Y")

    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')

    await update.message.reply_text(f"⏳ এক্সপোর্ট হচ্ছে ({date})...")

    csv_file = advanced_features.export_to_csv(date)
    
    if csv_file:
        await update.message.reply_document(
            document=csv_file,
            filename=f"portfolio_{date}.csv",
            caption=f"📁 পোর্টফোলিও রিপোর্ট - {date}\n📅 এক্সপোর্ট সময়: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        )
    else:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")

async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সাপ্তাহিক রিপোর্ট দেখান"""
    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')
    
    dates = hf_manager.get_all_csv_files()
    if len(dates) < 5:
        await update.message.reply_text("❌ সাপ্তাহিক রিপোর্টের জন্য পর্যাপ্ত ডাটা নেই।")
        return
    
    last_7_days = dates[:7]
    result = advanced_features.generate_weekly_report(last_7_days, hf_manager)
    
    await update.message.reply_text(result, parse_mode='Markdown')

async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নতুন সিম্বল ওয়াচলিস্ট দেখান"""
    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')
    
    await update.message.reply_text("⏳ ওয়াচলিস্ট লোড হচ্ছে...")
    
    new_symbols = advanced_features.get_new_symbols_from_today(hf_manager)
    
    if not new_symbols:
        await update.message.reply_text(f"📭 আজকে কোনো নতুন সিম্বল নেই।")
        return
    
    # সাজান এবং দেখান
    new_symbols.sort(key=lambda x: x['score'] if x['score'] else 0, reverse=True)
    
    message = f"🆕 **নতুন সিম্বল ({datetime.now().strftime('%d-%m-%Y')})**\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for sym in new_symbols[:20]:
        score_emoji = "💎" if sym['score'] and sym['score'] >= 90 else \
                     "🔥" if sym['score'] and sym['score'] >= 80 else \
                     "✅" if sym['score'] and sym['score'] >= 70 else \
                     "📊" if sym['score'] and sym['score'] >= 60 else "📌"
        
        score_text = f"{sym['score']}/100" if sym['score'] else "N/A"
        message += f"{score_emoji} **{sym['symbol']}**\n"
        message += f"   • স্কোর: {score_text}\n"
        message += f"   • ওয়েভ টাইপ: {sym['wave_type']}\n"
        
        if sym['price'] and sym['price'] != 'N/A':
            message += f"   • মূল্য: {sym['price']}\n"
        
        message += "\n"
    
    if len(new_symbols) > 20:
        message += f"📌 এবং আরও {len(new_symbols) - 20}টি সিম্বল...\n"
    
    message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "💡 অটো এলার্ট সেট করতে: `/setalert 70`\n"
    message += "🔔 নোটিফিকেশন পেতে: `/setalert`"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যাডভান্সড স্ট্যাটিস্টিক্স দেখান"""
    hf_manager = context.bot_data.get('hf_manager')
    advanced_features = context.bot_data.get('advanced_features')
    
    date = datetime.now().strftime("%d-%m-%Y")
    data = hf_manager.read_csv_file(date)
    
    if not data:
        await update.message.reply_text(f"❌ {date}.csv ফাইল পাওয়া যায়নি।")
        return
    
    start_idx = 0
    if data and data[0] and len(data[0]) > 0 and data[0][0] == "symbol":
        start_idx = 1
    all_data = data[start_idx:]
    
    stats = advanced_features.calculate_portfolio_stats(all_data)
    
    message = f"""
📊 **পোর্টফোলিও স্ট্যাটিস্টিক্স** - {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **মেট্রিক্স:**
• মোট সিম্বল: {stats['total']}
• গড় স্কোর: {stats['avg_score']:.1f}/100
• মধ্যমা স্কোর: {stats['median_score']:.1f}/100
• সর্বোচ্চ স্কোর: {stats['max_score']}
• সর্বনিম্ন স্কোর: {stats['min_score']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **স্কোর ডিস্ট্রিবিউশন:**
• 💎 90+: {len([s for s in [stats['strong_count']] if s >= 90])}
• 🔥 80-89: {stats['strong_count'] - len([s for s in [stats['strong_count']] if s >= 90])}
• ✅ 70-79: {stats['strong_count'] - (stats['strong_count'] - stats['good_count'])}
• 📊 60-69: {stats['good_count']}
• ⚠️ 50-59: {stats['medium_count']}
• ❌ 40-49: {stats['weak_count']}
• 🚫 <40: {stats['very_weak_count']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **ওয়েভ টাইপ:**
• ইম্পালস: {stats['impulse_count']}
• করেকটিভ: {stats['corrective_count']}
• রেশিও: {stats['impulse_count']/stats['corrective_count'] if stats['corrective_count'] > 0 else 0:.2f}

🏆 **টপ সিম্বল:**
{chr(10).join([f"  • {sym}" for sym in stats['high_score_symbols'][:5]]) if stats['high_score_symbols'] else '  • নেই'}

💡 **সুপারিশ:**
{self.get_market_recommendation(stats)}
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')

def get_market_recommendation(stats: Dict) -> str:
    """মার্কেট রিকমেন্ডেশন"""
    if stats['avg_score'] >= 70:
        return "🔥 মার্কেট শক্তিশালী। ট্রেডিং চালিয়ে যান।"
    elif stats['avg_score'] >= 60:
        return "📈 মার্কেট মধ্যম। সিলেক্টিভ ট্রেডিং করুন।"
    elif stats['avg_score'] >= 50:
        return "⚠️ মার্কেট দুর্বল। রিস্ক ম্যানেজ করুন।"
    else:
        return "❌ মার্কেট খুব দুর্বল। ক্যাশে থাকুন।"

# এক্সপোর্ট করার জন্য ফাংশন
__all__ = [
    'AdvancedFeatures',
    'chart_command',
    'compare_command',
    'setalert_command',
    'stopalert_command',
    'myalerts_command',
    'backtest_command',
    'export_command',
    'weekly_command',
    'watchlist_command',
    'stats_command'
]