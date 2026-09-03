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

# --- YETKİ DENETİM YARDIMCILARI ---
def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == interaction.guild.owner_id

def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    if interaction.user.id == interaction.guild.owner_id:
        return True
    admin_role = discord.utils.get(interaction.guild.roles, name="🛠️ Admin")
    return admin_role in interaction.user.roles if admin_role else False

def is_staff(interaction: discord.Interaction) -> bool:
    if is_admin_or_owner(interaction):
        return True
    mod_role = discord.utils.get(interaction.guild.roles, name="🛡️ Moderator")
    return mod_role in interaction.user.roles if mod_role else False

# --- ARAYÜZ (VIEWS) ---
class RuleAcceptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Accept Rules / Kuralları Kabul Et", style=discord.ButtonStyle.success, custom_id="accept_rules_btn")
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        gamer_role = discord.utils.get(guild.roles, name="🎮 Gamer")
        
        if gamer_role:
            if gamer_role in member.roles:
                await interaction.response.send_message("Zaten kuralları kabul ettiniz! / You have already accepted the rules!", ephemeral=True)
            else:
                await member.add_roles(gamer_role)
                await interaction.response.send_message("🎉 Kuralları kabul ettiniz! Sunucuya erişiminiz açıldı. / Rules accepted! Full access granted.", ephemeral=True)
                await log_event(guild, "✅ Kurallar Kabul Edildi", f"**Üye:** {member.mention}", discord.Color.green())
        else:
            await interaction.response.send_message("❌ '🎮 Gamer' rolü bulunamadı. Lütfen yetkililere bildirin.", ephemeral=True)

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
    bot.add_view(RuleAcceptView())
    bot.add_view(TicketView())
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print("✅ Slash komutları ve Persistent View'lar yüklendi!")
    except Exception as e:
        print(f"Hata: {e}")

@bot.event
async def on_member_join(member):
    guild = member.guild
    welcome_channel = discord.utils.get(guild.channels, name="welcome")
    if welcome_channel:
        embed = discord.Embed(
            title="🎉 Welcome to Apexium Community!",
            description=f"Welcome {member.mention}!\nTo gain full access to channels, please read and accept the rules in the `#rules` channel.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed)
    
    await log_event(guild, "📥 Yeni Üye Katıldı", f"**Üye:** {member.mention} ({member.tag})", discord.Color.blue())

# --- KOMUTLAR ---

# 1. /sunucukur (Sadece OWNER)
@bot.tree.command(name="sunucukur", description="Var olan kanalları siler ve sunucu yapısını baştan kurar.")
@app_commands.default_permissions(administrator=True)
async def setup_server(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if not is_owner(interaction):
        msg = "❌ Bu komutu sadece **Sunucu Sahibi (Owner)** kullanabilir!" if lang == 'tr' else "❌ Only the **Server Owner** can use this command!"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    for channel in guild.channels:
        try:
            await channel.delete()
        except Exception:
            pass

    owner_role = discord.utils.get(guild.roles, name="👑 Owner") or await guild.create_role(name="👑 Owner", permissions=discord.Permissions.all(), color=discord.Color.gold(), hoist=True)
    
    admin_perms = discord.Permissions(
        manage_channels=True, manage_roles=True, kick_members=True, ban_members=True,
        manage_messages=True, read_messages=True, send_messages=True, connect=True, speak=True
    )
    admin_role = discord.utils.get(guild.roles, name="🛠️ Admin") or await guild.create_role(name="🛠️ Admin", permissions=admin_perms, color=discord.Color.red(), hoist=True)

    mod_perms = discord.Permissions(
        manage_messages=True, mute_members=True, deafen_members=True,
        read_messages=True, send_messages=True, connect=True, speak=True
    )
    mod_role = discord.utils.get(guild.roles, name="🛡️ Moderator") or await guild.create_role(name="🛡️ Moderator", permissions=mod_perms, color=discord.Color.blue(), hoist=True)

    player_role = discord.utils.get(guild.roles, name="🎮 Gamer") or await guild.create_role(name="🎮 Gamer", permissions=discord.Permissions.general(), color=discord.Color.green(), hoist=True)

    try:
        await interaction.user.add_roles(owner_role)
    except Exception:
        pass

    # KANAL İZİNLERİ HİYERARŞİSİ
    public_read_only = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
        player_role: discord.PermissionOverwrite(send_messages=False, read_messages=True)
    }

    gamer_access = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        player_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    staff_only_text = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        player_role: discord.PermissionOverwrite(read_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    owner_admin_voice = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        player_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    staff_voice = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        player_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        mod_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    # KATEGORİ VEYA KANALLARIN OLUŞTURULMASI
    info_cat = await guild.create_category("INFORMATION")
    await info_cat.create_text_channel("welcome", overwrites=public_read_only)
    rules_ch = await info_cat.create_text_channel("rules", overwrites=public_read_only)
    await info_cat.create_text_channel("announcements", overwrites=public_read_only)
    await info_cat.create_text_channel("updates", overwrites=public_read_only)
    await info_cat.create_text_channel("logs", overwrites=staff_only_text)
    await info_cat.create_text_channel("staff-commands", overwrites=staff_only_text)

    # Otomatik Kurallar & Onay Mesajını Gönder
    rules_embed = discord.Embed(
        title="📜 Server Rules & Verification / Sunucu Kuralları",
        description="1. Respect all members / Tüm üyelere saygılı olun.\n"
                    "2. No spam or advertising / Spam ve reklam yasaktır.\n"
                    "3. Follow Discord ToS / Discord kullanım şartlarına uyun.\n\n"
                    "Aşağıdaki **Accept Rules** butonuna basarak tüm kanallara erişim sağlayabilirsiniz.",
        color=discord.Color.gold()
    )
    await rules_ch.send(embed=rules_embed, view=RuleAcceptView())

    comm_cat = await guild.create_category("COMMUNITY")
    await comm_cat.create_text_channel("general-chat", overwrites=gamer_access)
    await comm_cat.create_text_channel("media-share", overwrites=gamer_access)
    await comm_cat.create_text_channel("bot-commands", overwrites=gamer_access)

    supp_cat = await guild.create_category("SUPPORT & FEEDBACK")
    await supp_cat.create_text_channel("bug-reports", overwrites=gamer_access)
    await supp_cat.create_text_channel("suggestions", overwrites=gamer_access)
    ticket_channel = await supp_cat.create_text_channel("create-ticket", overwrites=gamer_access)

    ticket_embed = discord.Embed(
        title="🎮 Game Support System",
        description="Sorunlarınız ve iletişim için bilet oluşturun / Click below to open a support ticket.",
        color=discord.Color.blue()
    )
    await ticket_channel.send(embed=ticket_embed, view=TicketView())

    voice_cat = await guild.create_category("VOICE CHANNELS")
    await voice_cat.create_voice_channel("Public Lounge", overwrites=gamer_access)
    await voice_cat.create_voice_channel("Squad 1", overwrites=gamer_access)
    await voice_cat.create_voice_channel("🔒 Staff Voice", overwrites=staff_voice)
    await voice_cat.create_voice_channel("🔒 Owner & Admin Voice", overwrites=owner_admin_voice)

    succ_msg = "✅ İngilizce kanal yapısı, yetkili ses odaları ve kural kabul sistemi kuruldu!" if lang == 'tr' else "✅ English channels, staff voice rooms and rule verification system setup complete!"
    try:
        await interaction.followup.send(succ_msg, ephemeral=True)
    except Exception:
        pass

# 2. /duyuru (ADMIN / OWNER)
@bot.tree.command(name="duyuru", description="Duyurular kanalına görsel ve açıklamalı duyuru gönderir.")
@app_commands.default_permissions(administrator=True)
async def announce(interaction: discord.Interaction, title: str, message: str, image_url: str = None):
    lang = get_lang(interaction.user.id)
    if not is_admin_or_owner(interaction):
        msg = "❌ Bu komutu sadece **Admin** veya **Owner** kullanabilir!" if lang == 'tr' else "❌ Only **Admin** or **Owner** can use this command!"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    ann_channel = discord.utils.get(interaction.guild.channels, name="announcements")
    if not ann_channel:
        await interaction.response.send_message("❌ `#announcements` kanalı bulunamadı.", ephemeral=True)
        return

    embed = discord.Embed(title=f"📢 {title}", description=message, color=discord.Color.gold())
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text=f"Posted by {interaction.user.display_name}")

    await ann_channel.send(content="@everyone", embed=embed)
    await interaction.response.send_message("✅ Duyuru başarıyla gönderildi!", ephemeral=True)
    await log_event(interaction.guild, "📢 Duyuru Paylaşıldı", f"**Başlık:** {title}\n**Yetkili:** {interaction.user.mention}", discord.Color.gold())

# 3. /kurallar (ADMIN / OWNER)
@bot.tree.command(name="kurallar", description="#rules kanalına kural mesajını ve onay butonunu yeniden yollar.")
@app_commands.default_permissions(administrator=True)
async def post_rules(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if not is_admin_or_owner(interaction):
        msg = "❌ Bu komutu sadece **Admin** veya **Owner** kullanabilir!" if lang == 'tr' else "❌ Only **Admin** or **Owner** can use this command!"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    rules_ch = discord.utils.get(interaction.guild.channels, name="rules")
    if not rules_ch:
        await interaction.response.send_message("❌ `#rules` kanalı bulunamadı.", ephemeral=True)
        return

    rules_embed = discord.Embed(
        title="📜 Server Rules & Verification / Sunucu Kuralları",
        description="1. Respect all members / Tüm üyelere saygılı olun.\n"
                    "2. No spam or advertising / Spam ve reklam yasaktır.\n"
                    "3. Follow Discord ToS / Discord kullanım şartlarına uyun.\n\n"
                    "Aşağıdaki **Accept Rules** butonuna basarak tüm kanallara erişim sağlayabilirsiniz.",
        color=discord.Color.gold()
    )
    await rules_ch.send(embed=rules_embed, view=RuleAcceptView())
    await interaction.response.send_message("✅ Kural paneli gönderildi!", ephemeral=True)

# 4. /ban (ADMIN / OWNER)
@bot.tree.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Bu komut için **Admin** veya **Owner** olmalısınız!", ephemeral=True)
        return
    await member.ban(reason=reason)
    msg = f"🚫 {member.mention} sunucudan yasaklandı." if lang == 'tr' else f"🚫 {member.mention} has been banned."
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "🔨 Ban Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.red())

# 5. /kick (ADMIN / OWNER)
@bot.tree.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Bu komut için **Admin** veya **Owner** olmalısınız!", ephemeral=True)
        return
    await member.kick(reason=reason)
    msg = f"👞 {member.mention} sunucudan atıldı." if lang == 'tr' else f"👞 {member.mention} has been kicked."
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "👞 Kick Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.orange())

# 6. /mute (MOD / ADMIN / OWNER)
@bot.tree.command(name="mute", description="Bir kullanıcıyı belirli bir süre susturur (dakika).")
@app_commands.default_permissions(moderate_members=True)
async def mute_user(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    msg = f"🤐 {member.mention} **{minutes} dakika** boyunca susturuldu." if lang == 'tr' else f"🤐 {member.mention} muted for **{minutes} minutes**."
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "🤐 Mute Event", f"**User:** {member.mention}\n**Duration:** {minutes} Min\n**Staff:** {interaction.user.mention}", discord.Color.gold())

# 7. /unmute (MOD / ADMIN / OWNER)
@bot.tree.command(name="unmute", description="Bir kullanıcının susturmasını kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def unmute_user(interaction: discord.Interaction, member: discord.Member):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.timeout(None)
    msg = f"🔊 {member.mention} kullanıcısının susturması kaldırıldı." if lang == 'tr' else f"🔊 {member.mention} unmuted."
    await interaction.response.send_message(msg, ephemeral=True)
    await log_event(interaction.guild, "🔊 Unmute Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}", discord.Color.green())

# 8. /lock (MOD / ADMIN / OWNER)
@bot.tree.command(name="lock", description="Komutun yazıldığı kanala mesaj gönderimini kilitler.")
@app_commands.default_permissions(manage_channels=True)
async def lock_channel(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    msg = "🔒 Bu kanal mesaj gönderimine kilitlendi." if lang == 'tr' else "🔒 Channel locked."
    await interaction.response.send_message(msg)
    await log_event(interaction.guild, "🔒 Lock Event", f"**Channel:** {channel.mention}\n**Staff:** {interaction.user.mention}", discord.Color.dark_red())

# 9. /unlock (MOD / ADMIN / OWNER)
@bot.tree.command(name="unlock", description="Kilitli kanalı tekrar mesaj gönderimine açar.")
@app_commands.default_permissions(manage_channels=True)
async def unlock_channel(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    channel = interaction.channel
    overwrite = channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    msg = "🔓 Kanal kilidi açıldı." if lang == 'tr' else "🔓 Channel unlocked."
    await interaction.response.send_message(msg)
    await log_event(interaction.guild, "🔓 Unlock Event", f"**Channel:** {channel.mention}\n**Staff:** {interaction.user.mention}", discord.Color.green())

# 10. /sil (MOD / ADMIN / OWNER)
@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı kanaldan siler.")
@app_commands.default_permissions(manage_messages=True)
async def purge_messages(interaction: discord.Interaction, amount: int):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ Lütfen 1-100 arası bir sayı girin.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    msg = f"🗑️ **{len(deleted)}** mesaj silindi." if lang == 'tr' else f"🗑️ **{len(deleted)}** messages deleted."
    await interaction.followup.send(msg, ephemeral=True)
    await log_event(interaction.guild, "🗑️ Purge Event", f"**Channel:** {interaction.channel.mention}\n**Count:** {len(deleted)}\n**Staff:** {interaction.user.mention}", discord.Color.purple())

# 11. /help (GAMER / HERKES)
@bot.tree.command(name="help", description="Sunucu kullanım rehberi ve komut listesi.")
async def help_command(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if lang == 'en':
        embed = discord.Embed(
            title="🎮 Apexium Gamer Guide",
            description="Welcome to the server! Here is a guide to get you started:",
            color=discord.Color.green()
        )
        embed.add_field(name="📜 1. Verification", value="Go to `#rules` and click **Accept Rules** to unlock all channels.", inline=False)
        embed.add_field(name="🌐 2. Language", value="Type `/language` to switch between Turkish & English.", inline=False)
        embed.add_field(name="📩 3. Support", value="Open a ticket in `#create-ticket` if you need help from staff.", inline=False)
        embed.add_field(name="🏓 4. Commands", value="`/ping` - Check latency\n`/help` - Open this guide", inline=False)
    else:
        embed = discord.Embed(
            title="🎮 Apexium Oyuncu Rehberi",
            description="Sunucumuza hoş geldiniz! İşte başlangıç için kullanabileceğiniz rehber:",
            color=discord.Color.green()
        )
        embed.add_field(name="📜 1. Sunucu Kaydı", value="`#rules` kanalına gidip **Accept Rules** butonuna basarak tüm kanalları açın.", inline=False)
        embed.add_field(name="🌐 2. Dil Seçimi", value="`/language` yazarak bot dilini Türkçe veya İngilizce yapabilirsiniz.", inline=False)
        embed.add_field(name="📩 3. Destek & İletişim", value="Bir sorun yaşarsanız `#create-ticket` kanalından destek talebi açabilirsiniz.", inline=False)
        embed.add_field(name="🏓 4. Kullanılabilir Komutlar", value="`/ping` - Bot gecikmesini ölçer\n`/help` - Bu rehber menüsünü açar", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# 12. Genel Komutlar
@bot.tree.command(name="language", description="Select your language / Dilinizi seçin")
async def language(interaction: discord.Interaction):
    await interaction.response.send_message("Lütfen dil seçin / Please select a language:", view=LanguageSelectView(), ephemeral=True)

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir.")
async def ping(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    ms = round(bot.latency * 1000)
    msg = f"🏓 Pong! Latency: **{ms}ms**" if lang == 'en' else f"🏓 Pong! Gecikme Süresi: **{ms}ms**"
    await interaction.response.send_message(msg, ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN") or "MTU0NDY5OTM3OTA5OTc3MDg5Mg.GLxPNK.zX5pectcQSndVdHhUNVGitM9V5GqD_kWGQ5L_0"

keep_alive()
bot.run(TOKEN)
