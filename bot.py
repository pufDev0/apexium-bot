import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from datetime import timedelta, datetime, timezone
from aiohttp import web

# --- RENDER PORT HEALTH CHECK (ASYNCHRONOUS WEB SERVER) ---
async def handle_ping(request):
    return web.Response(text="Apexium Bot 7/24 Online & Healthy!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/health', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Web Sunucusu {port} portunda aktifleştirildi!")

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

        msg = f"✅ **{role_name}** rolü tanımlandı!" if val == 'TR' else f"✅ Assigned **{role_name}** role!"
        await interaction.response.send_message(msg, ephemeral=True)
        await log_event(guild, "🌐 Ülke/Dil Seçildi", f"**Üye:** {member.mention}\n**Ülke:** {role_name}", discord.Color.blue())

class RuleAcceptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Accept Rules / Kuralları Kabul Et", style=discord.ButtonStyle.success, custom_id="accept_rules_btn")
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        gamer_l1 = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer")
        
        if gamer_l1:
            if gamer_l1 in member.roles:
                await interaction.response.send_message("✨ Zaten kuralları kabul ettiniz! / You have already accepted the rules!", ephemeral=True)
            else:
                await member.add_roles(gamer_l1)
                embed = discord.Embed(
                    title="🎉 Access Granted / Erişim Onaylandı!",
                    description="Kuralları kabul ettiğin için teşekkürler! **Level 1 Gamer** rolü tanımlandı.",
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

            if days >= 365 and master_role and master_role not in member.roles:
                await member.add_roles(master_role)
                if l3_role in member.roles: await member.remove_roles(l3_role)
                await log_event(guild, "👑 Level Up! (Master Gamer)", f"**Kullanıcı:** {member.mention}\n**Sunucuda Süre:** {days} Gün", discord.Color.gold())
            elif days >= 30 and days < 365 and l3_role and l3_role not in member.roles:
                await member.add_roles(l3_role)
                if l2_role in member.roles: await member.remove_roles(l2_role)
                await log_event(guild, "🔥 Level Up! (Level 3)", f"**Kullanıcı:** {member.mention}\n**Sunucuda Süre:** {days} Gün", discord.Color.purple())
            elif days >= 7 and days < 30 and l2_role and l2_role not in member.roles:
                await member.add_roles(l2_role)
                if l1_role in member.roles: await member.remove_roles(l1_role)
                await log_event(guild, "⚡ Level Up! (Level 2)", f"**Kullanıcı:** {member.mention}\n**Sunucuda Süre:** {days} Gün", discord.Color.blue())

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} olarak giriş yaptı!')
    bot.add_view(RuleAcceptView())
    bot.add_view(TicketView())
    bot.add_view(DownloadGameView())
    bot.add_view(CountrySelectView())
    if not check_member_levels.is_running():
        check_member_levels.start()
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print("✅ Slash komutları ve Otomatik Level sistemi yüklendi!")
    except Exception as e:
        print(f"Hata: {e}")

# OTOMATİK ROL KORUMA SİSTEMİ (Manuel Verilen Rolleri Anında Siler)
@bot.event
async def on_member_update(before, after):
    guild = after.guild
    if before.roles != after.roles:
        added = [r for r in after.roles if r not in before.roles]
        
        if not added:
            return

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            executor = entry.user
            # Botun kendi verdiği ya da Sunucu Sahibinin yaptığı işlemleri muaf tut
            if executor and not executor.bot and executor.id != guild.owner_id:
                admin_role = discord.utils.get(guild.roles, name="🛠️ Admin")
                is_executor_admin = admin_role in executor.roles if admin_role else False
                
                # Admin veya Owner değilse eklenen rolleri anında sil
                if not is_executor_admin:
                    for role in added:
                        await after.remove_roles(role)
                    await log_event(guild, "🚨 YETKİSİZ ROL EKLEME ENGELLENDİ", f"**İşlemi Yapan:** {executor.mention}\n**Hedef Üye:** {after.mention}\n**Silinen Rol:** {', '.join([r.name for r in added])}", discord.Color.red())
                    return

        desc = f"**Üye:** {after.mention}\n"
        desc += f"**Eklendi:** {', '.join([r.mention for r in added])}"
        await log_event(guild, "🛡️ Rol Değişikliği", desc, discord.Color.gold())

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
    
    await log_event(guild, "📥 Üye Katıldı", f"**Üye:** {member.mention} ({member.tag})", discord.Color.blue())

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
        embed.add_field(name="🎮 About The Game", value="• **Genre:** 3D Low-Poly Action Parkour\n• **Engine:** Unreal Engine 5\n• **Features:** Fluid movement, dynamic obstacles, time-trials & level checkpoints.", inline=False)
        embed.add_field(name="👑 Game Creator & Server Owner", value=f"• **Lead Developer:** {owner.mention if owner else 'Berat Eşkiler (@pufDev0)'}\n• **Discord Profile:** `{owner.name if owner else 'pufDev0'}`\n• **Role:** Game Designer, 3D Modeler & Developer", inline=False)
        embed.add_field(name="📊 Server Info", value=f"• **Community Name:** {guild.name}\n• **Total Members:** {guild.member_count}\n• **Creation Date:** {guild.created_at.strftime('%Y-%m-%d')}", inline=False)
    else:
        embed = discord.Embed(
            title="🏃 APEXIUM: PARKOUR CHRONICLES",
            description="**Apexium: Parkour Chronicles** resmi bilgi paneline hoş geldiniz!\n"
                        "Yüksek tempolu, low-poly grafikli ve ekstrem refleks gerektiren bağımsız parkur oyunu projesi.\n"
                        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
            color=discord.Color.gold()
        )
        embed.add_field(name="🎮 Oyun Hakkında", value="• **Tür:** 3D Low-Poly Aksiyon Parkur\n• **Oyun Motoru:** Unreal Engine 5\n• **Özellikler:** Akıcı tırmanış mekanikleri, dinamik tuzaklar, süreye karşı yarış ve check-point sistemi.", inline=False)
        embed.add_field(name="👑 Yapımcı & Sunucu Kurucusu", value=f"• **Geliştirici:** {owner.mention if owner else 'Berat Eşkiler (@pufDev0)'}\n• **Discord:** `{owner.name if owner else 'pufDev0'}`\n• **Unvan:** Oyun Tasarımcısı, 3D Modelleyici & Yazılımcı", inline=False)
        embed.add_field(name="📊 Sunucu Bilgisi", value=f"• **Sunucu:** {guild.name}\n• **Toplam Üye:** {guild.member_count}\n• **Kuruluş Tarihi:** {guild.created_at.strftime('%d.%m.%Y')}", inline=False)

    if owner and owner.display_avatar:
        embed.set_thumbnail(url=owner.display_avatar.url)
    elif guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.set_footer(text="Apexium Studio • Developed by Berat Eşkiler", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="sunucukur", description="Var olan tüm kanalları ve rolleri siler, sıfırdan güvenli yapıyı kurar.")
@app_commands.default_permissions(administrator=True)
async def setup_server(interaction: discord.Interaction):
    lang = get_lang(interaction.user.id)
    if not is_owner(interaction):
        msg = "❌ Bu komutu sadece **Sunucu Sahibi (Owner)** kullanabilir!" if lang == 'tr' else "❌ Only the **Server Owner** can use this command!"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # 1. TÜM KANALLARI SİL
    for channel in guild.channels:
        try:
            await channel.delete()
        except Exception:
            pass

    # 2. ESKİ ROL KILIFLARINI VE İZİNLERİ TEMİZLE
    for role in guild.roles:
        if role.name != "@everyone" and role < guild.me.top_role:
            try:
                await role.delete()
            except Exception:
                pass

    # @everyone İZİNLERİNİ SIFIRLA VE ROL YÖNETİMİNİ KAPAT
    try:
        everyone_perms = discord.Permissions(
            read_messages=True, send_messages=True, connect=True, speak=True,
            manage_roles=False, manage_channels=False, manage_guild=False, administrator=False
        )
        await guild.default_role.edit(permissions=everyone_perms)
    except Exception:
        pass

    # 3. KİLİTLİ ROLLERİ SIFIRDAN OLUŞTUR
    owner_role = discord.utils.get(guild.roles, name="👑 Owner") or await guild.create_role(name="👑 Owner", permissions=discord.Permissions.all(), color=discord.Color.gold(), hoist=True)
    dev_role = discord.utils.get(guild.roles, name="👑 Developer") or await guild.create_role(name="👑 Developer", permissions=discord.Permissions.all(), color=discord.Color.teal(), hoist=True)
    
    admin_perms = discord.Permissions(manage_channels=True, manage_roles=True, kick_members=True, ban_members=True, manage_messages=True, read_messages=True, send_messages=True, connect=True, speak=True)
    admin_role = discord.utils.get(guild.roles, name="🛠️ Admin") or await guild.create_role(name="🛠️ Admin", permissions=admin_perms, color=discord.Color.red(), hoist=True)

    mod_perms = discord.Permissions(manage_messages=True, mute_members=True, deafen_members=True, read_messages=True, send_messages=True, connect=True, speak=True, manage_roles=False)
    mod_role = discord.utils.get(guild.roles, name="🛡️ Moderator") or await guild.create_role(name="🛡️ Moderator", permissions=mod_perms, color=discord.Color.blue(), hoist=True)

    gamer_perms = discord.Permissions(read_messages=True, send_messages=True, connect=True, speak=True, manage_roles=False, manage_guild=False)
    
    await guild.create_role(name="👑 Master Gamer", permissions=gamer_perms, color=discord.Color.gold(), hoist=True)
    await guild.create_role(name="🔥 Level 3 Gamer", permissions=gamer_perms, color=discord.Color.purple(), hoist=True)
    await guild.create_role(name="⚡ Level 2 Gamer", permissions=gamer_perms, color=discord.Color.blue(), hoist=True)
    l1_gamer = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer") or await guild.create_role(name="🎮 Level 1 Gamer", permissions=gamer_perms, color=discord.Color.green(), hoist=True)

    for country in ["🇹🇷 Turkey", "🇬🇧 United Kingdom", "🇺🇸 United States", "🇩🇪 Germany", "🇫🇷 France", "🇪🇸 Spain"]:
        if not discord.utils.get(guild.roles, name=country):
            await guild.create_role(name=country, permissions=gamer_perms, color=discord.Color.dark_teal())

    try:
        await interaction.user.add_roles(owner_role, dev_role)
    except Exception:
        pass

    # 4. KANAL İZİNLERİ VE KATEGORİLER
    public_read_only = {guild.default_role: discord.PermissionOverwrite(send_messages=False, read_messages=True), l1_gamer: discord.PermissionOverwrite(send_messages=False, read_messages=True)}
    all_can_write = {guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
    create_ticket_perms = {guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False), owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
    logs_only_admin = {guild.default_role: discord.PermissionOverwrite(read_messages=False), mod_role: discord.PermissionOverwrite(read_messages=False), owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
    staff_only_text = {guild.default_role: discord.PermissionOverwrite(read_messages=False), owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True), mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
    owner_admin_voice = {guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True), owner_role: discord.PermissionOverwrite(connect=True, view_channel=True), admin_role: discord.PermissionOverwrite(connect=True, view_channel=True)}
    staff_voice = {guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True), owner_role: discord.PermissionOverwrite(connect=True, view_channel=True), admin_role: discord.PermissionOverwrite(connect=True, view_channel=True), mod_role: discord.PermissionOverwrite(connect=True, view_channel=True)}

    info_cat = await guild.create_category("INFORMATION")
    welcome_ch = await info_cat.create_text_channel("welcome", overwrites=public_read_only)
    rules_ch = await info_cat.create_text_channel("rules", overwrites=public_read_only)
    download_ch = await info_cat.create_text_channel("download-game", overwrites=public_read_only)
    await info_cat.create_text_channel("announcements", overwrites=public_read_only)
    await info_cat.create_text_channel("updates", overwrites=public_read_only)
    await info_cat.create_text_channel("logs", overwrites=logs_only_admin)
    await info_cat.create_text_channel("staff-commands", overwrites=staff_only_text)

    welcome_embed = discord.Embed(title="🌐 SELECT YOUR COUNTRY / ÜLKENİZİ SEÇİN", description="Sunucu kanallarına erişmek için lütfen aşağıdaki menüden ülkenizi seçin.\n\nPlease select your country from the menu below to unlock channels.", color=discord.Color.gold())
    await welcome_ch.send(embed=welcome_embed, view=CountrySelectView())

    await rules_ch.send(embed=create_rules_embed(guild), view=RuleAcceptView())

    download_embed = discord.Embed(title="🎮 DOWNLOAD APEXIUM: PARKOUR CHRONICLES", description=f"**Apexium Trial** sürümünü aşağıdaki bağlantıdan hemen indirebilirsiniz!\n\n🔗 **Direct Link:**\n{GAME_ITCH_LINK}", color=discord.Color.green())
    download_embed.set_image(url=DOWNLOAD_GAME_BANNER)
    download_embed.set_footer(text="Apexium Studio • Official itch.io Release", icon_url=bot.user.display_avatar.url)
    await download_ch.send(embed=download_embed, view=DownloadGameView())

    comm_cat = await guild.create_category("COMMUNITY")
    await comm_cat.create_text_channel("general-chat", overwrites=all_can_write)
    await comm_cat.create_text_channel("media-share", overwrites=all_can_write)
    await comm_cat.create_text_channel("bot-commands", overwrites=all_can_write)

    supp_cat = await guild.create_category("SUPPORT & FEEDBACK")
    await supp_cat.create_text_channel("bug-reports", overwrites=all_can_write)
    await supp_cat.create_text_channel("suggestions", overwrites=all_can_write)
    ticket_channel = await supp_cat.create_text_channel("create-ticket", overwrites=create_ticket_perms)

    ticket_embed = discord.Embed(title="🎫 APEXIUM OFFICIAL SUPPORT SYSTEM", description="Sorunlarınız ve yetkili iletişimi için bilet oluşturun / Click below to open a support ticket.", color=discord.Color.blue())
    ticket_embed.set_image(url=DOWNLOAD_GAME_BANNER)
    await ticket_channel.send(embed=ticket_embed, view=TicketView())

    voice_cat = await guild.create_category("VOICE CHANNELS")
    await voice_cat.create_voice_channel("Public Lounge", overwrites=all_can_write)
    await voice_cat.create_voice_channel("Squad 1", overwrites=all_can_write)
    await voice_cat.create_voice_channel("🔒 Staff Voice", overwrites=staff_voice)
    await voice_cat.create_voice_channel("🔒 Owner & Admin Voice", overwrites=owner_admin_voice)

    embed_done = discord.Embed(title="🔥 Apexium Core System Online", description="✅ Rol hiyerarşisi, eski izinlerin temizliği ve güvenlik kilitleri başarıyla kuruldu!", color=discord.Color.gold())
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
    embed = discord.Embed(title=f"📢 {title.upper()}", description=f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n{message}\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", color=discord.Color.gold())
    if guild.icon:
        embed.set_author(name=f"{guild.name} • OFFICIAL ANNOUNCEMENT", icon_url=guild.icon.url)
        embed.set_thumbnail(url=guild.icon.url)
    else:
        embed.set_author(name=f"{guild.name} • OFFICIAL ANNOUNCEMENT")

    final_image = image_url if image_url else DEFAULT_ANNOUNCEMENT_BANNER
    embed.set_image(url=final_image)
    embed.set_footer(text=f"Announced by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = datetime.now(timezone.utc)

    await ann_channel.send(content="@everyone", embed=embed)
    await interaction.response.send_message("📢 Duyuru paylaşıldı!", ephemeral=True)

# 4. /kurallar
@bot.tree.command(name="kurallar", description="#rules kanalına kural mesajını ve onay butonunu yeniden yollar.")
@app_commands.default_permissions(administrator=True)
async def post_rules(interaction: discord.Interaction):
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    rules_ch = discord.utils.get(interaction.guild.channels, name="rules")
    if rules_ch:
        await rules_ch.send(embed=create_rules_embed(interaction.guild), view=RuleAcceptView())
        await interaction.response.send_message("✅ Kurallar gönderildi.", ephemeral=True)

# 5. /ban
@bot.tree.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🚫 {member.mention} yasaklandı.", ephemeral=True)

# 6. /kick
@bot.tree.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👞 {member.mention} atıldı.", ephemeral=True)

# 7. /mute
@bot.tree.command(name="mute", description="Bir kullanıcıyı belirli bir süre susturur (dakika).")
@app_commands.default_permissions(moderate_members=True)
async def mute_user(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Sebep belirtilmedi"):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"🤐 {member.mention} {minutes} dakika susturuldu.", ephemeral=True)

# 8. /unmute
@bot.tree.command(name="unmute", description="Bir kullanıcının susturmasını kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def unmute_user(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 {member.mention} susturması kaldırıldı.", ephemeral=True)

# 9. /lock
@bot.tree.command(name="lock", description="Komutun yazıldığı kanala mesaj gönderimini kilitler.")
@app_commands.default_permissions(manage_channels=True)
async def lock_channel(interaction: discord.Interaction):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Kanal kilitlendi.")

# 10. /unlock
@bot.tree.command(name="unlock", description="Kilitli kanalı tekrar mesaj gönderimine açar.")
@app_commands.default_permissions(manage_channels=True)
async def unlock_channel(interaction: discord.Interaction):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Kanal açıldı.")

# 11. /sil
@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı kanaldan siler.")
@app_commands.default_permissions(manage_messages=True)
async def purge_messages(interaction: discord.Interaction, amount: int):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🗑️ {len(deleted)} mesaj silindi.", ephemeral=True)

# 12. /help
@bot.tree.command(name="help", description="Sunucu kullanım rehberi ve komut listesi.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🎮 GAMER GUIDE", description="`/ping` • Gecikmeyi ölçer\n`/info` • Oyun & Kurucu Bilgisi\n`/help` • Bu rehberi açar", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

# 13. Genel Komutlar
@bot.tree.command(name="language", description="Select your language / Dilinizi seçin")
async def language(interaction: discord.Interaction):
    await interaction.response.send_message("🌐 Select country:", view=CountrySelectView(), ephemeral=True)

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! ({round(bot.latency * 1000)}ms)", ephemeral=True)

# --- ANA ÇALIŞTIRMA DÖNGÜSÜ ---
async def main():
    await start_web_server()
    token = os.getenv("DISCORD_TOKEN") or "MTU0NDY5OTM3OTA5OTc3MDg5Mg.GLxPNK.zX5pectcQSndVdHhUNVGitM9V5GqD_kWGQ5L_0"
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
