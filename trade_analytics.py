# trade_analytics.py - Complete Updated Version (Auto-create files on first run)

import os
import csv
from datetime import datetime
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes


class TradeAnalytics:
    """ট্রেডিং অ্যানালাইটিক্স - ইনলাইন বাটন ও কার্ড ভিউ সমর্থন করে"""

    def __init__(self, data_dir="./csv"):
        self.data_dir = data_dir
        self.stock_dir = os.path.join(data_dir, "stock")
        
        # Trade files in stock folder
        self.ed_file = os.path.join(self.stock_dir, "ed.csv")
        self.rd_file = os.path.join(self.stock_dir, "rd.csv")
        self.sl_file = os.path.join(self.stock_dir, "sl.csv")
        self.tp_file = os.path.join(self.stock_dir, "tp.csv")
        
        # Create directories and files on first run
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage - create folders and files on first run"""
        # Create stock folder if not exists
        os.makedirs(self.stock_dir, exist_ok=True)
        print(f"✅ Stock folder ready: {self.stock_dir}")
        
        # Create trade files with headers if they don't exist
        self._ensure_csv_files()
        
        # Download daily stock data from HF if available
        self._download_daily_stock_data()

    def _ensure_csv_files(self):
        """Create CSV files with headers if not exist (first run only)"""
        headers = {
            self.rd_file: ['symbol', 'wave', 'subwave', 'entry', 'stop', 'tp1', 'tp2', 'tp3', 'rrr', 'score', 'insight'],
            self.ed_file: ['symbol', 'wave', 'subwave', 'entry', 'stop', 'tp1', 'tp2', 'tp3', 'rrr', 'score', 'insight', 'entry_date'],
            self.sl_file: ['symbol', 'wave', 'subwave', 'entry', 'stop', 'tp1', 'tp2', 'tp3', 'rrr', 'score', 'insight', 'sl_date'],
            self.tp_file: ['symbol', 'wave', 'subwave', 'entry', 'stop', 'tp1', 'tp2', 'tp3', 'rrr', 'score', 'insight', 'tp1_date', 'tp1_gap', 'tp2_date', 'tp2_gap', 'tp3_date', 'tp3_gap']
        }
        
        created_count = 0
        for filepath, header in headers.items():
            if not os.path.exists(filepath):
                try:
                    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                    print(f"✅ Created: {os.path.basename(filepath)}")
                    created_count += 1
                except Exception as e:
                    print(f"⚠️ Could not create {filepath}: {e}")
        
        if created_count > 0:
            print(f"📋 Created {created_count} new trade files")
        else:
            print(f"📋 All trade files already exist")

    def _download_daily_stock_data(self):
        """Download daily stock data from Hugging Face"""
        try:
            from huggingface_hub import hf_hub_download
            from dotenv import load_dotenv
            
            load_dotenv()
            HF_TOKEN = os.getenv("hf_token")
            REPO_ID = "ahashanahmed/csv"
            
            # Try to download today's stock file
            today = datetime.now().strftime('%d-%m-%Y')
            stock_file = f"stock/{today}.csv"
            
            try:
                hf_hub_download(
                    repo_id=REPO_ID,
                    filename=stock_file,
                    repo_type="dataset",
                    token=HF_TOKEN,
                    local_dir="./csv",
                    local_dir_use_symlinks=False
                )
                print(f"✅ Downloaded daily stock data: {stock_file}")
            except Exception as e:
                print(f"⚠️ No daily stock data for {today}: {e}")
                
        except ImportError:
            print("⚠️ huggingface_hub not installed, skipping daily stock download")
        except Exception as e:
            print(f"⚠️ Could not download daily stock data: {e}")

    def read_csv_file(self, filepath: str) -> Optional[List[List[str]]]:
        """CSV ফাইল পড়ুন"""
        try:
            if not os.path.exists(filepath):
                return None
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                return list(reader)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None

    def write_csv_file(self, filepath: str, data: List[List[str]]):
        """CSV ফাইল লিখুন"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False

    def add_trade(self, trade_data: Dict, file_type: str):
        """নতুন ট্রেড যোগ করুন (ed, rd, sl, tp)"""
        file_map = {
            'ed': self.ed_file,
            'rd': self.rd_file,
            'sl': self.sl_file,
            'tp': self.tp_file
        }
        
        filepath = file_map.get(file_type)
        if not filepath:
            return False
        
        data = self.read_csv_file(filepath)
        if not data:
            return False
        
        # Get header and create new row
        header = data[0]
        new_row = []
        for col in header:
            new_row.append(trade_data.get(col, ""))
        
        data.append(new_row)
        return self.write_csv_file(filepath, data)

    def get_score_emoji(self, score: str) -> str:
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

    def get_score_text(self, score: str) -> str:
        """স্কোর অনুযায়ী টেক্সট"""
        try:
            score_num = int(score)
            if score_num >= 85:
                return "এক্সট্রিম শক্তিশালী"
            elif score_num >= 80:
                return "খুব শক্তিশালী"
            elif score_num >= 70:
                return "শক্তিশালী"
            elif score_num >= 60:
                return "ভাল"
            elif score_num >= 50:
                return "মধ্যম"
            elif score_num >= 40:
                return "দুর্বল"
            else:
                return "খুব দুর্বল"
        except:
            return "সাধারণ"

    def format_stock_card(self, stock: Dict, serial: int) -> str:
        """স্টক কার্ড ফরম্যাট করুন"""
        score_emoji = self.get_score_emoji(stock['score'])
        score_text = self.get_score_text(stock['score'])

        wave = stock.get('wave', '-')
        subwave = stock.get('subwave', '')
        if subwave and subwave != '-':
            wave_display = f"{wave} → {subwave}"
        else:
            wave_display = wave

        insight = stock.get('insight', 'কোনো ইনসাইট নেই')
        insight_lines = []
        for j in range(0, len(insight), 70):
            insight_lines.append(insight[j:j+70])

        card = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ #{serial} {stock['symbol']} {score_emoji}
╠══════════════════════════════════════════════════════════════════════════════╣
║ 🌊 ওয়েভ    : {wave_display}
║ 📈 এন্ট্রি  : {stock.get('entry', '-')}  |  🛑 স্টপ: {stock.get('stop', '-')}
║ 🎯 টার্গেট  : {stock.get('tp1', '-')} → {stock.get('tp2', '-')} → {stock.get('tp3', '-')}  |  📊 RRR: {stock.get('rrr', '-')}
║ 🏆 স্কোর    : {stock['score']}/100 {score_emoji}  |  {score_text}
║ 💡 ইনসাইট  : {insight_lines[0] if insight_lines else insight}"""

        for line in insight_lines[1:]:
            card += f"""
║              {line}"""

        card += """
╚══════════════════════════════════════════════════════════════════════════════╝"""
        return card

    def get_active_trades(self) -> List[Dict]:
        """সক্রিয় ট্রেড লিস্ট"""
        data = self.read_csv_file(self.rd_file)
        if not data or len(data) <= 1:
            return []

        active_trades = []
        for row in data[1:]:
            if row and len(row) >= 11:
                active_trades.append({
                    'symbol': row[0],
                    'wave': row[1] if len(row) > 1 else "-",
                    'subwave': row[2] if len(row) > 2 else "",
                    'entry': row[3] if len(row) > 3 else "-",
                    'stop': row[4] if len(row) > 4 else "-",
                    'tp1': row[5] if len(row) > 5 else "-",
                    'tp2': row[6] if len(row) > 6 else "-",
                    'tp3': row[7] if len(row) > 7 else "-",
                    'rrr': row[8] if len(row) > 8 else "-",
                    'score': row[9] if len(row) > 9 else "-",
                    'insight': row[10] if len(row) > 10 else "কোনো ইনসাইট নেই"
                })
        return active_trades

    def get_tp_list(self) -> List[Dict]:
        """টেক প্রফিট লিস্ট"""
        tp_data = self.read_csv_file(self.tp_file)
        if not tp_data or len(tp_data) <= 1:
            return []

        tp_list = []
        for row in tp_data[1:]:
            if row and len(row) > 0:
                tp_item = {
                    'symbol': row[0],
                    'wave': row[1] if len(row) > 1 else "-",
                    'subwave': row[2] if len(row) > 2 else "",
                    'entry': row[3] if len(row) > 3 else "-",
                    'stop': row[4] if len(row) > 4 else "-",
                    'tp1': row[5] if len(row) > 5 else "-",
                    'tp2': row[6] if len(row) > 6 else "-",
                    'tp3': row[7] if len(row) > 7 else "-",
                    'rrr': row[8] if len(row) > 8 else "-",
                    'score': row[9] if len(row) > 9 else "-",
                    'insight': row[10] if len(row) > 10 else "কোনো ইনসাইট নেই",
                    'tp_level': 0,
                    'tp_date': ""
                }

                if len(row) > 17 and row[17] and row[17] != '':
                    tp_item['tp_level'] = 3
                    tp_item['tp_date'] = row[17]
                elif len(row) > 15 and row[15] and row[15] != '':
                    tp_item['tp_level'] = 2
                    tp_item['tp_date'] = row[15]
                elif len(row) > 13 and row[13] and row[13] != '':
                    tp_item['tp_level'] = 1
                    tp_item['tp_date'] = row[13]

                if tp_item['tp_level'] > 0:
                    tp_list.append(tp_item)

        tp_list.sort(key=lambda x: x['tp_date'], reverse=True)
        return tp_list

    def get_sl_list(self) -> List[Dict]:
        """স্টপ লস লিস্ট"""
        sl_data = self.read_csv_file(self.sl_file)
        if not sl_data or len(sl_data) <= 1:
            return []

        sl_list = []
        for row in sl_data[1:]:
            if row and len(row) > 0:
                sl_list.append({
                    'symbol': row[0],
                    'wave': row[1] if len(row) > 1 else "-",
                    'subwave': row[2] if len(row) > 2 else "",
                    'entry': row[3] if len(row) > 3 else "-",
                    'stop': row[4] if len(row) > 4 else "-",
                    'tp1': row[5] if len(row) > 5 else "-",
                    'tp2': row[6] if len(row) > 6 else "-",
                    'tp3': row[7] if len(row) > 7 else "-",
                    'rrr': row[8] if len(row) > 8 else "-",
                    'score': row[9] if len(row) > 9 else "-",
                    'insight': row[10] if len(row) > 10 else "কোনো ইনসাইট নেই",
                    'sl_date': row[13] if len(row) > 13 else "-"
                })

        sl_list.sort(key=lambda x: x['sl_date'], reverse=True)
        return sl_list

    def get_wave_stats(self) -> Dict:
        """ওয়েভ স্ট্যাটিস্টিক্স"""
        tp_data = self.read_csv_file(self.tp_file)
        sl_data = self.read_csv_file(self.sl_file)

        stats = {
            'impulse': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []},
            'corrective': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []}
        }

        if tp_data and len(tp_data) > 1:
            for row in tp_data[1:]:
                if row and len(row) > 1:
                    wave = row[1].lower() if len(row) > 1 else ""
                    if 'impulse' in wave:
                        stats['impulse']['tp'] += 1
                        stats['impulse']['tp_symbols'].append(row[0])
                    elif 'corrective' in wave:
                        stats['corrective']['tp'] += 1
                        stats['corrective']['tp_symbols'].append(row[0])

        if sl_data and len(sl_data) > 1:
            for row in sl_data[1:]:
                if row and len(row) > 1:
                    wave = row[1].lower() if len(row) > 1 else ""
                    if 'impulse' in wave:
                        stats['impulse']['sl'] += 1
                        stats['impulse']['sl_symbols'].append(row[0])
                    elif 'corrective' in wave:
                        stats['corrective']['sl'] += 1
                        stats['corrective']['sl_symbols'].append(row[0])

        return stats

    def get_gap_stats(self) -> Dict:
        """গ্যাপ স্ট্যাটিস্টিক্স"""
        tp_data = self.read_csv_file(self.tp_file)
        sl_data = self.read_csv_file(self.sl_file)

        stats = {
            '0-5': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []},
            '6-10': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []},
            '11-15': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []},
            '16-30': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []},
            '30+': {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []}
        }

        if tp_data and len(tp_data) > 1:
            for row in tp_data[1:]:
                gap = 0
                for i in [14, 16, 18]:
                    if len(row) > i and row[i] and row[i] != '':
                        try:
                            gap = int(row[i])
                            break
                        except:
                            pass

                if gap <= 5:
                    stats['0-5']['tp'] += 1
                    stats['0-5']['tp_symbols'].append(row[0])
                elif gap <= 10:
                    stats['6-10']['tp'] += 1
                    stats['6-10']['tp_symbols'].append(row[0])
                elif gap <= 15:
                    stats['11-15']['tp'] += 1
                    stats['11-15']['tp_symbols'].append(row[0])
                elif gap <= 30:
                    stats['16-30']['tp'] += 1
                    stats['16-30']['tp_symbols'].append(row[0])
                else:
                    stats['30+']['tp'] += 1
                    stats['30+']['tp_symbols'].append(row[0])

        if sl_data and len(sl_data) > 1:
            for row in sl_data[1:]:
                try:
                    gap = int(row[14]) if len(row) > 14 and row[14] else 0
                except:
                    gap = 0

                if gap <= 5:
                    stats['0-5']['sl'] += 1
                    stats['0-5']['sl_symbols'].append(row[0])
                elif gap <= 10:
                    stats['6-10']['sl'] += 1
                    stats['6-10']['sl_symbols'].append(row[0])
                elif gap <= 15:
                    stats['11-15']['sl'] += 1
                    stats['11-15']['sl_symbols'].append(row[0])
                elif gap <= 30:
                    stats['16-30']['sl'] += 1
                    stats['16-30']['sl_symbols'].append(row[0])
                else:
                    stats['30+']['sl'] += 1
                    stats['30+']['sl_symbols'].append(row[0])

        return stats

    def get_tp_level_stats(self) -> Dict:
        """টিপি লেভেল স্ট্যাটিস্টিক্স"""
        tp_data = self.read_csv_file(self.tp_file)

        stats = {
            'tp1': {'count': 0, 'symbols': [], 'symbols_detail': []},
            'tp2': {'count': 0, 'symbols': [], 'symbols_detail': []},
            'tp3': {'count': 0, 'symbols': [], 'symbols_detail': []}
        }

        if tp_data and len(tp_data) > 1:
            for row in tp_data[1:]:
                if row and len(row) > 0:
                    if len(row) > 13 and row[13] and row[13] != '':
                        stats['tp1']['count'] += 1
                        stats['tp1']['symbols'].append(row[0])
                        stats['tp1']['symbols_detail'].append({
                            'symbol': row[0],
                            'score': row[9] if len(row) > 9 else "-"
                        })

                    if len(row) > 15 and row[15] and row[15] != '':
                        stats['tp2']['count'] += 1
                        stats['tp2']['symbols'].append(row[0])
                        stats['tp2']['symbols_detail'].append({
                            'symbol': row[0],
                            'score': row[9] if len(row) > 9 else "-"
                        })

                    if len(row) > 17 and row[17] and row[17] != '':
                        stats['tp3']['count'] += 1
                        stats['tp3']['symbols'].append(row[0])
                        stats['tp3']['symbols_detail'].append({
                            'symbol': row[0],
                            'score': row[9] if len(row) > 9 else "-"
                        })

        return stats

    def get_score_stats(self) -> Dict:
        """স্কোর স্ট্যাটিস্টিক্স"""
        tp_data = self.read_csv_file(self.tp_file)
        sl_data = self.read_csv_file(self.sl_file)

        stats = {
            'excellent': {'range': '85-100', 'tp': 0, 'sl': 0},
            'very_strong': {'range': '80-84', 'tp': 0, 'sl': 0},
            'strong': {'range': '70-79', 'tp': 0, 'sl': 0},
            'good': {'range': '60-69', 'tp': 0, 'sl': 0},
            'medium': {'range': '50-59', 'tp': 0, 'sl': 0},
            'weak': {'range': '40-49', 'tp': 0, 'sl': 0},
            'very_weak': {'range': '0-39', 'tp': 0, 'sl': 0}
        }

        def get_range(score_str):
            try:
                score = int(score_str)
                if score >= 85:
                    return 'excellent'
                elif score >= 80:
                    return 'very_strong'
                elif score >= 70:
                    return 'strong'
                elif score >= 60:
                    return 'good'
                elif score >= 50:
                    return 'medium'
                elif score >= 40:
                    return 'weak'
                else:
                    return 'very_weak'
            except:
                return 'medium'

        if tp_data and len(tp_data) > 1:
            for row in tp_data[1:]:
                if len(row) > 9:
                    score_range = get_range(row[9])
                    stats[score_range]['tp'] += 1

        if sl_data and len(sl_data) > 1:
            for row in sl_data[1:]:
                if len(row) > 9:
                    score_range = get_range(row[9])
                    stats[score_range]['sl'] += 1

        return stats


# ==================== Global Instance ====================
trade_analytics = TradeAnalytics()


# ==================== INLINE KEYBOARDS ====================

def get_main_keyboard():
    """মূল মেনু কীবোর্ড"""
    keyboard = [
        [
            InlineKeyboardButton("📊 পারফরম্যান্স", callback_data="perf_main"),
            InlineKeyboardButton("📈 সক্রিয় ট্রেড", callback_data="active_list_1")
        ],
        [
            InlineKeyboardButton("✅ টেক প্রফিট", callback_data="tp_list_1"),
            InlineKeyboardButton("❌ স্টপ লস", callback_data="sl_list_1")
        ],
        [
            InlineKeyboardButton("🌊 ওয়েভ অ্যানালাইসিস", callback_data="wave_menu"),
            InlineKeyboardButton("⏱️ গ্যাপ অ্যানালাইসিস", callback_data="gap_menu")
        ],
        [
            InlineKeyboardButton("🎯 টিপি লেভেল", callback_data="tp_level_menu"),
            InlineKeyboardButton("⭐ স্কোর অ্যানালাইসিস", callback_data="score_menu")
        ],
        [
            InlineKeyboardButton("📋 সম্পূর্ণ রিপোর্ট", callback_data="full_report"),
            InlineKeyboardButton("🔍 সিম্বল সার্চ", callback_data="search_symbol")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wave_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🌊 ইম্পালস ওয়েভ", callback_data="wave_impulse"),
            InlineKeyboardButton("📉 করেকটিভ ওয়েভ", callback_data="wave_corrective")
        ],
        [
            InlineKeyboardButton("📊 ওয়েভ কম্পেয়ার", callback_data="wave_compare"),
            InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_gap_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("0-5 দিন", callback_data="gap_0-5"),
            InlineKeyboardButton("6-10 দিন", callback_data="gap_6-10")
        ],
        [
            InlineKeyboardButton("11-15 দিন", callback_data="gap_11-15"),
            InlineKeyboardButton("16-30 দিন", callback_data="gap_16-30")
        ],
        [
            InlineKeyboardButton("30+ দিন", callback_data="gap_30+"),
            InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tp_level_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎯 TP1", callback_data="tp_level_1"),
            InlineKeyboardButton("🎯 TP2", callback_data="tp_level_2"),
            InlineKeyboardButton("🎯 TP3", callback_data="tp_level_3")
        ],
        [
            InlineKeyboardButton("📊 TP কম্পেয়ার", callback_data="tp_level_compare"),
            InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_score_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("💎 85-100", callback_data="score_excellent"),
            InlineKeyboardButton("🔥 80-84", callback_data="score_very_strong")
        ],
        [
            InlineKeyboardButton("⭐ 70-79", callback_data="score_strong"),
            InlineKeyboardButton("✅ 60-69", callback_data="score_good")
        ],
        [
            InlineKeyboardButton("📈 50-59", callback_data="score_medium"),
            InlineKeyboardButton("⚠️ 40-49", callback_data="score_weak")
        ],
        [
            InlineKeyboardButton("❌ 0-39", callback_data="score_very_weak"),
            InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== SYMBOL DETAIL HANDLERS ====================

async def show_symbol_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সিম্বল ডিটেইল দেখান - কার্ড স্টাইলে"""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split('_')

    if len(parts) < 3:
        await query.edit_message_text("❌ Invalid request")
        return

    symbol = parts[1]
    list_type = parts[2]  # active, tp, sl

    if list_type == "active":
        trades = trade_analytics.get_active_trades()
        found = [t for t in trades if t['symbol'] == symbol]
    elif list_type == "tp":
        tp_list = trade_analytics.get_tp_list()
        found = [t for t in tp_list if t['symbol'] == symbol]
    elif list_type == "sl":
        sl_list = trade_analytics.get_sl_list()
        found = [s for s in sl_list if s['symbol'] == symbol]
    else:
        found = []

    if not found:
        await query.edit_message_text(f"❌ '{symbol}' সিম্বলটি পাওয়া যায়নি।")
        return

    stock = found[0]
    result = trade_analytics.format_stock_card(stock, 1)

    if list_type == "tp" and stock.get('tp_level'):
        result += f"\n🎯 **TP{stock['tp_level']} হিট**\n"
    elif list_type == "sl" and stock.get('sl_date'):
        result += f"\n🛑 **স্টপ লস হিট**: {stock['sl_date']}\n"

    keyboard = [[InlineKeyboardButton("◀️ লিস্টে ফিরুন", callback_data=f"back_to_{list_type}")]]
    await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """লিস্টে ফিরে যান"""
    query = update.callback_query
    await query.answer()

    list_type = query.data.replace("back_to_", "")

    if list_type == "active":
        await show_active_trades(query, 1)
    elif list_type == "tp":
        await show_tp_list(query, 1)
    elif list_type == "sl":
        await show_sl_list(query, 1)
    else:
        await query.edit_message_text(
            "📊 **ট্রেডিং অ্যানালাইটিক্স মেনু**\n\nনিচের বাটন থেকে আপনার পছন্দের অপশন নির্বাচন করুন:",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )


# ==================== LIST DISPLAY FUNCTIONS ====================

async def show_active_trades(query, page: int = 1, items_per_page: int = 3):
    """সক্রিয় ট্রেড দেখান - সিম্বল বাটন সহ"""
    trades = trade_analytics.get_active_trades()

    if not trades:
        await query.edit_message_text(
            "📭 **সক্রিয় ট্রেড** - কোনো ট্রেড নেই।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")]]),
            parse_mode='Markdown'
        )
        return

    total = len(trades)
    total_pages = (total + items_per_page - 1) // items_per_page
    if page > total_pages:
        page = total_pages

    start = (page - 1) * items_per_page
    end = min(start + items_per_page, total)
    page_trades = trades[start:end]

    result = f"📈 **সক্রিয় ট্রেড**  |  📋 {total} টি  |  📄 পৃষ্ঠা {page}/{total_pages}\n\n"
    keyboard = []

    for i, trade in enumerate(page_trades):
        serial = start + i + 1
        keyboard.append([InlineKeyboardButton(
            f"#{serial} {trade['symbol']} {trade_analytics.get_score_emoji(trade['score'])}", 
            callback_data=f"symdetail_{trade['symbol']}_active"
        )])
        result += f"`{serial}. {trade['symbol']}` → ওয়েভ: {trade['wave']} | স্কোর: {trade['score']}/100\n"

    result += "\n💡 **সিম্বলে ক্লিক করুন বিস্তারিত দেখতে**"

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ পূর্ববর্তী", callback_data=f"active_list_page_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("পরবর্তী ▶️", callback_data=f"active_list_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("◀️ মেনুতে ফিরুন", callback_data="back_main")])

    await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def show_tp_list(query, page: int = 1, items_per_page: int = 3):
    """টেক প্রফিট লিস্ট দেখান - সিম্বল বাটন সহ"""
    tp_list = trade_analytics.get_tp_list()

    if not tp_list:
        await query.edit_message_text(
            "📭 **টেক প্রফিট লিস্ট** - কোনো টিপি রেকর্ড নেই।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")]]),
            parse_mode='Markdown'
        )
        return

    total = len(tp_list)
    total_pages = (total + items_per_page - 1) // items_per_page
    if page > total_pages:
        page = total_pages

    start = (page - 1) * items_per_page
    end = min(start + items_per_page, total)
    page_tps = tp_list[start:end]

    result = f"✅ **টেক প্রফিট লিস্ট**  |  📋 {total} টি  |  📄 পৃষ্ঠা {page}/{total_pages}\n\n"
    keyboard = []

    for i, tp in enumerate(page_tps):
        serial = start + i + 1
        keyboard.append([InlineKeyboardButton(
            f"#{serial} {tp['symbol']} 🎯TP{tp['tp_level']}", 
            callback_data=f"symdetail_{tp['symbol']}_tp"
        )])
        result += f"`{serial}. {tp['symbol']}` → TP{tp['tp_level']} হিট | স্কোর: {tp['score']}/100\n"

    result += "\n💡 **সিম্বলে ক্লিক করুন বিস্তারিত দেখতে**"

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ পূর্ববর্তী", callback_data=f"tp_list_page_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("পরবর্তী ▶️", callback_data=f"tp_list_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("◀️ মেনুতে ফিরুন", callback_data="back_main")])

    await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def show_sl_list(query, page: int = 1, items_per_page: int = 3):
    """স্টপ লস লিস্ট দেখান - সিম্বল বাটন সহ"""
    sl_list = trade_analytics.get_sl_list()

    if not sl_list:
        await query.edit_message_text(
            "📭 **স্টপ লস লিস্ট** - কোনো এসএল রেকর্ড নেই।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ব্যাক", callback_data="back_main")]]),
            parse_mode='Markdown'
        )
        return

    total = len(sl_list)
    total_pages = (total + items_per_page - 1) // items_per_page
    if page > total_pages:
        page = total_pages

    start = (page - 1) * items_per_page
    end = min(start + items_per_page, total)
    page_sls = sl_list[start:end]

    result = f"⚠️ **স্টপ লস লিস্ট**  |  📋 {total} টি  |  📄 পৃষ্ঠা {page}/{total_pages}\n\n"
    keyboard = []

    for i, sl in enumerate(page_sls):
        serial = start + i + 1
        keyboard.append([InlineKeyboardButton(
            f"#{serial} {sl['symbol']} 🛑", 
            callback_data=f"symdetail_{sl['symbol']}_sl"
        )])
        result += f"`{serial}. {sl['symbol']}` → তারিখ: {sl['sl_date']} | স্কোর: {sl['score']}/100\n"

    result += "\n💡 **সিম্বলে ক্লিক করুন বিস্তারিত দেখতে**"

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ পূর্ববর্তী", callback_data=f"sl_list_page_{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("পরবর্তী ▶️", callback_data=f"sl_list_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("◀️ মেনুতে ফিরুন", callback_data="back_main")])

    await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


# ==================== ANALYSIS FUNCTIONS ====================

async def show_performance_report(query):
    active = len(trade_analytics.get_active_trades())
    tp_list = trade_analytics.get_tp_list()
    sl_list = trade_analytics.get_sl_list()
    wave_stats = trade_analytics.get_wave_stats()
    gap_stats = trade_analytics.get_gap_stats()
    tp_level_stats = trade_analytics.get_tp_level_stats()

    total_tp = len(tp_list)
    total_sl = len(sl_list)
    total_closed = total_tp + total_sl
    win_rate = (total_tp / total_closed * 100) if total_closed > 0 else 0

    report = f"""
📊 **ট্রেডিং পারফরম্যান্স রিপোর্ট**
📅 {datetime.now().strftime('%d-%m-%Y %H:%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 **সারাংশ:**
• সক্রিয় ট্রেড: {active} টি
• টেক প্রফিট: {total_tp} টি
• স্টপ লস: {total_sl} টি
• জয়ের হার: {win_rate:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌊 **ওয়েভ অনুযায়ী:**
• ইম্পালস: TP {wave_stats['impulse']['tp']} | SL {wave_stats['impulse']['sl']}
• করেকটিভ: TP {wave_stats['corrective']['tp']} | SL {wave_stats['corrective']['sl']}

⏱️ **গ্যাপ অনুযায়ী:**
• 0-5 দিন: TP {gap_stats['0-5']['tp']} | SL {gap_stats['0-5']['sl']}
• 6-10 দিন: TP {gap_stats['6-10']['tp']} | SL {gap_stats['6-10']['sl']}
• 11-15 দিন: TP {gap_stats['11-15']['tp']} | SL {gap_stats['11-15']['sl']}
• 16-30 দিন: TP {gap_stats['16-30']['tp']} | SL {gap_stats['16-30']['sl']}
• 30+ দিন: TP {gap_stats['30+']['tp']} | SL {gap_stats['30+']['sl']}

🎯 **টিপি লেভেল:**
• TP1: {tp_level_stats['tp1']['count']} টি
• TP2: {tp_level_stats['tp2']['count']} টি
• TP3: {tp_level_stats['tp3']['count']} টি
"""

    keyboard = [[InlineKeyboardButton("◀️ মেনুতে ফিরুন", callback_data="back_main")]]
    await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def show_wave_analysis(query, data):
    wave_stats = trade_analytics.get_wave_stats()

    if data == "wave_impulse":
        total = wave_stats['impulse']['tp'] + wave_stats['impulse']['sl']
        win_rate = (wave_stats['impulse']['tp'] / total * 100) if total > 0 else 0
        result = f"""
🌊 **ইম্পালস ওয়েভ অ্যানালাইসিস**

📊 মোট ট্রেড: {total} টি
✅ টেক প্রফিট: {wave_stats['impulse']['tp']} টি
❌ স্টপ লস: {wave_stats['impulse']['sl']} টি
📈 সাকসেস রেট: {win_rate:.1f}%

💡 সেরা সিম্বল: {', '.join(wave_stats['impulse']['tp_symbols'][:5]) if wave_stats['impulse']['tp_symbols'] else 'N/A'}
⚠️ সাবধান সিম্বল: {', '.join(wave_stats['impulse']['sl_symbols'][:3]) if wave_stats['impulse']['sl_symbols'] else 'N/A'}
"""

    elif data == "wave_corrective":
        total = wave_stats['corrective']['tp'] + wave_stats['corrective']['sl']
        win_rate = (wave_stats['corrective']['tp'] / total * 100) if total > 0 else 0
        result = f"""
📉 **করেকটিভ ওয়েভ অ্যানালাইসিস**

📊 মোট ট্রেড: {total} টি
✅ টেক প্রফিট: {wave_stats['corrective']['tp']} টি
❌ স্টপ লস: {wave_stats['corrective']['sl']} টি
📈 সাকসেস রেট: {win_rate:.1f}%

💡 সেরা সিম্বল: {', '.join(wave_stats['corrective']['tp_symbols'][:5]) if wave_stats['corrective']['tp_symbols'] else 'N/A'}
⚠️ সাবধান সিম্বল: {', '.join(wave_stats['corrective']['sl_symbols'][:3]) if wave_stats['corrective']['sl_symbols'] else 'N/A'}
"""

    else:
        impulse_total = wave_stats['impulse']['tp'] + wave_stats['impulse']['sl']
        corrective_total = wave_stats['corrective']['tp'] + wave_stats['corrective']['sl']
        impulse_rate = (wave_stats['impulse']['tp'] / impulse_total * 100) if impulse_total > 0 else 0
        corrective_rate = (wave_stats['corrective']['tp'] / corrective_total * 100) if corrective_total > 0 else 0
        result = f"""
📊 **ওয়েভ কম্পেয়ার**

🌊 ইম্পালস ওয়েভ: TP {wave_stats['impulse']['tp']} | SL {wave_stats['impulse']['sl']} | সাকসেস: {impulse_rate:.1f}%
📉 করেকটিভ ওয়েভ: TP {wave_stats['corrective']['tp']} | SL {wave_stats['corrective']['sl']} | সাকসেস: {corrective_rate:.1f}%

🏆 সেরা ওয়েভ: {'ইম্পালস' if impulse_rate >= corrective_rate else 'করেকটিভ'}
"""

    await query.edit_message_text(result, reply_markup=get_wave_keyboard(), parse_mode='Markdown')


async def show_gap_analysis(query, data):
    gap_stats = trade_analytics.get_gap_stats()
    gap_map = {
        'gap_0-5': ('0-5 দিন', '0-5'),
        'gap_6-10': ('6-10 দিন', '6-10'),
        'gap_11-15': ('11-15 দিন', '11-15'),
        'gap_16-30': ('16-30 দিন', '16-30'),
        'gap_30+': ('30+ দিন', '30+')
    }

    gap_name, gap_key = gap_map.get(data, ('0-5 দিন', '0-5'))
    stats = gap_stats.get(gap_key, {'tp': 0, 'sl': 0, 'tp_symbols': [], 'sl_symbols': []})

    total = stats['tp'] + stats['sl']
    win_rate = (stats['tp'] / total * 100) if total > 0 else 0

    result = f"""
⏱️ **গ্যাপ অ্যানালাইসিস - {gap_name}**

📊 মোট ট্রেড: {total} টি
✅ টেক প্রফিট: {stats['tp']} টি
❌ স্টপ লস: {stats['sl']} টি
📈 সাকসেস রেট: {win_rate:.1f}%

💡 টিপি সিম্বল: {', '.join(stats['tp_symbols'][:5]) if stats['tp_symbols'] else 'N/A'}
⚠️ এসএল সিম্বল: {', '.join(stats['sl_symbols'][:3]) if stats['sl_symbols'] else 'N/A'}

📊 বিশ্লেষণ: {_get_gap_analysis_text(gap_key, win_rate)}
"""

    await query.edit_message_text(result, reply_markup=get_gap_keyboard(), parse_mode='Markdown')


async def show_tp_level_analysis(query, data):
    tp_stats = trade_analytics.get_tp_level_stats()

    if data == "tp_level_1":
        result = f"""🎯 **TP1 অ্যানালাইসিস**

📊 মোট TP1: {tp_stats['tp1']['count']} টি

💡 টপ সিম্বল:
"""
        for i, sym in enumerate(tp_stats['tp1']['symbols_detail'][:10], 1):
            emoji = trade_analytics.get_score_emoji(sym['score'])
            result += f"{i}. {sym['symbol']} (স্কোর: {sym['score']}/100 {emoji})\n"
        result += f"\n📈 TP1 → TP2 রূপান্তর: {round(tp_stats['tp2']['count'] / tp_stats['tp1']['count'] * 100, 1) if tp_stats['tp1']['count'] > 0 else 0}%"

    elif data == "tp_level_2":
        result = f"""🎯 **TP2 অ্যানালাইসিস**

📊 মোট TP2: {tp_stats['tp2']['count']} টি

💡 টপ সিম্বল:
"""
        for i, sym in enumerate(tp_stats['tp2']['symbols_detail'][:10], 1):
            emoji = trade_analytics.get_score_emoji(sym['score'])
            result += f"{i}. {sym['symbol']} (স্কোর: {sym['score']}/100 {emoji})\n"
        result += f"\n📈 TP2 → TP3 রূপান্তর: {round(tp_stats['tp3']['count'] / tp_stats['tp2']['count'] * 100, 1) if tp_stats['tp2']['count'] > 0 else 0}%"

    elif data == "tp_level_3":
        result = f"""🎯 **TP3 অ্যানালাইসিস**

📊 মোট TP3: {tp_stats['tp3']['count']} টি

💡 টপ সিম্বল:
"""
        for i, sym in enumerate(tp_stats['tp3']['symbols_detail'][:10], 1):
            emoji = trade_analytics.get_score_emoji(sym['score'])
            result += f"{i}. {sym['symbol']} (স্কোর: {sym['score']}/100 {emoji})\n"
        result += f"\n🏆 পারফেক্ট স্কোর: {tp_stats['tp3']['count']} টি সিম্বল সর্বোচ্চ TP3 হিট করেছে!"

    else:
        result = f"""📊 **টিপি লেভেল কম্পেয়ার**

🎯 TP1: {tp_stats['tp1']['count']} টি
🎯 TP2: {tp_stats['tp2']['count']} টি
🎯 TP3: {tp_stats['tp3']['count']} টি

📈 রূপান্তর হার:
• TP1 → TP2: {round(tp_stats['tp2']['count'] / tp_stats['tp1']['count'] * 100, 1) if tp_stats['tp1']['count'] > 0 else 0}%
• TP2 → TP3: {round(tp_stats['tp3']['count'] / tp_stats['tp2']['count'] * 100, 1) if tp_stats['tp2']['count'] > 0 else 0}%
• TP1 → TP3: {round(tp_stats['tp3']['count'] / tp_stats['tp1']['count'] * 100, 1) if tp_stats['tp1']['count'] > 0 else 0}%
"""

    await query.edit_message_text(result, reply_markup=get_tp_level_keyboard(), parse_mode='Markdown')


async def show_score_analysis(query, data):
    score_stats = trade_analytics.get_score_stats()
    score_map = {
        'score_excellent': ('excellent', '💎 85-100'),
        'score_very_strong': ('very_strong', '🔥 80-84'),
        'score_strong': ('strong', '⭐ 70-79'),
        'score_good': ('good', '✅ 60-69'),
        'score_medium': ('medium', '📈 50-59'),
        'score_weak': ('weak', '⚠️ 40-49'),
        'score_very_weak': ('very_weak', '❌ 0-39')
    }

    score_key, score_name = score_map.get(data, ('medium', '📈 50-59'))
    stats = score_stats.get(score_key, {'range': 'N/A', 'tp': 0, 'sl': 0})

    total = stats['tp'] + stats['sl']
    win_rate = (stats['tp'] / total * 100) if total > 0 else 0

    result = f"""
⭐ **স্কোর অ্যানালাইসিস - {score_name}**

📊 মোট ট্রেড: {total} টি
✅ টেক প্রফিট: {stats['tp']} টি
❌ স্টপ লস: {stats['sl']} টি
📈 সাকসেস রেট: {win_rate:.1f}%

💡 সুপারিশ: {_get_score_recommendation(score_key, win_rate)}
"""

    await query.edit_message_text(result, reply_markup=get_score_keyboard(), parse_mode='Markdown')


async def show_full_report(query):
    active = len(trade_analytics.get_active_trades())
    tp_list = trade_analytics.get_tp_list()
    sl_list = trade_analytics.get_sl_list()
    wave_stats = trade_analytics.get_wave_stats()
    gap_stats = trade_analytics.get_gap_stats()
    tp_level_stats = trade_analytics.get_tp_level_stats()
    score_stats = trade_analytics.get_score_stats()

    total_tp = len(tp_list)
    total_sl = len(sl_list)
    total_closed = total_tp + total_sl
    win_rate = (total_tp / total_closed * 100) if total_closed > 0 else 0

    report = f"""
📊 **সম্পূর্ণ ট্রেডিং রিপোর্ট**
📅 {datetime.now().strftime('%d-%m-%Y %H:%M')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 সারাংশ:
• সক্রিয় ট্রেড: {active} টি
• টেক প্রফিট: {total_tp} টি
• স্টপ লস: {total_sl} টি
• জয়ের হার: {win_rate:.1f}%

🌊 ওয়েভ অনুযায়ী:
• ইম্পালস: TP {wave_stats['impulse']['tp']} | SL {wave_stats['impulse']['sl']}
• করেকটিভ: TP {wave_stats['corrective']['tp']} | SL {wave_stats['corrective']['sl']}

⏱️ গ্যাপ অনুযায়ী:
• 0-5 দিন: TP {gap_stats['0-5']['tp']} | SL {gap_stats['0-5']['sl']}
• 6-10 দিন: TP {gap_stats['6-10']['tp']} | SL {gap_stats['6-10']['sl']}
• 11-15 দিন: TP {gap_stats['11-15']['tp']} | SL {gap_stats['11-15']['sl']}
• 16-30 দিন: TP {gap_stats['16-30']['tp']} | SL {gap_stats['16-30']['sl']}
• 30+ দিন: TP {gap_stats['30+']['tp']} | SL {gap_stats['30+']['sl']}

🎯 টিপি লেভেল:
• TP1: {tp_level_stats['tp1']['count']} টি
• TP2: {tp_level_stats['tp2']['count']} টি
• TP3: {tp_level_stats['tp3']['count']} টি

⭐ সেরা স্কোর রেঞ্জ:
• 85-100: TP {score_stats['excellent']['tp']} | SL {score_stats['excellent']['sl']}
• 80-84: TP {score_stats['very_strong']['tp']} | SL {score_stats['very_strong']['sl']}
• 70-79: TP {score_stats['strong']['tp']} | SL {score_stats['strong']['sl']}
"""

    keyboard = [[InlineKeyboardButton("◀️ মেনুতে ফিরুন", callback_data="back_main")]]
    await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def search_symbol_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔍 **সিম্বল সার্চ**\n\nসিম্বল লিখুন: `/searchsymbol [সিম্বল]`\n\nউদাহরণ: `/searchsymbol ADVENT`",
            parse_mode='Markdown'
        )
        return

    symbol = context.args[0].upper()
    active = trade_analytics.get_active_trades()
    tp_list = trade_analytics.get_tp_list()
    sl_list = trade_analytics.get_sl_list()

    active_found = [a for a in active if a['symbol'].upper() == symbol]
    tp_found = [t for t in tp_list if t['symbol'].upper() == symbol]
    sl_found = [s for s in sl_list if s['symbol'].upper() == symbol]

    result = f"🔍 **'{symbol}' সার্চ রেজাল্ট**\n\n"

    if active_found:
        result += f"📈 **সক্রিয় ট্রেড:**\n"
        for a in active_found:
            result += trade_analytics.format_stock_card(a, 1)
    else:
        result += f"📈 **সক্রিয় ট্রেড:** নেই\n"

    if tp_found:
        result += f"\n✅ **টেক প্রফিট:**\n"
        for t in tp_found:
            result += trade_analytics.format_stock_card(t, 1)
            result += f"\n🎯 TP{t['tp_level']} হিট\n"
    else:
        result += f"\n✅ **টেক প্রফিট:** নেই\n"

    if sl_found:
        result += f"\n⚠️ **স্টপ লস:**\n"
        for s in sl_found:
            result += trade_analytics.format_stock_card(s, 1)
            result += f"\n🛑 স্টপ লস হিট\n"
    else:
        result += f"\n⚠️ **স্টপ লস:** নেই\n"

    if len(result) > 4000:
        parts = [result[i:i+4000] for i in range(0, len(result), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode='Markdown')
    else:
        await update.message.reply_text(result, parse_mode='Markdown')


async def trade_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 **ট্রেডিং অ্যানালাইটিক্স মেনু**\n\nনিচের বাটন থেকে আপনার পছন্দের অপশন নির্বাচন করুন:",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ক্যালব্যাক কোয়েরি হ্যান্ডলার - লিস্ট পেজিনেশন এবং মেনু"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await query.edit_message_text(
            "📊 **ট্রেডিং অ্যানালাইটিক্স মেনু**\n\nনিচের বাটন থেকে আপনার পছন্দের অপশন নির্বাচন করুন:",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == "perf_main":
        await show_performance_report(query)
        return

    if data.startswith("active_list"):
        page = 1
        if data.startswith("active_list_page_"):
            page = int(data.split("_")[-1])
        await show_active_trades(query, page)
        return

    if data.startswith("tp_list"):
        page = 1
        if data.startswith("tp_list_page_"):
            page = int(data.split("_")[-1])
        await show_tp_list(query, page)
        return

    if data.startswith("sl_list"):
        page = 1
        if data.startswith("sl_list_page_"):
            page = int(data.split("_")[-1])
        await show_sl_list(query, page)
        return

    if data == "wave_menu":
        await query.edit_message_text(
            "🌊 **ওয়েভ অ্যানালাইটিক্স**\n\nওয়েভ টাইপ নির্বাচন করুন:",
            reply_markup=get_wave_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data in ["wave_impulse", "wave_corrective", "wave_compare"]:
        await show_wave_analysis(query, data)
        return

    if data == "gap_menu":
        await query.edit_message_text(
            "⏱️ **গ্যাপ অ্যানালাইটিক্স**\n\nগ্যাপ রেঞ্জ নির্বাচন করুন:",
            reply_markup=get_gap_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data.startswith("gap_"):
        await show_gap_analysis(query, data)
        return

    if data == "tp_level_menu":
        await query.edit_message_text(
            "🎯 **টিপি লেভেল অ্যানালাইটিক্স**\n\nটিপি লেভেল নির্বাচন করুন:",
            reply_markup=get_tp_level_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data in ["tp_level_1", "tp_level_2", "tp_level_3", "tp_level_compare"]:
        await show_tp_level_analysis(query, data)
        return

    if data == "score_menu":
        await query.edit_message_text(
            "⭐ **স্কোর অ্যানালাইটিক্স**\n\nস্কোর রেঞ্জ নির্বাচন করুন:",
            reply_markup=get_score_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data.startswith("score_"):
        await show_score_analysis(query, data)
        return

    if data == "full_report":
        await show_full_report(query)
        return

    if data == "search_symbol":
        await query.edit_message_text(
            "🔍 **সিম্বল সার্চ**\n\nসিম্বল লিখুন: `/searchsymbol [সিম্বল]`\n\nউদাহরণ: `/searchsymbol ADVENT`",
            parse_mode='Markdown'
        )
        return


# ==================== HELPER FUNCTIONS ====================

def _get_gap_analysis_text(gap_key: str, win_rate: float) -> str:
    if win_rate >= 70:
        return "🔥 এই সময়ের মধ্যে টিপি হিটের সম্ভাবনা খুব বেশি। দ্রুত ট্রেড করার জন্য উপযুক্ত।"
    elif win_rate >= 50:
        return "📈 মধ্যম পারফরম্যান্স। ট্রেড করতে পারেন তবে সতর্ক থাকুন।"
    elif win_rate >= 30:
        return "⚠️ কম সাকসেস রেট। ট্রেড করার আগে ভালোভাবে বিশ্লেষণ করুন।"
    else:
        return "❌ এই সময়ের মধ্যে ট্রেড এড়িয়ে চলুন।"


def _get_score_recommendation(score_key: str, win_rate: float) -> str:
    recommendations = {
        'excellent': "💎 এক্সট্রিম শক্তিশালী - ট্রেড করার জন্য সেরা সিম্বল",
        'very_strong': "🔥 খুব শক্তিশালী - ট্রেড করার জন্য উপযুক্ত",
        'strong': "⭐ শক্তিশালী - মনিটর করে ট্রেড করুন",
        'good': "✅ ভাল - ভালো সেটআপ পেলে ট্রেড করুন",
        'medium': "📈 মধ্যম - সতর্কতার সাথে ট্রেড করুন",
        'weak': "⚠️ দুর্বল - এড়িয়ে চলুন",
        'very_weak': "❌ খুব দুর্বল - ট্রেড করবেন না"
    }
    return recommendations.get(score_key, "📈 সাধারণ - নিজের বিশ্লেষণ করুন")


# ==================== HANDLER FUNCTIONS ====================

def add_trade_analytics_handlers(application):
    """ট্রেড অ্যানালাইটিক্স হ্যান্ডলার যোগ করুন"""
    application.add_handler(CommandHandler("trademenu", trade_menu_command))
    application.add_handler(CommandHandler("searchsymbol", search_symbol_command))

    application.add_handler(CallbackQueryHandler(handle_callback, pattern='^(?!symdetail_|back_to_)'))
    application.add_handler(CallbackQueryHandler(show_symbol_detail, pattern='^symdetail_'))
    application.add_handler(CallbackQueryHandler(back_to_list, pattern='^back_to_'))

    print("✅ Trade Analytics handlers added successfully (with symbol detail buttons)")


# ==================== TEST/DEBUG ====================
if __name__ == "__main__":
    print("="*60)
    print("📊 Trade Analytics Module Loaded")
    print("="*60)
    print(f"📁 Data directory: {trade_analytics.data_dir}")
    print(f"📁 Stock directory: {trade_analytics.stock_dir}")
    print(f"📄 ed.csv: {os.path.exists(trade_analytics.ed_file)}")
    print(f"📄 rd.csv: {os.path.exists(trade_analytics.rd_file)}")
    print(f"📄 sl.csv: {os.path.exists(trade_analytics.sl_file)}")
    print(f"📄 tp.csv: {os.path.exists(trade_analytics.tp_file)}")
    print("="*60)