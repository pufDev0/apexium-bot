import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from datetime import timedelta, datetime, timezone
from aiohttp import web

# --- RENDER PORT HEALTH CHECK ---
async def handle_ping(request):
    return web.Response(text="⚡ APEXIUM CORE ONLINE & ACTIVE ⚡")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/health', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 [SYSTEM] Web Sunucusu {port} portunda aktifleştirildi!")

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

async def log_event(guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.gold()):
    log_channel = discord.utils.get(guild.channels, name="logs")
    if log_channel:
        embed = discord.Embed(
            title=f"🛡️ APEXIUM SECURITY LOG | {title.upper()}",
            description=description,
            color=color
        )
        embed.set_footer(text="Apexium Core Autonomous Security Sentinel", icon_url=bot.user.display_avatar.url)
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

# --- ARAYÜZ (VIEWS) ---
class DownloadGameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="⚡ PLAY APEXIUM TRIAL (itch.io)", url=GAME_ITCH_LINK, style=discord.ButtonStyle.link))

class CountrySelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="🌐 Step 1: Choose Your Gateway / Ülkenizi Seçin...",
        custom_id="country_select_menu",
        options=[
            discord.SelectOption(label="Turkey 🇹🇷", value="TR", emoji="🇹🇷", description="Türkçe / Turkish Language Area"),
            discord.SelectOption(label="United Kingdom 🇬🇧", value="UK", emoji="🇬🇧", description="English / UK Region"),
            discord.SelectOption(label="United States 🇺🇸", value="US", emoji="🇺🇸", description="English / US Region"),
            discord.SelectOption(label="Germany 🇩🇪", value="DE", emoji="🇩🇪", description="German / Europe Central"),
            discord.SelectOption(label="France 🇫🇷", value="FR", emoji="🇫🇷", description="French / Europe West"),
            discord.SelectOption(label="Spain 🇪🇸", value="ES", emoji="🇪🇸", description="Spanish / Europe South")
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
        role = discord.utils.get(guild.roles, name=role_name) or await guild.create_role(name=role_name, color=discord.Color.dark_teal())
        
        user_languages[member.id] = 'tr' if val == 'TR' else 'en'
        await member.add_roles(role)

        rules_ch = discord.utils.get(guild.channels, name="rules")
        rules_mention = rules_ch.mention if rules_ch else "#rules"

        msg = (
            f"✅ **{role_name}** bölgesi seçildi!\n"
            f"👉 Şimdi {rules_mention} kanalına giderek sunucu kurallarını onaylayın ve tüm sunucuya erişim kazanın."
            if val == 'TR' else
            f"✅ Assigned **{role_name}** sector!\n"
            f"👉 Now proceed to {rules_mention} to accept rules and unlock full server access."
        )
        await interaction.response.send_message(msg, ephemeral=True)
        await log_event(guild, "🌐 Ülke/Dil Seçildi", f"**Üye:** {member.mention}\n**Bölge:** {role_name}", discord.Color.blue())

class RuleAcceptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚡ VERIFY ACCESS / KURALLARI ONAYLA", style=discord.ButtonStyle.success, custom_id="accept_rules_btn")
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        gamer_l1 = discord.utils.get(guild.roles, name="🎮 Level 1 Gamer")
        
        has_country = any(r.name in ["🇹🇷 Turkey", "🇬🇧 United Kingdom", "🇺🇸 United States", "🇩🇪 Germany", "🇫🇷 France", "🇪🇸 Spain"] for r in member.roles)
        if not has_country:
            welcome_ch = discord.utils.get(guild.channels, name="welcome")
            welc_mention = welcome_ch.mention if welcome_ch else "#welcome"
            await interaction.response.send_message(f"⚠️ Lütfen önce {welc_mention} kanalından ülkenizi/dilinizi seçin! / Please select your country first!", ephemeral=True)
            return

        if gamer_l1:
            if gamer_l1 in member.roles:
                await interaction.response.send_message("🛡️ Kimliğiniz zaten doğrulanmış durumda! / Already verified!", ephemeral=True)
            else:
                await member.add_roles(gamer_l1)
                embed = discord.Embed(
                    title="🔓 ACCESS GRANTED | APEXIUM CORE",
                    description="Güvenlik protokollerini onayladığınız için teşekkürler!\n**Level 1 Gamer** yetkiniz tanımlandı ve tüm topluluk kanalları erişime açıldı! 🎉",
                    color=discord.Color.brand_green()
                )
                embed.set_footer(text="Apexium Autonomous Defense Network", icon_url=bot.user.display_avatar.url)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                await log_event(guild, "✅ Güvenlik Onayı (Rol Alındı)", f"**Üye:** {member.mention}", discord.Color.green())

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 OPEN TICKET / DESTEK TALEBİ AÇ", style=discord.ButtonStyle.primary, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        lang = get_lang(user.id)

        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            msg = "Zaten aktif bir iletişim kanalınız bulunuyor: " if lang == 'tr' else "Active ticket session already exists: "
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
        res_msg = "Özel destek kanalınız bağlandı: " if lang == 'tr' else "Secure ticket terminal initialized: "
        await interaction.response.send_message(f"{res_msg}{ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title="🎫 APEXIUM SUPPORT TERMINAL",
            description=f"Selam {user.mention}, üst yönetim ve uzman ekibimiz konuyu incelemek için birazdan burada olacaktır.\n\nHello {user.mention}, staff has been notified.",
            color=discord.Color.teal()
        )
        embed.set_footer(text="Apexium Command & Control Terminal", icon_url=bot.user.display_avatar.url)
        await ticket_channel.send(embed=embed, view=CloseTicketView())
        await log_event(guild, "🎟️ Destek Terminali Başlatıldı", f"**Kullanıcı:** {user.mention}\n**Kanal:** {ticket_channel.mention}", discord.Color.green())

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 TERMINATE TICKET / KAPAT", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        lang = get_lang(interaction.user.id)
        msg = "Kanal 5 saniye içinde imha edilecektir..." if lang == 'tr' else "Terminating session in 5 seconds..."
        await interaction.response.send_message(msg)
        await log_event(interaction.guild, "🔒 Destek Talebi Sonlandırıldı", f"**Kapatan:** {interaction.user.mention}\n**Kanal:** {interaction.channel.name}", discord.Color.red())
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- AUTOMATIC LEVEL DÖNGÜSÜ ---
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
                await log_event(guild, "👑 EXPERT LEVEL UP (Master Gamer)", f"**Oyuncu:** {member.mention}\n**Süre:** {days} Gün", discord.Color.gold())
            elif days >= 30 and days < 365 and l3_role and l3_role not in member.roles:
                await member.add_roles(l3_role)
                if l2_role in member.roles: await member.remove_roles(l2_role)
                await log_event(guild, "🔥 LEVEL UP (Level 3 Gamer)", f"**Oyuncu:** {member.mention}\n**Süre:** {days} Gün", discord.Color.purple())
            elif days >= 7 and days < 30 and l2_role and l2_role not in member.roles:
                await member.add_roles(l2_role)
                if l1_role in member.roles: await member.remove_roles(l1_role)
                await log_event(guild, "⚡ LEVEL UP (Level 2 Gamer)", f"**Oyuncu:** {member.mention}\n**Süre:** {days} Gün", discord.Color.blue())

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching, name="Apexium Universe | /help")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print(f'⚡ [SYSTEM] Apexium Security Bot [{bot.user.name}] Aktif!')
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
        print("✅ [SYSTEM] Slash Komutları Senkronize Edildi!")
    except Exception as e:
        print(f"Hata: {e}")

# YETKİSİZ ROL EKLEME ENGELLEYİCİ
@bot.event
async def on_member_update(before, after):
    guild = after.guild
    if before.roles != after.roles:
        added = [r for r in after.roles if r not in before.roles]
        if not added: return

        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            executor = entry.user
            if executor and not executor.bot and executor.id != guild.owner_id:
                admin_role = discord.utils.get(guild.roles, name="🛠️ Admin")
                is_executor_admin = admin_role in executor.roles if admin_role else False
                
                if not is_executor_admin:
                    for role in added:
                        await after.remove_roles(role)
                    await log_event(guild, "🚨 İZİNSİZ ROL MÜDAHALESİ ENGELLENDİ", f"**İşlemi Yapan:** {executor.mention}\n**Hedef:** {after.mention}\n**Engellenen Rol:** {', '.join([r.name for r in added])}", discord.Color.red())
                    return

@bot.event
async def on_member_join(member):
    guild = member.guild
    welcome_channel = discord.utils.get(guild.channels, name="welcome")
    if welcome_channel:
        embed = discord.Embed(
            title=f"⚡ APEXIUM CORE HAS DETECTED A NEW PLAYER ⚡",
            description=f"Aramıza hoş geldin {member.mention}!\n\nLütfen önce aşağıdaki menüden ülkenizi seçin.\nPlease select your country below to start verification.",
            color=discord.Color.gold()
        )
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        embed.set_image(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed, view=CountrySelectView())
    
    await log_event(guild, "📥 Yeni Oyuncu Bağlandı", f"**Oyuncu:** {member.mention} ({member.tag})", discord.Color.blue())

@bot.event
async def on_member_remove(member):
    await log_event(member.guild, "📤 Oyuncu Bağlantısı Koptu", f"**Oyuncu:** {member.mention} ({member.tag})", discord.Color.dark_orange())

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild: return
    content = message.content if message.content else "*Medya / Dosya*"
    await log_event(message.guild, "🗑️ Mesaj İmha Edildi", f"**Yazar:** {message.author.mention}\n**Kanal:** {message.channel.mention}\n**İçerik:** {content}", discord.Color.red())

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content: return
    await log_event(before.guild, "✏️ Mesaj Güncellendi", f"**Yazar:** {before.author.mention}\n**Kanal:** {before.channel.mention}\n**Önce:** {before.content}\n**Sonra:** {after.content}", discord.Color.orange())

def create_rules_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title=f"📜 {guild.name.upper()} — SYSTEM PROTOCOLS / SUNUCU KURALLARI",
        description="Sunucu güvenliği ve düzeni için aşağıdaki protokollerin ihlali kesinlikle yasaktır.\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=discord.Color.gold()
    )
    if guild.icon:
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(
        name="1️⃣ Saygı ve İletişim / Conduct & Respect",
        value="• Saygısızlık, küfür, argo, haysiyet kırıcı kelimeler ve toksik davranışlar **BAN** sebebidir.\n"
              "• Zero tolerance for profanity, hate speech, or toxicity.",
        inline=False
    )
    embed.add_field(
        name="2️⃣ Spam ve Reklam / Spam & Promotion",
        value="• Reklam yapmak, izinsiz link paylaşmak ve DM üzerinden davet atmak yasaktır.\n"
              "• Self-promotion or unsolicited links are strictly forbidden.",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Discord Şartları / Discord ToS",
        value="• Resmi Discord Topluluk İlkeleri ve Hizmet Şartlarına uyulması zorunludur.\n"
              "• Compliance with Official Discord ToS is mandatory.",
        inline=False
    )
    embed.add_field(
        name="✅ VERIFICATION / ONAY",
        value="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
              "Aşağıdaki **VERIFY ACCESS** butonuna basarak tüm sunucu kanallarına erişim sağlayabilirsiniz.",
        inline=False
    )
    embed.set_footer(text="Apexium Autonomous Defense Network", icon_url=bot.user.display_avatar.url)
    return embed

# --- HERKESE AÇIK 4 KOMUT ---

@bot.tree.command(name="info", description="Apexium evreni, geliştirici ve sunucu hakkında detaylı uzman bilgiler.")
async def info_command(interaction: discord.Interaction):
    guild = interaction.guild
    owner = guild.owner

    embed = discord.Embed(
        title="🏃 APEXIUM: PARKOUR CHRONICLES",
        description="**Apexium: Parkour Chronicles** evrenine hoş geldiniz!\n"
                    "Yüksek temposu, dinamik low-poly dünyası ve refleks odaklı parkur mekanikleriyle bağımsız aksiyon oyunu projesi.\n"
                    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=discord.Color.gold()
    )
    embed.add_field(name="🎮 Oyun Özellikleri", value="• **Tür:** 3D Action Parkour\n• **Motor:** Unreal Engine 5\n• **Sistem:** Dinamik Tuzaklar, Zaman Yarışı & Checkpoints", inline=False)
    embed.add_field(name="👑 Oyun Tasarımcısı & Kurucu", value=f"• **Lead Developer:** {owner.mention if owner else 'Berat Eşkiler (@pufDev0)'}\n• **Profil:** `{owner.name if owner else 'pufDev0'}`\n• **Unvan:** Game Designer, 3D Modeler & Developer", inline=False)
    embed.add_field(name="📊 Sunucu Ağ Bilgisi", value=f"• **Topluluk:** {guild.name}\n• **Toplam Üye:** {guild.member_count}\n• **Kuruluş:** {guild.created_at.strftime('%d.%m.%Y')}", inline=False)

    if owner and owner.display_avatar: embed.set_thumbnail(url=owner.display_avatar.url)
    embed.set_footer(text="Apexium Core Intelligence • Developed by Berat Eşkiler", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="Apexium Core erişim ve komut rehberi.")
async def help_command(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title=f"⚡ {guild.name.upper()} — OYUNCU REHBERİ & PROTOKOL",
        description="Apexium sunucusunda kullanabileceğiniz temel komutlar ve rehber aşağıdadır:\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        color=discord.Color.green()
    )
    embed.add_field(name="🌐 1. Ülke Seçimi", value="`#welcome` kanalından ülkenizi seçin.", inline=False)
    embed.add_field(name="📜 2. Kimlik Doğrulama", value="`#rules` kanalına gidip **VERIFY ACCESS** butonuna basarak kanalları açın.", inline=False)
    embed.add_field(name="🏃 3. Oyun Bilgileri", value="`/info` yazarak oyun detaylarına ve geliştirici profiline ulaşın.", inline=False)
    embed.add_field(name="📩 4. Destek Masası", value="Destek almak için `#create-ticket` kanalındaki butona basın.", inline=False)
    embed.add_field(name="🏓 5. Erişim Komutları", value="• `/ping` — Ağ gecikmesini ölçer\n• `/info` — Oyun ve Yapımcı Bilgisi\n• `/language` — Dil panelini açar\n• `/help` — Bu rehber panelini gösterir", inline=False)

    embed.set_footer(text="Apexium Autonomous Command Center", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="language", description="Select your language / Dilinizi ve ülkenizi seçin.")
async def language(interaction: discord.Interaction):
    embed = discord.Embed(title="🌐 LANGUAGE & REGION SELECTION", description="Lütfen aşağıdaki menüden ülkenizi seçin / Select your sector below:", color=discord.Color.blurple())
    embed.set_footer(text="Apexium Regional Routing", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, view=CountrySelectView(), ephemeral=True)

@bot.tree.command(name="ping", description="Botun ağ gecikmesini ve sistem tepki süresini ölçer.")
async def ping(interaction: discord.Interaction):
    ms = round(bot.latency * 1000)
    embed = discord.Embed(
        title="⚡ APEXIUM NETWORK STATUS",
        description=f"🌐 Core Latency: **{ms}ms**\n🛡️ System Status: **ALL SYSTEMS OPERATIONAL**",
        color=discord.Color.green()
    )
    embed.set_footer(text="Apexium Core Performance Monitor", icon_url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- YÖNETİCİ KOMUTLARI ---

@bot.tree.command(name="sunucukur", description="Adımlı doğrulama ve kilitli izin yapısını kurar.")
@app_commands.default_permissions(administrator=True)
async def setup_server(interaction: discord.Interaction):
    if not is_owner(interaction):
        await interaction.response.send_message("❌ Bu komut sadece **Sunucu Sahibi (Owner)** tarafından çalıştırılabilir!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # 1. KANALLARI SİL
    for channel in guild.channels:
        try: await channel.delete()
        except Exception: pass

    # 2. ESKİ ROLLERİ TEMİZLE
    for role in guild.roles:
        if role.name != "@everyone" and role < guild.me.top_role:
            try: await role.delete()
            except Exception: pass

    # @everyone İZİNLERİ (Sadece okuyabilir, kanal seçebilir)
    try:
        everyone_perms = discord.Permissions(
            read_messages=True, send_messages=False, connect=False, speak=False,
            manage_roles=False, manage_channels=False, manage_guild=False, administrator=False
        )
        await guild.default_role.edit(permissions=everyone_perms)
    except Exception: pass

    # 3. YENİ ROLLER
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

    try: await interaction.user.add_roles(owner_role, dev_role)
    except Exception: pass

    # --- KANAL İZİN MİMARİSİ ---

    # WELCOME VE RULES: Herkes görebilir ama mesaj yazamaz
    public_verification_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False)
    }

    # BİLGİ KANALLARI (Sadece Rolü Olanlar Görebilir, Mesaj Yazamaz)
    info_read_only = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        l1_gamer: discord.PermissionOverwrite(read_messages=True, send_messages=False)
    }

    # SOHBET KANALLARI (Sadece Rolü Olanlar Görebilir VE Mesaj Yazabilir)
    comm_full_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        l1_gamer: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # BİLET KANALI (Sadece Rolü Olanlar Görebilir, Mesaj Yazamaz - Butona Basabilir)
    ticket_channel_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        l1_gamer: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # LOGS KANALI (Sadece Admin & Owner)
    logs_admin_only = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        mod_role: discord.PermissionOverwrite(read_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    staff_text_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        owner_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    # SES KANALLARI (Sadece Rolü Olanlar Bağlanabilir)
    public_voice_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False),
        l1_gamer: discord.PermissionOverwrite(read_messages=True, connect=True, speak=True)
    }

    locked_voice_perm = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    staff_voice_perm = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        mod_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    # --- KANALLARI OLUŞTURMA ---

    # 1. INFORMATION KATEGORİSİ
    info_cat = await guild.create_category("INFORMATION")
    welcome_ch = await info_cat.create_text_channel("welcome", overwrites=public_verification_perm)
    rules_ch = await info_cat.create_text_channel("rules", overwrites=public_verification_perm)
    download_ch = await info_cat.create_text_channel("download-game", overwrites=info_read_only)
    await info_cat.create_text_channel("announcements", overwrites=info_read_only)
    await info_cat.create_text_channel("updates", overwrites=info_read_only)
    await info_cat.create_text_channel("logs", overwrites=logs_admin_only)
    await info_cat.create_text_channel("staff-commands", overwrites=staff_text_perm)

    welcome_embed = discord.Embed(
        title="🌐 STEP 1: SELECT YOUR COUNTRY / ÜLKENİZİ SEÇİN",
        description="Sunucuya erişmek için lütfen aşağıdaki menüden ülkenizi seçin.\nÜlkenizi seçtikten sonra `#rules` kanalına geçerek erişimi doğrulayın.\n\nPlease select your country below.",
        color=discord.Color.gold()
    )
    await welcome_ch.send(embed=welcome_embed, view=CountrySelectView())

    await rules_ch.send(embed=create_rules_embed(guild), view=RuleAcceptView())

    download_embed = discord.Embed(title="🎮 DOWNLOAD APEXIUM: PARKOUR CHRONICLES", description=f"**Apexium Trial** sürümünü aşağıdaki bağlantıdan hemen indirebilirsiniz!\n\n🔗 **Direct Link:**\n{GAME_ITCH_LINK}", color=discord.Color.green())
    download_embed.set_image(url=DOWNLOAD_GAME_BANNER)
    download_embed.set_footer(text="Apexium Studio • Official itch.io Release", icon_url=bot.user.display_avatar.url)
    await download_ch.send(embed=download_embed, view=DownloadGameView())

    # 2. COMMUNITY KATEGORİSİ
    comm_cat = await guild.create_category("COMMUNITY")
    await comm_cat.create_text_channel("general-chat", overwrites=comm_full_perm)
    await comm_cat.create_text_channel("media-share", overwrites=comm_full_perm)
    await comm_cat.create_text_channel("bot-commands", overwrites=comm_full_perm)

    # 3. SUPPORT & FEEDBACK KATEGORİSİ
    supp_cat = await guild.create_category("SUPPORT & FEEDBACK")
    await supp_cat.create_text_channel("bug-reports", overwrites=comm_full_perm)
    await supp_cat.create_text_channel("suggestions", overwrites=comm_full_perm)
    ticket_channel = await supp_cat.create_text_channel("create-ticket", overwrites=ticket_channel_perm)

    ticket_embed = discord.Embed(title="🎫 APEXIUM OFFICIAL SUPPORT SYSTEM", description="Sorunlarınız ve yetkili iletişimi için bilet oluşturun / Click below to open a support ticket.", color=discord.Color.blue())
    ticket_embed.set_image(url=DOWNLOAD_GAME_BANNER)
    await ticket_channel.send(embed=ticket_embed, view=TicketView())

    # 4. VOICE CHANNELS KATEGORİSİ
    voice_cat = await guild.create_category("VOICE CHANNELS")
    await voice_cat.create_voice_channel("Public Lounge", overwrites=public_voice_perm)
    await voice_cat.create_voice_channel("Squad 1", overwrites=public_voice_perm)
    await voice_cat.create_voice_channel("🔒 Staff Voice", overwrites=staff_voice_perm)
    await voice_cat.create_voice_channel("🔒 Owner & Admin Voice", overwrites=locked_voice_perm)

    embed_done = discord.Embed(title="🔥 APEXIUM STEPPED ACCESS SYSTEM DEPLOYED", description="✅ Kusursuz izin mimarisi kuruldu! Artık ülke seçilip kural onaylanmadan hiçbir sohbet kanalı görünmez.", color=discord.Color.gold())
    try: await interaction.followup.send(embed=embed_done, ephemeral=True)
    except Exception: pass

# /duyuru
@bot.tree.command(name="duyuru", description="Duyurular kanalına görsel ve açıklamalı sinematik duyuru gönderir.")
@app_commands.default_permissions(administrator=True)
async def announce(interaction: discord.Interaction, title: str, message: str, image_url: str = None):
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return

    ann_channel = discord.utils.get(interaction.guild.channels, name="announcements")
    if not ann_channel:
        await interaction.response.send_message("❌ `#announcements` kanalı bulunamadı.", ephemeral=True)
        return

    guild = interaction.guild
    embed = discord.Embed(title=f"📢 {title.upper()}", description=f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n{message}\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", color=discord.Color.gold())
    if guild.icon: embed.set_author(name=f"{guild.name} • OFFICIAL ANNOUNCEMENT", icon_url=guild.icon.url)
    else: embed.set_author(name=f"{guild.name} • OFFICIAL ANNOUNCEMENT")

    final_image = image_url if image_url else DEFAULT_ANNOUNCEMENT_BANNER
    embed.set_image(url=final_image)
    embed.set_footer(text=f"Announced by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.timestamp = datetime.now(timezone.utc)

    await ann_channel.send(content="@everyone", embed=embed)
    await interaction.response.send_message("📢 Duyuru paylaşıldı!", ephemeral=True)

# /kurallar
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

# /ban
@bot.tree.command(name="ban", description="Bir kullanıcıyı sunucudan yasaklar.")
@app_commands.default_permissions(ban_members=True)
async def ban_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🚫 {member.mention} yasaklandı.", ephemeral=True)

# /kick
@bot.tree.command(name="kick", description="Bir kullanıcıyı sunucudan atar.")
@app_commands.default_permissions(kick_members=True)
async def kick_user(interaction: discord.Interaction, member: discord.Member, reason: str = "Sebep belirtilmedi"):
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👞 {member.mention} atıldı.", ephemeral=True)

# /mute
@bot.tree.command(name="mute", description="Bir kullanıcıyı belirli bir süre susturur (dakika).")
@app_commands.default_permissions(moderate_members=True)
async def mute_user(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Sebep belirtilmedi"):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"🤐 {member.mention} {minutes} dakika susturuldu.", ephemeral=True)

# /unmute
@bot.tree.command(name="unmute", description="Bir kullanıcının susturmasını kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def unmute_user(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 {member.mention} susturması kaldırıldı.", ephemeral=True)

# /lock
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

# /unlock
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

# /sil
@bot.tree.command(name="sil", description="Belirtilen miktarda mesajı kanaldan siler.")
@app_commands.default_permissions(manage_messages=True)
async def purge_messages(interaction: discord.Interaction, amount: int):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Yetkiniz yetersiz!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🗑️ {len(deleted)} mesaj silindi.", ephemeral=True)

# --- ANA ÇALIŞTIRMA DÖNGÜSÜ ---
async def main():
    await start_web_server()
    token = os.getenv("DISCORD_TOKEN") or "MTU0NDY5OTM3OTA5OTc3MDg5Mg.GLxPNK.zX5pectcQSndVdHhUNVGitM9V5GqD_kWGQ5L_0"
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
