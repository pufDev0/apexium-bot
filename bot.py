import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from datetime import timedelta, datetime, timezone
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
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_languages = {}

DEFAULT_ANNOUNCEMENT_BANNER = "https://raw.githubusercontent.com/pufDev0/apexium-bot/main/announcement_banner.jpg"
DOWNLOAD_GAME_BANNER = "https://raw.githubusercontent.com/pufDev0/apexium-bot/main/download_banner.jpg"
GAME_ITCH_LINK = "https://pufdev.itch.io/apexiumtrial"

def get_lang(user_id):
    return user_languages.get(user_id, 'tr')

async def log_event(guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.blue()):
    log_channel = discord.utils.get(guild.channels, name="logs")
    if log_channel:
        embed = discord.Embed(title=f"🛡️ AUDIT LOG | {title}", description=description, color=color)
        embed.timestamp = datetime.now(timezone.utc)
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
class DownloadGameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🚀 Play Apexium Trial (itch.io)", url=GAME_ITCH_LINK, style=discord.ButtonStyle.link))

class CountrySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Select your Country / Ülkenizi Seçin...",
        custom_id="country_select_menu",
        options=[
            discord.SelectOption(label="Turkey 🇹🇷", value="TR", emoji="🇹🇷", description="Türkçe / Turkish Language"),
            discord.SelectOption(label="United Kingdom 🇬🇧", value="UK", emoji="🇬🇧", description="English / İngilizce"),
            discord.SelectOption(label="United States 🇺🇸", value="US", emoji="🇺🇸", description="English / İngilizce"),
            discord.SelectOption(label="Germany 🇩🇪", value="DE", emoji="🇩🇪", description="German / Almanca"),
            discord.SelectOption(label="France 🇫🇷", value="FR", emoji="🇫🇷", description="French / Fransızca"),
            discord.SelectOption(label="Spain 🇪🇸", value="ES", emoji="🇪🇸", description="Spanish / İspanyolca")
        ]
    )
    async def select_country(self, interaction: discord.Interaction, select: discord.ui.Select):
        val = select.values[0]
        guild = interaction.guild
        member = interaction.user

        country_roles = {
            "TR": "🇹🇷 Turkey", "UK": "🇬🇧 United Kingdom", "US": "🇺🇸 United States",
            "DE": "🇩🇪 Germany", "FR": "🇫🇷 France", "ES": "🇪🇸 Spain"
        }
        
        role_name = country_roles.get(val, "🇹🇷 Turkey")
        role = discord.utils.get(guild.roles, name=role_name) or await guild.create_role(name=role_name, color=discord.Color.blue())
        
        user_languages[member.id] = 'tr' if val == 'TR' else 'en'
        await member.add_roles(role)

        gamer_l1 = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer")
        if gamer_l1 and gamer_l1 not in member.roles:
            await member.add_roles(gamer_l1)

        msg = f"✅ **{role_name}** rolü tanımlandı! Access granted." if val == 'TR' else f"✅ Assigned **{role_name}** role! Access granted."
        await interaction.response.send_message(msg, ephemeral=True)
        await log_event(guild, "🌐 Ülke/Dil Seçildi", f"**Üye:** {member.mention}\n**Ülke:** {role_name}", discord.Color.blue())

class RuleAcceptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Accept Rules / Kuralları Kabul Et", style=discord.ButtonStyle.success, custom_id="accept_rules_btn")
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        gamer_role = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer")
        
        if gamer_role:
            if gamer_role in member.roles:
                await interaction.response.send_message("✨ Zaten kuralları kabul ettiniz! / You have already accepted the rules!", ephemeral=True)
            else:
                await member.add_roles(gamer_role)
                embed = discord.Embed(
                    title="🎉 Access Granted / Erişim Onaylandı!",
                    description="Kuralları kabul ettiğin için teşekkürler! Lütfen `#welcome` kanalından ülkeni seç.\n\nThank you for accepting the rules! Please select your country in `#welcome`.",
                    color=discord.Color.brand_green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                await log_event(guild, "✅ Kurallar Kabul Edildi", f"**Üye:** {member.mention}", discord.Color.green())

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
            title="🎫 Support Desk / Destek Masası",
            description=f"Merhaba {user.mention}, yetkililerimiz en kısa sürede sizinle ilgilenecektir.\n\nHello {user.mention}, our staff will assist you shortly.",
            color=discord.Color.teal()
        )
        embed.set_footer(text="Destek talebini kapatmak için aşağıdaki butona basabilirsiniz.")
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

# --- SÜREYE DAYALI LEVEL GÜNCELLEME DÖNGÜSÜ ---
@tasks.loop(hours=12)
async def check_member_levels():
    for guild in bot.guilds:
        l1_role = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer")
        l2_role = discord.utils.get(guild.roles, name="⚡ Level 2 Gamer")
        l3_role = discord.utils.get(guild.roles, name="🔥 Level 3 Gamer")
        master_role = discord.utils.get(guild.roles, name="👑 Master Gamer")

        now = datetime.now(timezone.utc)
        for member in guild.members:
            if member.bot or not member.joined_at:
                continue
            
            days = (now - member.joined_at).days

            # 1 Yıl
            if days >= 365 and master_role and master_role not in member.roles:
                await member.add_roles(master_role)
                if l3_role in member.roles: await member.remove_roles(l3_role)
                await log_event(guild, "👑 Level Up! (Master Gamer)", f"**Kullanıcı:** {member.mention}\n**Sunucuda Süre:** {days} Gün", discord.Color.gold())
            # 1 Ay (30 gün)
            elif days >= 30 and days < 365 and l3_role and l3_role not in member.roles:
                await member.add_roles(l3_role)
                if l2_role in member.roles: await member.remove_roles(l2_role)
                await log_event(guild, "🔥 Level Up! (Level 3)", f"**Kullanıcı:** {member.mention}\n**Sunucuda Süre:** {days} Gün", discord.Color.purple())
            # 1 Hafta (7 gün)
            elif days >= 7 and days < 30 and l2_role and l2_role not in member.roles:
                await member.add_roles(l2_role)
                if l1_role in member.roles: await member.remove_roles(l1_role)
                await log_event(guild, "⚡ Level Up! (Level 2)", f"**Kullanıcı:** {member.mention}\n**Sunucuda Süre:** {days} Gün", discord.Color.blue())

# --- BOT ETKİNLİKLERİ VE DETAYLI LOGLAR ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} olarak giriş yaptı!')
    bot.add_view(RuleAcceptView())
    bot.add_view(TicketView())
    bot.add_view(DownloadGameView())
    bot.add_view(CountrySelectView())
    check_member_levels.start()
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print("✅ Slash komutları ve Otomatik Level sistemi yüklendi!")
    except Exception as e:
        print(f"Hata: {e}")

@bot.event
async def on_member_join(member):
    guild = member.guild
    welcome_channel = discord.utils.get(guild.channels, name="welcome")
    if welcome_channel:
        embed = discord.Embed(
            title=f"✨ WELCOME TO {guild.name.upper()}! ✨",
            description=f"Hoş geldin {member.mention}!\n\nLütfen aşağıdan ülkenizi/dili seçin.\nPlease select your country/language below to unlock the server.",
            color=discord.Color.gold()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_image(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed, view=CountrySelectView())
    
    await log_event(guild, "📥 Üye Katıldı", f"**Üye:** {member.mention} ({member.tag})\n**Hesap Oluşturulma:** {member.created_at.strftime('%d.%m.%Y')}", discord.Color.blue())

@bot.event
async def on_member_remove(member):
    await log_event(member.guild, "📤 Üye Ayrıldı / Atıldı", f"**Üye:** {member.mention} ({member.tag})", discord.Color.dark_orange())

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    content = message.content if message.content else "*Görsel/Dosya*"
    await log_event(message.guild, "🗑️ Mesaj Silindi", f"**Yazar:** {message.author.mention}\n**Kanal:** {message.channel.mention}\n**İçerik:** {content}", discord.Color.red())

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    await log_event(before.guild, "✏️ Mesaj Düzenlendi", f"**Yazar:** {before.author.mention}\n**Kanal:** {before.channel.mention}\n**Önce:** {before.content}\n**Sonra:** {after.content}", discord.Color.orange())

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added = [r.mention for r in after.roles if r not in before.roles]
        removed = [r.mention for r in before.roles if r not in after.roles]
        desc = f"**Üye:** {after.mention}\n"
        if added: desc += f"**Eklendi:** {', '.join(added)}\n"
        if removed: desc += f"**Kaldırıldı:** {', '.join(removed)}"
        await log_event(after.guild, "🛡️ Rol / Yetki Değişti", desc, discord.Color.gold())

@bot.event
async def on_invite_create(invite):
    await log_event(invite.guild, "🔗 Davet Linki Oluşturuldu", f"**Oluşturan:** {invite.inviter.mention}\n**Kod:** `{invite.code}`\n**Kanal:** {invite.channel.mention}", discord.Color.light_grey())

def create_rules_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=f"📜 {guild.name} — OFFICIAL RULES / SUNUCU KURALLARI",
        description="Sunucumuzda keyifli ve güvenli bir ortam sağlamak için aşağıdaki kurallara uymanız zorunludur.\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=discord.Color.gold()
    )
    if guild.icon:
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(
        name="1️⃣ Saygı ve İletişim / Respect & Conduct",
        value="• Her ne koşulda olursa olsun **KÜFÜR, ARGO, HAKARET ve AŞAĞILAYICI DİL YASAKTIR**.\n"
              "• Absolutely NO profanity, offensive language, insults, or toxicity allowed.",
        inline=False
    )
    embed.add_field(
        name="2️⃣ Spam ve Reklam / Spam & Self-Promotion",
        value="• Reklam yapmak, DM yoluyla dahi davet linki atmak kesinlikle ban sebebidir.\n"
              "• No spamming, mass tagging, or unauthorized promotions/links.",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Discord Topluluk Kuralları / Discord ToS",
        value="• Discord Hizmet Şartlarına ve Topluluk İlkelerine tam uyum zorunludur.\n"
              "• Comply with all Official Discord Terms of Service.",
        inline=False
    )
    embed.add_field(
        name="✅ Verification / Onay",
        value="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
              "Aşağıdaki **Accept Rules / Kuralları Kabul Et** butonuna basarak tüm sunucuya erişim sağlayabilirsiniz.",
        inline=False
    )
    embed.set_footer(text="Apexium Security System • Rules Enforcement", icon_url=bot.user.display_avatar.url)
    return embed

# --- KOMUTLAR ---

# 1. /info
@bot.tree.command(name="info", description="Apexium oyunu, geliştirici ve sunucu hakkında havalı bilgiler.")
async def info_command(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    guild = interaction.guild
    owner = guild.owner

    if lang == 'en':
        embed = discord.Embed(
            title="🏃 APEXIUM: PARKOUR CHRONICLES",
            description="Welcome to the official showcase of **Apexium: Parkour Chronicles**!\n"
                        "A high-octane, low-poly parkour game designed for extreme agility and thrill-seekers.\n"
                        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="🎮 About The Game",
            value="• **Genre:** 3D Low-Poly Action Parkour\n"
                  "• **Engine:** Unreal Engine 5\n"
                  "• **Features:** Fluid movement, dynamic obstacles, time-trials & level checkpoints.",
            inline=False
        )
        embed.add_field(
            name="👑 Game Creator & Server Owner",
            value=f"• **Lead Developer:** {owner.mention if owner else 'Berat Eşkiler (@pufDev0)'}\n"
                  f"• **Discord Profile:** `{owner.name if owner else 'pufDev0'}`\n"
                  "• **Role:** Game Designer, 3D Modeler & Developer",
            inline=False
        )
        embed.add_field(
            name="📊 Server Info",
            value=f"• **Community Name:** {guild.name}\n"
                  f"• **Total Members:** {guild.member_count}\n"
                  f"• **Creation Date:** {guild.created_at.strftime('%Y-%m-%d')}",
            inline=False
        )
    else:
        embed = discord.Embed(
            title="🏃 APEXIUM: PARKOUR CHRONICLES",
            description="**Apexium: Parkour Chronicles** resmi bilgi paneline hoş geldiniz!\n"
                        "Yüksek tempolu, low-poly grafikli ve ekstrem refleks gerektiren bağımsız parkur oyunu projesi.\n"
                        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="🎮 Oyun Hakkında",
            value="• **Tür:** 3D Low-Poly Aksiyon Parkur\n"
                  "• **Oyun Motoru:** Unreal Engine 5\n"
                  "• **Özellikler:** Akıcı tırmanış mekanikleri, dinamik tuzaklar, süreye karşı yarış ve check-point sistemi.",
            inline=False
        )
        embed.add_field(
            name="👑 Yapımcı & Sunucu Kurucusu",
            value=f"• **Geliştirici:** {owner.mention if owner else 'Berat Eşkiler (@pufDev0)'}\n"
                  f"• **Discord:** `{owner.name if owner else 'pufDev0'}`\n"
                  "• **Unvan:** Oyun Tasarımcısı, 3D Modelleyici & Yazılımcı",
            inline=False
        )
        embed.add_field(
            name="📊 Sunucu Bilgisi",
            value=f"• **Sunucu:** {guild.name}\n"
                  f"• **Toplam Üye:** {guild.member_count}\n"
                  f"• **Kuruluş Tarihi:** {guild.created_at.strftime('%d.%m.%Y')}",
            inline=False
        )

    if owner and owner.display_avatar:
        embed.set_thumbnail(url=owner.display_avatar.url)
    elif guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text="Apexium Studio • Developed by Berat Eşkiler", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 2. /sunucukur (SADECE OWNER)
@bot.tree.command(name="sunucukur", description="Var olan kanalları siler ve ultra havalı sunucu yapısını kurar.")
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

    # İNGİLİZCE GAMER LEVEL ROLLERİ
    l1_gamer = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer") or await guild.create_role(name="🎮 Level 1 Gamer", permissions=discord.Permissions.general(), color=discord.Color.green(), hoist=True)
    await guild.create_role(name="⚡ Level 2 Gamer", permissions=discord.Permissions.general(), color=discord.Color.blue(), hoist=True)
    await guild.create_role(name="🔥 Level 3 Gamer", permissions=discord.Permissions.general(), color=discord.Color.purple(), hoist=True)
    await guild.create_role(name="👑 Master Gamer", permissions=discord.Permissions.general(), color=discord.Color.gold(), hoist=True)

    # ÜLKE ROLLERİ
    for country in ["🇹🇷 Turkey", "🇬🇧 United Kingdom", "🇺🇸 United States", "🇩🇪 Germany", "🇫🇷 France", "🇪🇸 Spain"]:
        if not discord.utils.get(guild.roles, name=country):
            await guild.create_role(name=country, color=discord.Color.dark_teal())

    try:
        await interaction.user.add_roles(owner_role)
    except Exception:
        pass

    public_read_only = {
        guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True),
        l1_gamer: discord.PermissionOverwrite(send_messages=False, read_messages=True)
    }

    gamer_access = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        l1_gamer: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # MODERATÖRLER LOGS KANALINI GÖREMEZ (Sadece Owner & Admin)
    logs_only_admin = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        mod_role: discord.PermissionOverwrite(read_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    staff_only_text = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    owner_admin_voice = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    staff_voice = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        mod_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    info_cat = await guild.create_category("INFORMATION")
    welcome_ch = await info_cat.create_text_channel("welcome", overwrites=public_read_only)
    rules_ch = await info_cat.create_text_channel("rules", overwrites=public_read_only)
    download_ch = await info_cat.create_text_channel("download-game", overwrites=public_read_only)
    await info_cat.create_text_channel("announcements", overwrites=public_read_only)
    await info_cat.create_text_channel("updates", overwrites=public_read_only)
    await info_cat.create_text_channel("logs", overwrites=logs_only_admin)
    await info_cat.create_text_channel("staff-commands", overwrites=staff_only_text)

    # Welcome Ülke/Dil Seçim Paneli
    welcome_embed = discord.Embed(
        title="🌐 SELECT YOUR COUNTRY / ÜLKENİZİ SEÇİN",
        description="Sunucu kanallarına erişmek için lütfen aşağıdaki menüden ülkenizi seçin.\n\nPlease select your country from the menu below to unlock channels.",
        color=discord.Color.gold()
    )
    await welcome_ch.send(embed=welcome_embed, view=CountrySelectView())

    # Rules
    await rules_ch.send(embed=create_rules_embed(guild), view=RuleAcceptView())

    # Download Game
    download_embed = discord.Embed(
        title="🎮 DOWNLOAD APEXIUM: PARKOUR CHRONICLES",
        description="**Apexium Trial** sürümünü aşağıdaki bağlantıdan hemen indirebilir ve maceraya atılabilirsiniz!\n"
                    "Click below to download and play the official demo on itch.io.\n\n"
                    f"🔗 **Direct Link / Doğrudan Bağlantı:**\n{GAME_ITCH_LINK}\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=discord.Color.green()
    )
    download_embed.set_image(url=DOWNLOAD_GAME_BANNER)
    download_embed.set_footer(text="Apexium Studio • Official itch.io Release", icon_url=bot.user.display_avatar.url)
    await download_ch.send(embed=download_embed, view=DownloadGameView())

    comm_cat = await guild.create_category("COMMUNITY")
    await comm_cat.create_text_channel("general-chat", overwrites=gamer_access)
    await comm_cat.create_text_channel("media-share", overwrites=gamer_access)
    await comm_cat.create_text_channel("bot-commands", overwrites=gamer_access)

    supp_cat = await guild.create_category("SUPPORT & FEEDBACK")
    await supp_cat.create_text_channel("bug-reports", overwrites=gamer_access)
    await supp_cat.create_text_channel("suggestions", overwrites=gamer_access)
    ticket_channel = await supp_cat.create_text_channel("create-ticket", overwrites=gamer_access)

    # Create Ticket Kanalı Banner Güncellemesi
    ticket_embed = discord.Embed(
        title="🎫 APEXIUM OFFICIAL SUPPORT SYSTEM",
        description="Sorunlarınız ve yetkili iletişimi için bilet oluşturun / Click below to open a support ticket.",
        color=discord.Color.blue()
    )
    ticket_embed.set_image(url=DOWNLOAD_GAME_BANNER)
    await ticket_channel.send(embed=ticket_embed, view=TicketView())

    voice_cat = await guild.create_category("VOICE CHANNELS")
    await voice_cat.create_voice_channel("Public Lounge", overwrites=gamer_access)
    await voice_cat.create_voice_channel("Squad 1", overwrites=gamer_access)
    await voice_cat.create_voice_channel("🔒 Staff Voice", overwrites=staff_voice)
    await voice_cat.create_voice_channel("🔒 Owner & Admin Voice", overwrites=owner_admin_voice)

    embed_done = discord.Embed(
        title="🔥 Apexium Core System Online",
        description="✅ Ülke rolleri, Gamer seviye sistemi, gizli loglar ve sinematik bilet kanalı başarıyla kuruldu!",
        color=discord.Color.gold()
    )
    try:
        await interaction.followup.send(embed=embed_done, ephemeral=True)
    except Exception:
        pass

# 3. /duyuru
@bot.tree.command(name="duyuru", description="Duyurular kanalına görsel ve açıklamalı sinematik duyuru gönderir.")
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

    guild = interaction.guild
    embed = discord.Embed(
        title=f"📢 {title.upper()}",
        description=f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n{message}\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=discord.Color.gold()
    )
    
    if guild.icon:
        embed.set_author(name=f"{guild.name} • OFFICIAL ANNOUNCEMENT", icon_url=guild.icon.url)
        embed.set_thumbnail(url=guild.icon.url)
    else:
        embed.set_author(name=f"{guild.name} • OFFICIAL ANNOUNCEMENT")

    final_image = image_url if image_url else DEFAULT_ANNOUNCEMENT_BANNER
    embed.set_image(url=final_image)

    embed.set_footer(text=f"Announced by {interaction.user.display_name} • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = datetime.now(timezone.utc)

    await ann_channel.send(content="@everyone", embed=embed)
    
    confirm_embed = discord.Embed(title="✨ Success / Başarılı", description="📢 Duyuru `#announcements` kanalında sinematik banner ile yayınlandı!", color=discord.Color.green())
    await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
    await log_event(interaction.guild, "📢 Duyuru Paylaşıldı", f"**Başlık:** {title}\n**Yetkili:** {interaction.user.mention}", discord.Color.gold())

# 4. /kurallar
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

    await rules_ch.send(embed=create_rules_embed(interaction.guild), view=RuleAcceptView())
    embed_ok = discord.Embed(title="✅ Kurallar Gönderildi", description="Kural paneli `#rules` kanalında başarıyla güncellendi.", color=discord.Color.green())
    await interaction.response.send_message(embed=embed_ok, ephemeral=True)

# 5. /ban
@bot.tree.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Bu komut için **Admin** veya **Owner** olmalısınız!", ephemeral=True)
        return
    await member.ban(reason=reason)
    embed = discord.Embed(title="🚫 User Banned / Kullanıcı Yasaklandı", description=f"**Target:** {member.mention}\n**Reason:** {reason}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_event(interaction.guild, "🔨 Ban Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.red())

# 6. /kick
@bot.tree.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Bu komut için **Admin** veya **Owner** olmalısınız!", ephemeral=True)
        return
    await member.kick(reason=reason)
    embed = discord.Embed(title="👞 User Kicked / Kullanıcı Atıldı", description=f"**Target:** {member.mention}\n**Reason:** {reason}", color=discord.Color.orange())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_event(interaction.guild, "👞 Kick Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}\n**Reason:** {reason}", discord.Color.orange())

# 7. /mute
@bot.tree.command(name="mute", description="Bir kullanıcıyı belirli bir süre susturur (dakika).")
@app_commands.default_permissions(moderate_members=True)
async def mute_user(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Sebep belirtilmedi"):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    embed = discord.Embed(title="🤐 User Muted / Kullanıcı Susturuldu", description=f"**Target:** {member.mention}\n**Duration:** {minutes} Min\n**Reason:** {reason}", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_event(interaction.guild, "🤐 Mute Event", f"**User:** {member.mention}\n**Duration:** {minutes} Min\n**Staff:** {interaction.user.mention}", discord.Color.gold())

# 8. /unmute
@bot.tree.command(name="unmute", description="Bir kullanıcının susturmasını kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def unmute_user(interaction: discord.Interaction, member: discord.Member):
    lang = get_lang(interaction.user.id)
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.timeout(None)
    embed = discord.Embed(title="🔊 User Unmuted / Susturma Kaldırıldı", description=f"**Target:** {member.mention}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_event(interaction.guild, "🔊 Unmute Event", f"**User:** {member.mention}\n**Staff:** {interaction.user.mention}", discord.Color.green())

# 9. /lock
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
    embed = discord.Embed(title="🔒 Channel Locked / Kanal Kilitlendi", description=f"**Channel:** {channel.mention}", color=discord.Color.dark_red())
    await interaction.response.send_message(embed=embed)
    await log_event(interaction.guild, "🔒 Lock Event", f"**Channel:** {channel.mention}\n**Staff:** {interaction.user.mention}", discord.Color.dark_red())

# 10. /unlock
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
    embed = discord.Embed(title="🔓 Channel Unlocked / Kanal Açıldı", description=f"**Channel:** {channel.mention}", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)
    await log_event(interaction.guild, "🔓 Unlock Event", f"**Channel:** {channel.mention}\n**Staff:** {interaction.user.mention}", discord.Color.green())

# 11. /sil
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
    embed = discord.Embed(title="🗑️ Messages Purged / Mesajlar Silindi", description=f"**Deleted:** {len(deleted)} messages", color=discord.Color.purple())
    await interaction.followup.send(embed=embed, ephemeral=True)
    await log_event(interaction.guild, "🗑️ Purge Event", f"**Channel:** {interaction.channel.mention}\n**Count:** {len(deleted)}\n**Staff:** {interaction.user.mention}", discord.Color.purple())

# 12. /help
@bot.tree.command(name="help", description="Sunucu kullanım rehberi ve komut listesi.")
async def help_command(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    guild = interaction.guild
    if lang == 'en':
        embed = discord.Embed(
            title=f"🎮 {guild.name.upper()} — GAMER GUIDE",
            description="Welcome to our official gaming hub! Follow this guide to get started:\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=discord.Color.green()
        )
        embed.add_field(name="🌐 1. Language & Country", value="Select your country in `#welcome` or type `/language`.", inline=False)
        embed.add_field(name="📜 2. Verification", value="Head to `#rules` and click **Accept Rules** to unlock channels.", inline=False)
        embed.add_field(name="🏃 3. Game Info", value="Type `/info` to check game details, creator profile & server stats.", inline=False)
        embed.add_field(name="📩 4. Support Desk", value="Need assistance? Open a ticket in `#create-ticket`.", inline=False)
        embed.add_field(name="🏓 5. Commands", value="`/ping` • Check latency\n`/info` • Game & Owner Details\n`/help` • Display this guide", inline=False)
    else:
        embed = discord.Embed(
            title=f"🎮 {guild.name.upper()} — OYUNCU REHBERİ",
            description="Sunucumuza hoş geldiniz! Başlangıç rehberiniz aşağıdadır:\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=discord.Color.green()
        )
        embed.add_field(name="🌐 1. Dil & Ülke Seçimi", value="`#welcome` kanalından veya `/language` yazarak ülkenizi seçin.", inline=False)
        embed.add_field(name="📜 2. Sunucu Kaydı", value="`#rules` kanalına gidin ve **Accept Rules** butonuna basarak kanalları açın.", inline=False)
        embed.add_field(name="🏃 3. Oyun & Sunucu Bilgisi", value="`/info` yazarak oyun detaylarını, yapımcı profilini ve istatistikleri görün.", inline=False)
        embed.add_field(name="📩 4. Destek Masası", value="Yetkililere ulaşmak için `#create-ticket` kanalından bilet açabilirsiniz.", inline=False)
        embed.add_field(name="🏓 5. Komutlar", value="`/ping` • Gecikmeyi ölçer\n`/info` • Oyun & Kurucu Bilgisi\n`/help` • Bu rehberi açar", inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Apexium Bot Community System", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 13. Genel Komutlar
@bot.tree.command(name="language", description="Select your language / Dilinizi seçin")
async def language(interaction: discord.Interaction):
    embed = discord.Embed(title="🌐 Language Selection / Dil Seçimi", description="Lütfen ülkenizi/dilinizi seçin / Select your country below:", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, view=CountrySelectView(), ephemeral=True)

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir.")
async def ping(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    ms = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Gecikme Süresi: **{ms}ms**" if lang == 'tr' else f"Latency: **{ms}ms**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN") or "MTU0NDY5OTM3OTA5OTc3MDg5Mg.GLxPNK.zX5pectcQSndVdHhUNVGitM9V5GqD_kWGQ5L_0"

keep_alive()
bot.run(TOKEN)
