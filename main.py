import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import pytz
import os
from myserver import server_on


CHANNEL_ID = 1204467537618935839
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
boss_timers = {}
notifications_enabled = True  # เปิดแจ้งเตือนเริ่มต้น

# ไทยโซนเวลา
tz = pytz.timezone('Asia/Bangkok')

# ====================== ระบบแจ้งเตือนบอส ======================
@tasks.loop(seconds=1)
async def check_bosses():
    now = datetime.now(tz)
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        return
    for name, info in list(boss_timers.items()):
        warn_time = info['next_time'] - timedelta(minutes=2)
        if notifications_enabled and not info['warned'] and now >= warn_time:
            await channel.send(f"⏰ ใกล้ถึงเวลา **{name}** แล้วนะ!", file=discord.File(info['image_path']))
            info['warned'] = True
        if now >= info['next_time']:
            if notifications_enabled:
                await channel.send(f"🛡️ ถึงเวลา **{name}** แล้วนะ!", file=discord.File(info['image_path']))
            info['next_time'] += timedelta(hours=info['interval_hours'], minutes=info['interval_minutes'])
            info['warned'] = False

# ====================== !เปิดเสียง / !ปิดเสียง ======================
@bot.command(name='เปิดเสียง')
async def enable_notifications(ctx):
    global notifications_enabled
    notifications_enabled = True
    await ctx.send("🔊 เปิดการแจ้งเตือนเรียบร้อยแล้ว!")

@bot.command(name='ปิดเสียง')
async def disable_notifications(ctx):
    global notifications_enabled
    notifications_enabled = False
    await ctx.send("🔇 ปิดการแจ้งเตือนเรียบร้อยแล้ว! (ยังคงคำนวณเวลาบอสอยู่)")

# ====================== คำสั่งเปลี่ยน Channel ======================
@bot.command(name='CHID')
async def change_channel(ctx, new_channel_id: int):
    global CHANNEL_ID
    try:
        new_channel = bot.get_channel(new_channel_id)
        if new_channel is None:
            await ctx.send("❌ ไม่พบช่องที่ระบุ กรุณาตรวจสอบ ID ใหม่อีกครั้ง")
            return
        CHANNEL_ID = new_channel_id
        await ctx.send(f"✅ เปลี่ยน Channel ID เป็น {CHANNEL_ID} เรียบร้อยแล้ว")
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")

# ====================== ระบบเพิ่มบอสแบบโต้ตอบ ======================
@bot.command(name='เพิ่มบอส')
async def add_boss(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("📝 พิมพ์ชื่อบอส:")
    try:
        name_msg = await bot.wait_for('message', check=check, timeout=60)
        name = name_msg.content.strip()

        await ctx.send("⏰ ใส่ชั่วโมงที่บอสจะเกิด (เช่น 16):")
        hour_msg = await bot.wait_for('message', check=check, timeout=60)
        hour = int(hour_msg.content.strip())

        await ctx.send("🕧 ใส่นาทีที่บอสจะเกิด (เช่น 30):")
        min_msg = await bot.wait_for('message', check=check, timeout=60)
        minute = int(min_msg.content.strip())

        await ctx.send("🔁 บอสจะเกิดซ้ำทุกๆกี่ชั่วโมง:")
        interval_h_msg = await bot.wait_for('message', check=check, timeout=60)
        interval_hours = int(interval_h_msg.content.strip())

        await ctx.send("➕ ต้องการเพิ่มนาทีในรอบถัดไปหรือไม่? (ใส่เลข 0 ถ้าไม่ต้องการ):")
        interval_m_msg = await bot.wait_for('message', check=check, timeout=60)
        interval_minutes = int(interval_m_msg.content.strip())

        await ctx.send("🖼️ กรุณาส่งรูปบอส (แนบไฟล์รูปภาพ):")
        image_msg = await bot.wait_for('message', check=check, timeout=60)
        image = image_msg.attachments[0]

        os.makedirs("./boss_images", exist_ok=True)
        image_path = f"./boss_images/{name}.png"
        await image.save(image_path)

        now = datetime.now(tz)
        next_time = tz.localize(datetime(now.year, now.month, now.day, hour, minute))
        if next_time < now:
            next_time += timedelta(days=1)

        boss_timers[name] = {
            'next_time': next_time,
            'interval_hours': interval_hours,
            'interval_minutes': interval_minutes,
            'warned': False,
            'image_path': image_path
        }

        await ctx.send(f"✅ เพิ่มบอส **{name}** เวลา {hour:02d}:{minute:02d} แล้ว แจ้งเตือนทุก {interval_hours}ชม. {interval_minutes}นาที")
    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")

# ====================== แก้ไขบอส ======================
@bot.command(name='แก้ไขบอส')
async def edit_boss(ctx, *, name):
    if name not in boss_timers:
        await ctx.send("❌ ไม่พบบอสชื่อนี้!")
        return

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send(f"✏️ ต้องการแก้ไขชื่อบอส **{name}** เป็นอะไร? (พิมพ์ชื่อใหม่หรือพิมพ์ - เพื่อไม่เปลี่ยน)")
    new_name_msg = await bot.wait_for('message', check=check, timeout=60)
    new_name = new_name_msg.content.strip()
    if new_name == "-":
        new_name = name

    await ctx.send("⏰ แก้ไขชั่วโมงที่บอสจะเกิด (0-23) หรือพิมพ์ - เพื่อไม่เปลี่ยน:")
    hour_msg = await bot.wait_for('message', check=check, timeout=60)
    hour_input = hour_msg.content.strip()

    await ctx.send("🕧 แก้ไขนาทีที่บอสจะเกิด (0-59) หรือพิมพ์ - เพื่อไม่เปลี่ยน:")
    min_msg = await bot.wait_for('message', check=check, timeout=60)
    min_input = min_msg.content.strip()

    await ctx.send("🔁 แก้ไขจำนวนชั่วโมงที่บอสจะเกิดซ้ำ หรือพิมพ์ - เพื่อไม่เปลี่ยน:")
    interval_h_msg = await bot.wait_for('message', check=check, timeout=60)
    interval_h_input = interval_h_msg.content.strip()

    await ctx.send("➕ แก้ไขจำนวน *นาที* ที่เพิ่มในรอบถัดไป หรือพิมพ์ - เพื่อไม่เปลี่ยน:")
    interval_m_msg = await bot.wait_for('message', check=check, timeout=60)
    interval_m_input = interval_m_msg.content.strip()

    old_info = boss_timers[name]

    if hour_input != "-" and min_input != "-":
        hour = int(hour_input)
        minute = int(min_input)
        now = datetime.now(tz)
        next_time = tz.localize(datetime(now.year, now.month, now.day, hour, minute))
        if next_time < now:
            next_time += timedelta(days=1)
    else:
        next_time = old_info['next_time']

    interval_hours = int(interval_h_input) if interval_h_input != "-" else old_info['interval_hours']
    interval_minutes = int(interval_m_input) if interval_m_input != "-" else old_info['interval_minutes']

    if new_name != name:
        old_path = old_info['image_path']
        new_path = f"./boss_images/{new_name}.png"
        os.rename(old_path, new_path)
    else:
        new_path = old_info['image_path']

    boss_timers.pop(name)
    boss_timers[new_name] = {
        'next_time': next_time,
        'interval_hours': interval_hours,
        'interval_minutes': interval_minutes,
        'warned': False,
        'image_path': new_path
    }

    await ctx.send(f"✅ แก้ไขบอส **{new_name}** เรียบร้อยแล้ว")

# ====================== ลบบอส ======================
@bot.command(name='ลบบอส')
async def delete_boss(ctx, *, name):
    if name in boss_timers:
        del boss_timers[name]
        await ctx.send(f"🗑️ ลบบอส **{name}** แล้ว")
    else:
        await ctx.send("❌ ไม่พบบอสชื่อนี้!")

# ====================== เช็คบอสทั้งหมด ======================
@bot.command(name='เช็คบอส')
async def check_boss(ctx):
    if not boss_timers:
        await ctx.send("📭 ยังไม่มีบอสที่ตั้งไว้เลย")
        return

    msg = "📋 รายชื่อบอสที่ตั้งไว้:\n"
    for name, info in boss_timers.items():
        time_str = info['next_time'].strftime('%H:%M')
        msg += f"- {name} : ถัดไป {time_str} / ทุก {info['interval_hours']}ชม. {info['interval_minutes']}นาที\n"
    await ctx.send(msg)

# ====================== เช็คคำสั่ง ======================
@bot.command(name='เช็คคำสั่ง')
async def check_commands(ctx):
    help_text = (
        "📌 **คำสั่งของบอท Boss Timer**\n\n"
        "🔹 `!เพิ่มบอส` - เริ่มขั้นตอนเพิ่มบอสแบบโต้ตอบ\n"
        "🔹 `!แก้ไขบอส <ชื่อบอส>` - แก้ไขข้อมูลบอสที่ตั้งไว้\n"
        "🔹 `!ลบบอส <ชื่อบอส>` - ลบบอสตามชื่อที่ตั้งไว้\n"
        "🔹 `!เช็คบอส` - ดูรายชื่อบอสทั้งหมดที่ตั้งเวลาไว้\n"
        "🔹 `!เปิดเสียง` / `!ปิดเสียง` - เปิด/ปิดการแจ้งเตือน\n"
        "🔹 `!CHID <Channel ID>` - เปลี่ยน Channel ID ที่บอทจะส่งข้อความไป\n"
    )
    await ctx.send(help_text)

# ====================== เริ่มรันบอท ======================
@bot.event
async def on_ready():
    print(f'✅ บอทออนไลน์ในชื่อ: {bot.user}')
    check_bosses.start()

server_on

bot.run(os.getenv('TOKEN'))
