import os
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Hoş geldin mesajı ve otorol için bu ŞARTTIR.

bot = commands.Bot(command_prefix="!", intents=intents)

user_languages = {}

# --- DİL SEÇİM VİDGET'I ---
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

# --- TİCKET SİSTEMİ ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Create Ticket / Bilet Aç", style=discord.ButtonStyle.success, custom_id="create_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"Zaten açık bir destek talebiniz var: {existing_channel.mention}", ephemeral=True)
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
        await interaction.response.send_message(f"Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title="Support / Destek Talebi",
            description=f"Merhaba {user.mention}, yetkililer en kısa sürede sizinle ilgilenecektir.\nDestek talebini kapatmak için aşağıdaki butona basabilirsiniz.",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=embed, view=CloseTicketView())

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close / Kapat", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Kanal 5 saniye içinde silinecektir...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- BOT HAZIR OLDUĞUNDA ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} olarak giriş yaptı!')
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} adet slash komutu başarıyla yüklendi!")
    except Exception as e:
        print(f"Hata: {e}")

# --- YENİ BİRİ SUNUCUYA KATILDIĞINDA (OTOROL VE HOŞ GELDİN) ---
@bot.event
async def on_member_join(member):
    guild = member.guild
    
    # 1. Otomatik Rol Verme
    player_role = discord.utils.get(guild.roles, name="🎮 Gamer")
    if player_role:
        try:
            await member.add_roles(player_role)
            print(f"{member.name} kişisine Gamer rolü verildi.")
        except Exception as e:
            print(f"Rol verme hatası: {e}")

    # 2. Hoş Geldin Mesajı Atma
    # Hoş geldin mesajını general-chat kanalına atacak
    welcome_channel = discord.utils.get(guild.channels, name="general-chat")
    
    if welcome_channel:
        embed = discord.Embed(
            title="🎉 Sunucuya Hoş Geldin! / Welcome!",
            description=f"Selam {member.mention}! Oyunumuzun resmi Discord sunucusuna hoş geldin.\n"
                        f"Welcome to the official game Discord server!\n\n"
                        f"Kayıt olmak için sohbete `/language` yazarak dilini seçebilirsin.\n"
                        f"Type `/language` in chat to select your language.",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await welcome_channel.send(embed=embed)


# --- GELİŞMİŞ SUNUCU KURMA KOMUTU ---
@bot.tree.command(name="sunucukur", description="Var olan kanalları siler, rolleri ve tüm oyun kanallarını sıfırdan kurar.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_server(interaction: discord.Interaction):
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

    admin_only_voice = {
        guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
        owner_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        admin_role: discord.PermissionOverwrite(connect=True, view_channel=True),
        mod_role: discord.PermissionOverwrite(connect=True, view_channel=True)
    }

    info_cat = await guild.create_category("INFORMATION")
    await info_cat.create_text_channel("rules", overwrites=read_only_for_everyone)
    await info_cat.create_text_channel("announcements", overwrites=read_only_for_everyone)
    await info_cat.create_text_channel("updates", overwrites=read_only_for_everyone)

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

    try:
        await interaction.followup.send("✅ Tüm eski kanallar temizlendi, Roller oluşturuldu ve Sunucu Yapısı başarıyla kuruldu!", ephemeral=True)
    except Exception:
        pass

@setup_server.error
async def setup_server_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Bu komutu sadece **Yöneticiler** kullanabilir!", ephemeral=True)

# --- DİĞER KOMUTLAR ---
@bot.tree.command(name="language", description="Select your language / Dilinizi seçin")
async def language(interaction: discord.Interaction):
    await interaction.response.send_message("Lütfen dil seçin / Please select a language:", view=LanguageSelectView(), ephemeral=True)

@bot.tree.command(name="ping", description="Botun gecikmesini gösterir.")
async def ping(interaction: discord.Interaction):
    lang = user_languages.get(interaction.user.id, 'tr')
    ms = round(bot.latency * 1000)
    if lang == 'en':
        await interaction.response.send_message(f"🏓 Pong! Latency: **{ms}ms**", ephemeral=True)
    else:
        await interaction.response.send_message(f"🏓 Pong! Gecikme Süresi: **{ms}ms**", ephemeral=True)

bot.run("MTU0NDY5OTM3OTA5OTc3MDg5Mg.GtLecy.mO6zMD4OT1iDGni8mk996ZEs1Lt30fWuYRwwhQ")
