import discord
from discord.ext import commands
from datetime import datetime, time
import pytz

# 機器人設定
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ===== 重要設定區 =====
# 你的時區（台灣時間）
TIMEZONE = pytz.timezone('Asia/Taipei')

# 工作日設定（0=週一, 1=週二, 2=週三, 3=週四, 4=週五, 5=週六, 6=週日）
WORKING_DAYS = [0, 1, 2, 3, 4, 5, 6]  # 週一、週五、週六、週日

# 工作時間設定（24小時制）
WORK_START = time(21, 0)  # 晚上21:00開始工作
WORK_END = time(8, 0)    # 早上8:00結束工作

# ===== 監控設定 =====
# 監控指定的類別名稱（Category）
MONITORED_CATEGORIES = [
    'Tɪcket',           # 範例：票券類別
    'Upload Channel',              # 範例：客服類別
    'UPLOAD ONLY AVATAR',               # 範例：中文類別
    # 在這裡添加你要監控的類別名稱
]

# 監控指定的頻道名稱或ID
MONITORED_CHANNELS_IDS = [
    822211672840208395,    # 或者直接使用頻道ID（取消註解並填入實際ID）
]

# 監控特定 Forum 名稱
MONITORED_FORUM_NAMES = [
    'ʜᴇʟᴘ'
    # 在這裡添加你要監控的 Forum 名稱
]

# 自動回覆訊息
AUTO_REPLY_MESSAGE = """
🌙 **Latitia is currently unavailable**

Hello! Thank you for reaching out.

⏰ **Current time**: {current_time} (UTC+8)
🕐 **Working hours**: <t:1759449600:t> - <t:1759485600:t>
😴 **Break Time**：Daily <t:1759496400:t> - <t:1759449600:t>
✅ **Ticket Response Time**：<t:1759464000:t> - <t:1759496400:t>

**Current status**: {status_message}

I will respond to your inquiry as soon as I'm available. {next_available}

**Note**: If I don't respond during working hours, I might be working overtime at my day job.

Thank you for your patience! 🙏
"""

# 已回覆的頻道記錄（避免重複回覆）
replied_channels = set()

# ===== 功能函數 =====

def is_working_time():
    """檢查當前是否在工作時間內"""
    now = datetime.now(TIMEZONE)
    current_day = now.weekday()
    current_time = now.time()
    
    if current_day not in WORKING_DAYS:
        return False
    
    return WORK_START <= current_time <= WORK_END

def get_status_message():
    """獲取當前狀態訊息"""
    now = datetime.now(TIMEZONE)
    current_day = now.weekday()
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    if current_day not in WORKING_DAYS:
        return f"It's {day_names[current_day]}, which is my day off"
    else:
        current_time = now.time()
        if current_time < WORK_START:
            return f"It's before my working hours (starts at {WORK_START.strftime('%H:%M')})"
        elif current_time > WORK_END:
            return f"It's after my working hours (ends at {WORK_END.strftime('%H:%M')})"
        else:
            return "I'm currently working on other tasks or may be working overtime at my day job"

def get_next_available_time():
    """獲取下次可用時間"""
    now = datetime.now(TIMEZONE)
    current_day = now.weekday()
    current_time = now.time()
    
    if current_day in WORKING_DAYS and current_time < WORK_START:
        return f"Expected response after **{WORK_START.strftime('%H:%M')} today**."
    
    days_until_next_work = None
    for i in range(1, 8):
        next_day = (current_day + i) % 7
        if next_day in WORKING_DAYS:
            days_until_next_work = i
            break
    
    if days_until_next_work == 1:
        return f"Expected response after **{WORK_START.strftime('%H:%M')} tomorrow**."
    else:
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        next_work_day = day_names[(current_day + days_until_next_work) % 7]
        return f"Expected response after **{WORK_START.strftime('%H:%M')} on {next_work_day}**."

def should_monitor_channel(channel):
    """判斷是否應該監控此頻道"""
    # 檢查是否為 Forum 頻道
    if isinstance(channel, discord.ForumChannel):
        if MONITOR_FORUMS:
            # 如果設定監控所有 Forum，則檢查名稱
            if not MONITORED_FORUM_NAMES:
                return True
            return any(forum_name.lower() in channel.name.lower() for forum_name in MONITORED_FORUM_NAMES)
        return False
    
    # 檢查是否為 Thread（Forum 中的討論串或一般討論串）
    if isinstance(channel, discord.Thread):
        # 如果是 Forum 中的討論串
        if channel.parent and isinstance(channel.parent, discord.ForumChannel):
            if MONITOR_FORUMS:
                if not MONITORED_FORUM_NAMES:
                    return True
                return any(forum_name.lower() in channel.parent.name.lower() for forum_name in MONITORED_FORUM_NAMES)
        
        # 如果是一般討論串，檢查其父頻道
        if channel.parent:
            return should_monitor_channel(channel.parent)
        return False
    
    # 檢查頻道ID（精確匹配）
    if any(isinstance(ch, int) and ch == channel.id for ch in MONITORED_CHANNELS):
        return True
    
    # 檢查頻道名稱（包含關鍵字）
    channel_name_lower = channel.name.lower()
    if any(isinstance(ch, str) and ch.lower() in channel_name_lower for ch in MONITORED_CHANNELS):
        return True
    
    # 檢查類別（Category）
    if hasattr(channel, 'category') and channel.category:
        category_name = channel.category.name
        if any(cat.lower() in category_name.lower() for cat in MONITORED_CATEGORIES):
            return True
    
    return False

# ===== 機器人事件 =====

@bot.event
async def on_ready():
    """機器人啟動時執行"""
    print(f'✅ 機器人已上線：{bot.user.name}')
    print(f'📋 機器人 ID：{bot.user.id}')
    print(f'⏰ 當前時區：{TIMEZONE}')
    print(f'📅 工作日：週二、週三、週四')
    print(f'🕐 工作時間：{WORK_START.strftime("%H:%M")} - {WORK_END.strftime("%H:%M")}')
    print(f'💼 當前狀態：{"✅ 工作中" if is_working_time() else "😴 休息中"}')
    print('\n🔍 監控設定：')
    print(f'  📁 監控類別：{MONITORED_CATEGORIES if MONITORED_CATEGORIES else "無"}')
    print(f'  💬 監控頻道：{MONITORED_CHANNELS if MONITORED_CHANNELS else "無"}')
    print(f'  📋 監控 Forum：{"是" if MONITOR_FORUMS else "否"}')
    if MONITORED_FORUM_NAMES:
        print(f'  📋 指定 Forum：{MONITORED_FORUM_NAMES}')
    print('=' * 50)

@bot.event
async def on_message(message):
    """當有新訊息時觸發"""
    # 忽略機器人自己的訊息
    if message.author.bot:
        await bot.process_commands(message)
        return
    
    # 檢查是否應該監控此頻道
    channel = message.channel
    if not should_monitor_channel(channel):
        await bot.process_commands(message)
        return
    
    # 檢查是否已回覆過這個頻道
    if channel.id in replied_channels:
        await bot.process_commands(message)
        return
    
    # 檢查是否在工作時間（如果在工作時間，不回覆）
    if is_working_time():
        print(f'⏰ 當前是工作時間，不發送自動回覆：{channel.name}')
        await bot.process_commands(message)
        return
    
    # 發送自動回覆
    try:
        current_time = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M')
        status_msg = get_status_message()
        next_available = get_next_available_time()
        
        reply_message = AUTO_REPLY_MESSAGE.format(
            current_time=current_time,
            status_message=status_msg,
            next_available=next_available
        )
        
        await channel.send(reply_message)
        replied_channels.add(channel.id)
        
        # 顯示頻道類型
        channel_type = "Forum Thread" if isinstance(channel, discord.Thread) and isinstance(channel.parent, discord.ForumChannel) else \
                       "Thread" if isinstance(channel, discord.Thread) else \
                       "Forum" if isinstance(channel, discord.ForumChannel) else "Channel"
        
        print(f'✅ 已發送自動回覆')
        print(f'   類型：{channel_type}')
        print(f'   名稱：{channel.name}')
        print(f'   用戶：{message.author.name}')
        if hasattr(channel, 'category') and channel.category:
            print(f'   類別：{channel.category.name}')
        
    except discord.Forbidden:
        print(f'❌ 沒有權限在頻道發送訊息：{channel.name}')
    except Exception as e:
        print(f'❌ 發送訊息時發生錯誤：{e}')
    
    await bot.process_commands(message)

@bot.event
async def on_thread_create(thread):
    """當 Forum 中創建新討論串時（額外保險，確保捕捉到）"""
    # 如果是 Forum Thread，等待一下讓第一條訊息出現
    if isinstance(thread.parent, discord.ForumChannel):
        print(f'🆕 偵測到新 Forum Thread：{thread.name}')

# ===== 管理員指令 =====

@bot.command(name='status')
async def check_status(ctx):
    """檢查機器人狀態"""
    now = datetime.now(TIMEZONE)
    is_working = is_working_time()
    
    embed = discord.Embed(
        title="🤖 機器人狀態",
        color=discord.Color.green() if is_working else discord.Color.orange(),
        timestamp=now
    )
    
    embed.add_field(
        name="📅 當前時間", 
        value=now.strftime('%Y-%m-%d %H:%M:%S (%A)'), 
        inline=False
    )
    
    embed.add_field(
        name="🕐 工作時間", 
        value=f"週二、週三、週四\n{WORK_START.strftime('%H:%M')} - {WORK_END.strftime('%H:%M')}", 
        inline=False
    )
    
    status_emoji = "✅" if is_working else "😴"
    status_text = "工作中（不會自動回覆）" if is_working else "休息中（會自動回覆）"
    embed.add_field(
        name="💼 當前狀態", 
        value=f"{status_emoji} {status_text}", 
        inline=False
    )
    
    # 監控設定
    monitoring_info = []
    if MONITORED_CATEGORIES:
        monitoring_info.append(f"📁 類別：{len(MONITORED_CATEGORIES)} 個")
    if MONITORED_CHANNELS:
        monitoring_info.append(f"💬 頻道：{len(MONITORED_CHANNELS)} 個")
    if MONITOR_FORUMS:
        monitoring_info.append(f"📋 Forum：啟用")
    
    if monitoring_info:
        embed.add_field(
            name="🔍 監控設定",
            value="\n".join(monitoring_info),
            inline=False
        )
    
    embed.add_field(
        name="📊 統計", 
        value=f"已回覆頻道數：{len(replied_channels)}", 
        inline=False
    )
    
    if not is_working:
        next_available = get_next_available_time()
        embed.add_field(
            name="⏰ 下次工作時間", 
            value=next_available, 
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='check')
async def check_channel(ctx):
    """檢查當前頻道是否會被監控"""
    channel = ctx.channel
    is_monitored = should_monitor_channel(channel)
    
    embed = discord.Embed(
        title="🔍 頻道檢查",
        color=discord.Color.green() if is_monitored else discord.Color.red()
    )
    
    # 頻道資訊
    channel_type = "Forum Thread" if isinstance(channel, discord.Thread) and isinstance(channel.parent, discord.ForumChannel) else \
                   "Thread" if isinstance(channel, discord.Thread) else \
                   "Forum" if isinstance(channel, discord.ForumChannel) else \
                   "Text Channel"
    
    embed.add_field(name="頻道名稱", value=channel.name, inline=False)
    embed.add_field(name="頻道類型", value=channel_type, inline=False)
    embed.add_field(name="頻道 ID", value=str(channel.id), inline=False)
    
    if hasattr(channel, 'category') and channel.category:
        embed.add_field(name="所屬類別", value=channel.category.name, inline=False)
    elif isinstance(channel, discord.Thread) and channel.parent:
        if isinstance(channel.parent, discord.ForumChannel):
            embed.add_field(name="所屬 Forum", value=channel.parent.name, inline=False)
        else:
            embed.add_field(name="父頻道", value=channel.parent.name, inline=False)
    
    # 監控狀態
    embed.add_field(
        name="監控狀態",
        value=f"{'✅ 會被監控' if is_monitored else '❌ 不會被監控'}",
        inline=False
    )
    
    # 已回覆狀態
    if channel.id in replied_channels:
        embed.add_field(
            name="回覆狀態",
            value="⚠️ 此頻道已回覆過（不會再次自動回覆）",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='list')
@commands.has_permissions(administrator=True)
async def list_monitored(ctx):
    """列出所有監控設定（僅管理員可用）"""
    embed = discord.Embed(
        title="📋 監控設定清單",
        color=discord.Color.blue()
    )
    
    if MONITORED_CATEGORIES:
        categories_text = "\n".join([f"• {cat}" for cat in MONITORED_CATEGORIES])
        embed.add_field(name="📁 監控的類別", value=categories_text, inline=False)
    
    if MONITORED_CHANNELS:
        channels_text = "\n".join([f"• {ch}" for ch in MONITORED_CHANNELS])
        embed.add_field(name="💬 監控的頻道", value=channels_text, inline=False)
    
    forum_status = "✅ 啟用" if MONITOR_FORUMS else "❌ 停用"
    embed.add_field(name="📋 Forum 監控", value=forum_status, inline=False)
    
    if MONITORED_FORUM_NAMES:
        forums_text = "\n".join([f"• {forum}" for forum in MONITORED_FORUM_NAMES])
        embed.add_field(name="📋 指定的 Forum", value=forums_text, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='clear')
@commands.has_permissions(administrator=True)
async def clear_replied(ctx):
    """清除已回覆的頻道記錄（僅管理員可用）"""
    count = len(replied_channels)
    replied_channels.clear()
    await ctx.send(f'✅ 已清除 {count} 個頻道的回覆記錄')

@bot.command(name='test')
@commands.has_permissions(administrator=True)
async def test_reply(ctx):
    """在當前頻道測試自動回覆訊息（僅管理員可用）"""
    current_time = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M')
    status_msg = get_status_message()
    next_available = get_next_available_time()
    
    message = AUTO_REPLY_MESSAGE.format(
        current_time=current_time,
        status_message=status_msg,
        next_available=next_available
    )
    
    await ctx.send(message)
    await ctx.send('⬆️ 以上是自動回覆訊息預覽')

@bot.command(name='add')
@commands.has_permissions(administrator=True)
async def add_channel_to_replied(ctx):
    """將當前頻道加入已回覆清單（僅管理員可用）"""
    if ctx.channel.id in replied_channels:
        await ctx.send('⚠️ 此頻道已經在已回覆清單中')
    else:
        replied_channels.add(ctx.channel.id)
        await ctx.send('✅ 已將此頻道加入已回覆清單，機器人不會再次自動回覆')

@bot.command(name='remove')
@commands.has_permissions(administrator=True)
async def remove_channel_from_replied(ctx):
    """將當前頻道從已回覆清單移除（僅管理員可用）"""
    if ctx.channel.id not in replied_channels:
        await ctx.send('⚠️ 此頻道不在已回覆清單中')
    else:
        replied_channels.remove(ctx.channel.id)
        await ctx.send('✅ 已將此頻道從已回覆清單移除，機器人可以再次自動回覆')

@bot.command(name='help_bot')
async def help_command(ctx):
    """顯示機器人指令幫助"""
    embed = discord.Embed(
        title="🤖 機器人指令說明",
        description="以下是可用的指令：",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="!status", value="查看機器人當前狀態", inline=False)
    embed.add_field(name="!check", value="檢查當前頻道是否會被監控", inline=False)
    embed.add_field(name="!list (管理員)", value="列出所有監控設定", inline=False)
    embed.add_field(name="!test (管理員)", value="測試自動回覆訊息", inline=False)
    embed.add_field(name="!clear (管理員)", value="清除已回覆記錄", inline=False)
    embed.add_field(name="!add (管理員)", value="標記當前頻道已回覆", inline=False)
    embed.add_field(name="!remove (管理員)", value="移除當前頻道標記", inline=False)
    embed.add_field(name="!help_bot", value="顯示此幫助訊息", inline=False)
    
    await ctx.send(embed=embed)

# ===== 啟動機器人 =====
if __name__ == '__main__':
    import os
    
    print('🚀 正在啟動機器人...')
    
    # 直接從環境變數讀取 TOKEN
    TOKEN = os.environ.get('DISCORD_TOKEN')
    
    if not TOKEN:
        print('❌ 錯誤：找不到 DISCORD_TOKEN 環境變數')
        print('請在 Render 控制台設定 DISCORD_TOKEN')
        exit(1)
    else:
        print('✅ Token 已載入')
        print(f'✅ Token 長度：{len(TOKEN)} 字元')
        bot.run(TOKEN)
