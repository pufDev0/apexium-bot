import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
from datetime import timedelta
from flask import Flask
from threading import Thread

# --- RENDER WEB SUNUCUSU ---
app = Flask('')

@app.route('/')
def home():
    return "Apexium Bot 7/24 Online!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- DISCORD BOT AYARLARI ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_languages = {}

def get_lang(user_id):
    return user_languages.get(user_id, 'tr')

async def log_event(guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.blue()):
    log_channel = discord.utils.get(guild.channels, name="logs")
    if log_channel:
        embed = discord.Embed(title=title, description=description, color=color)
        await log_channel.send(embed=embed)

# --- ARAYÜZ (VIEWS) ---
class LanguageSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Türkçe 🇹🇷", style=discord.ButtonStyle.primary)
    async def turkish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_languages[interaction.user.id] = 'tr'
        await interaction.response.send_message("Dil tercihiniz **Türkçe** olarak ayarlandı!", ephemeral=True)

    @discord.ui.button(label="English 🇬🇧", style=discord.ButtonStyle.secondary)
    async def english_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_languages[interaction.user.id] = 'en'
        await interaction.response.send_message("Your language has been set to **English**!", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Create Ticket / Bilet Aç", style=discord.ButtonStyle.success, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        lang = get_lang(user.id)

        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            msg = "Zaten açık bir destek talebiniz var: " if lang == 'tr' else "You already have an open ticket: "
            await interaction.response.send_message(f"{msg}{existing_channel.mention}", ephemeral=True)
            return

        admin_role = discord.utils.get(guild.roles, name="🛠️ Admin")
        mod_role = discord.utils.get(guild.roles, name="🛡️ Moderator")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if admin_role: overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if mod_role: overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        res_msg = "Destek kanalınız oluşturuldu: " if lang == 'tr' else "Your ticket channel has been created: "
        await interaction.response.send_message(f"{res_msg}{ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title="Support / Destek Talebi",
            description=f"Merhaba {user.mention}, yetkililer en kısa sürede sizinle ilgilenecektir.\nDestek talebini kapatmak için aşağıdaki butona basabilirsiniz." if lang == 'tr' else f"Hello {user.mention}, staff will assist you shortly.\nClick below to close the ticket.",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=embed, view=CloseTicketView())
        await log_event(guild, "🎟️ Destek Talebi Açıldı", f"**Kullanıcı:** {user.mention}\n**Kanal:** {ticket_channel.mention}", discord.Color.green())

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close / Kapat", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        lang = get_lang(interaction.user.id)
        msg = "Kanal 5 saniye içinde silinecektir..." if lang == 'tr' else "Channel will be deleted in 5 seconds..."
        await interaction.response.send_message(msg)
        await log_event(interaction.guild, "🔒 Destek Talebi Kapatıldı", f"**Kapatan:** {interaction.user.mention}\n**Kanal:** {interaction.channel.name}", discord.Color.red())
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- BOT ETKİNLİKLERİ ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} olarak giriş yaptı!')
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print("✅ Slash komutları sunucuya özel anında yüklendi!")
    except Exception as e:
        print(f"Hata: {e}")

@bot.event
async def on_member_join(member):
    guild = member.guild
    player_role = discord.utils.get(guild.roles, name="🎮 Gamer")
    if player_role:
        try:
            await member.add_roles(player_role)
        except Exception:
            pass

    welcome_channel = discord.utils.get(guild.channels, name="welcome")
    if welcome_channel:
        embed = discord.Embed(
            title="🎉 Sunucuya Hoş Geldin! / Welcome!",
            description=f"Selam {member.mention}! Oyunumuzun resmi Discord sunucusuna hoş geldin.\n"
                        f"Kayıt olmak için sohbet kanallarına `/language` yazarak dilini seçebilirsin.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed)
    
    await log_event(guild, "📥 Yeni Üye Katıldı", f"**Üye:** {member.mention} ({member.tag})", discord.Color.blue())

# --- KOMUTLAR ---

# Sadece Sunucu Sahibi (Owner) Kullanabilir
@bot.tree.command(name="sunucukur", description="Var olan kanalları siler ve sunucu yapısını baştan kurar.")
async def setup_server(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if interaction.user.id != interaction.guild.owner_id:
        err_msg = "❌ Bu komutu sadece **Sunucu Sahibi (Owner)** kullanabilir!" if lang == 'tr' else "❌ Only the **Server Owner** can use this command!"
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    for channel in guild.channels:
        try:
            await channel.delete()
        except Exception:
            pass

    owner_role = discord.utils.get(guild.roles, name="👑 Owner")
    if not owner_role:
        owner_role = await guild.create_role(name="👑 Owner", permissions=discord.Permissions.all(), color=discord.Color.gold(), hoist=True)

    admin_perms = discord.Permissions(
        manage_channels=True, manage_roles=True, kick_members=True, ban_members=True,
        manage_messages=True, read_messages=True, send_messages=True, connect=True, speak=True
    )
    admin_role = discord.utils.get(guild.roles, name="🛠️ Admin")
    if not admin_role:
        admin_role = await guild.create_role(name="🛠️ Admin", permissions=admin_perms, color=discord.Color.red(), hoist=True)

    mod_perms = discord.Permissions(
        manage_messages=True, mute_members=True, deafen_members=True,
        read_messages=True, send_messages=True, connect=True, speak=True
    )
    mod_role = discord.utils.get(guild.roles, name="🛡️ Moderator")
    if not mod_role:
        mod_role = await guild.create_role(name="🛡️ Moderator", permissions=mod_perms, color=discord.Color.blue(), hoist=True)

    player_role = discord.utils.get(guild.roles, name="🎮 Gamer")
    if not player_role:
        player_role = await guild.create_role(name="🎮 Gamer", permissions=discord.Permissions.general(), color=discord.Color.green(), hoist=True)

    try:
        await interaction.user.add_roles(owner_role)
    except Exception:
        pass

    read_only_for_everyone = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
        admin_role: discord.PermissionOverwrite(send_messages=True, read_messages=True),
        owner_role: discord.PermissionOverwrite(send_messages=True, read_messages=True)
    }

    staff_only_logs = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    admin_only_voice = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        mod_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    info_cat = await guild.create_category("INFORMATION")
    await info_cat.create_text_channel("welcome", overwrites=read_only_for_everyone)
    await info_cat.create_text_channel("rules", overwrites=read_only_for_everyone)
    await info_cat.create_text_channel("announcements", overwrites=read_only_for_everyone)
    await info_cat.create_text_channel("updates", overwrites=read_only_for_everyone)
    await info_cat.create_text_channel("logs", overwrites=staff_only_logs)

    comm_cat = await guild.create_category("COMMUNITY")
    await comm_cat.create_text_channel("general-chat")
    await comm_cat.create_text_channel("media-share")
    await comm_cat.create_text_channel("bot-commands")

    supp_cat = await guild.create_category("SUPPORT & FEEDBACK")
    await supp_cat.create_text_channel("bug-reports")
    await supp_cat.create_text_channel("suggestions")
    ticket_channel = await supp_cat.create_text_channel("create-ticket")

    embed = discord.Embed(
        title="🎮 Game Support System",
        description="Sorunlarınız, yetkili iletişimleri veya özel bildirimleriniz için aşağıdan bilet oluşturun.\nClick below to open a support ticket.",
        color=discord.Color.blue()
    )
    await ticket_channel.send(embed=embed, view=TicketView())

    voice_cat = await guild.create_category("VOICE CHANNELS")
    await voice_cat.create_voice_channel("Public Lounge")
    await voice_cat.create_voice_channel("Squad 1")
    await voice_cat.create_voice_channel("🔒 Admin Private Voice", overwrites=admin_only_voice)

    succ_msg = "✅ Sunucu yapısı, gizli #logs kanalı ve tüm roller başarıyla kuruldu!" if lang == 'tr' else "✅ Server structure, secret #logs channel and all roles created successfully!"
    try:
        await interaction.followup.send(succ_msg, ephemeral=True)
    except Exception:
        pass

# --- MODERASYON KOMUTLARI (ADMIN / OWNER KONTROLLÜ) ---

@bot.tree.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    await member.ban(reason=reason)
    msg = f"🚫 {member.mention} sunucudan yasaklandı. Sebep: **{reason}**" if lang == 'tr' else f"🚫 {member.mention} has been banned. Reason: **{reason}**"
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "🔨 Ban Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.red())

@bot.tree.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    await member.kick(reason=reason)
    msg = f"👞 {member.mention} sunucudan atıldı. Sebep: **{reason}**" if lang == 'tr' else f"👞 {member.mention} has been kicked. Reason: **{reason}**"
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "👞 Kick Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.orange())

@bot.tree.command(name="mute", description="Bir kullanıcıyı belirli bir süre susturur (dakika).")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute_user(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    msg = f"🤐 {member.mention} **{minutes} dakika** boyunca susturuldu." if lang == 'tr' else f"🤐 {member.mention} has been muted for **{minutes} minutes**."
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "🤐 Mute Event", f"**User:** {member.mention}\n**Duration:** {minutes} Min\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.gold())

@bot.tree.command(name="unmute", description="Bir kullanıcının susturmasını kaldırır.")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute_user(interaction: discord.Interaction, member: discord.Member):
    lang = get_lang(interaction.user.id)
    await member.timeout(None)
    msg = f"🔊 {member.mention} kullanıcısının susturması kaldırıldı." if lang == 'tr' else f"🔊 {member.mention} has been unmuted."
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "🔊 Unmute Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}", discord.Color.green())

@bot.tree.command(name="lock", description="Komutun yazıldığı kanala mesaj gönderimini kilitler.")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock_channel(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    msg = "🔒 Bu kanal mesaj gönderimine kilitlendi." if lang == 'tr' else "🔒 This channel has been locked."
    await interaction.response.send_message(msg)
    await log_event(interaction.guild, "🔒 Lock Event", f"**Channel:** {channel.mention}\n**Staff:** {interaction.user.mention}", discord.Color.dark_red())

@bot.tree.command(name="unlock", description="Kilitli kanalı tekrar mesaj gönderimine açar.")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock_channel(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    msg = "🔓 Kanal kilidi açıldı." if lang == 'tr' else "🔓 Channel has been unlocked."
    await interaction.response.send_message(msg)
    await log_event(interaction.guild, "🔓 Unlock Event", f"**Channel:** {channel.mention}\n**Staff:** {interaction.user.mention}", discord.Color.green())

@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı kanaldan siler.")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge_messages(interaction: discord.Interaction, amount: int):
    lang = get_lang(interaction.user.id)
    if amount < 1 or amount > 100:
        err_msg = "❌ Lütfen 1 ile 100 arasında bir sayı girin." if lang == 'tr' else "❌ Please enter a number between 1 and 100."
        await interaction.response.send_message(err_msg, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    succ_msg = f"🗑️ **{len(deleted)}** adet mesaj silindi." if lang == 'tr' else f"🗑️ **{len(deleted)}** messages deleted."
    await interaction.followup.send(succ_msg, ephemeral=True)
    await log_event(interaction.guild, "🗑️ Mesaj Silindi (Purge)", f"**Kanal:** {interaction.channel.mention}\n**Silinen Adet:** {len(deleted)}\n**Yetkili:** {interaction.user.mention}", discord.Color.purple())

# Yetki Hataları Yönetimi (Moderatörlerin Admin Komutlarını Kullanmasını Engeller)
@ban_user.error
@kick_user.error
@lock_channel.error
@unlock_channel.error
@purge_messages.error
async def admin_perm_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        lang = get_lang(interaction.user.id)
        msg = "❌ Bu komutu kullanmak için **Admin** veya **Owner** yetkisine sahip olmalısınız!" if lang == 'tr' else "❌ You need **Admin** or **Owner** permissions to use this command!"
        await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="language", description="Select your language / Dilinizi seçin")
async def language(interaction: discord.Interaction):
    await interaction.response.send_message("Lütfen dil seçin / Please select a language:", view=LanguageSelectView(), ephemeral=True)

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir.")
async def ping(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    ms = round(bot.latency * 1000)
    if lang == 'en':
        await interaction.response.send_message(f"🏓 Pong! Latency: **{ms}ms**", ephemeral=True)
    else:
        await interaction.response.send_message(f"🏓 Pong! Gecikme Süresi: **{ms}ms**", ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN") or "MTU0NDY5OTM3OTA5OTc3MDg5Mg.GLxPNK.zX5pectcQSndVdHhUNVGitM9V5GqD_kWGQ5L_0"

keep_alive()
bot.run(TOKEN)
