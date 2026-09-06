import discord
from discord import app_commands
from discord.ext import commands

from config import STAFF_ROLE_ID, SUPPORT_CATEGORY_ID
from cogs.utils import is_staff, _is_staff_member, update_embed_field, CloseTicketView


SUPPORT_STATUS_MAP = {
    "ouvert": ("🟡 Ouvert", discord.Color.gold()),
    "en_cours": ("🟠 En cours", discord.Color.orange()),
    "resolu": ("✅ Résolu", discord.Color.green()),
}


async def create_support_channel(interaction: discord.Interaction) -> discord.TextChannel:
    guild = interaction.guild
    category = guild.get_channel(SUPPORT_CATEGORY_ID)
    staff_role = guild.get_role(STAFF_ROLE_ID)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True, attach_files=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True
        ),
    }
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )

    channel_name = f"support-{interaction.user.name}".lower().replace(" ", "-")
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=f"Support pour {interaction.user} (ID: {interaction.user.id})",
    )

    info_embed = discord.Embed(title="🎫 Ticket support", color=SUPPORT_STATUS_MAP["ouvert"][1])
    info_embed.add_field(name="👤 Membre", value=interaction.user.mention, inline=True)
    info_embed.add_field(name="📌 Statut", value=SUPPORT_STATUS_MAP["ouvert"][0], inline=True)
    info_embed.add_field(name="🙋 Pris en charge par", value="Personne pour l'instant", inline=True)
    info_embed.set_footer(text=f"ID du membre : {interaction.user.id}")

    ping = staff_role.mention if staff_role else ""
    await ticket_channel.send(
        content=f"{interaction.user.mention} {ping}", embed=info_embed, view=SupportInfoView()
    )
    await ticket_channel.send(
        content="👋 Décris ta question ou ton problème ci-dessous, un membre du staff va te répondre.",
        view=CloseTicketView(),
    )

    return ticket_channel


# ============================================================
# PANEL D'INFOS DU TICKET SUPPORT : statut + prise en charge
# ============================================================
class SupportStatusSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ouvert", emoji="🟡", value="ouvert"),
            discord.SelectOption(label="En cours", emoji="🟠", value="en_cours"),
            discord.SelectOption(label="Résolu", emoji="✅", value="resolu"),
        ]
        super().__init__(
            placeholder="Changer le statut du ticket...",
            options=options,
            custom_id="design_support_status_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _is_staff_member(interaction.guild, interaction.user):
            await interaction.response.send_message(
                "❌ Seul le staff peut changer le statut.", ephemeral=True
            )
            return

        label, color = SUPPORT_STATUS_MAP[self.values[0]]
        embed = await update_embed_field(interaction.message, "📌 Statut", label)
        embed.color = color
        await interaction.response.edit_message(embed=embed)
        await interaction.channel.send(f"📌 Statut changé en **{label}** par {interaction.user.mention}.")


class SupportInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SupportStatusSelect())

    @discord.ui.button(
        label="Prendre en charge",
        style=discord.ButtonStyle.primary,
        emoji="🙋",
        custom_id="design_support_claim",
        row=1,
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_staff_member(interaction.guild, interaction.user):
            await interaction.response.send_message(
                "❌ Seul le staff peut prendre en charge un ticket.", ephemeral=True
            )
            return

        embed = await update_embed_field(interaction.message, "🙋 Pris en charge par", interaction.user.mention)
        await interaction.response.edit_message(embed=embed)
        await interaction.channel.send(f"🙋 Ce ticket est maintenant pris en charge par {interaction.user.mention}.")


# ============================================================
# BOUTON PERSISTANT : PANEL DE SUPPORT
# ============================================================
class SupportPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Ouvrir un ticket support",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="design_open_support",
    )
    async def open_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        expected_name = f"support-{interaction.user.name}".lower().replace(" ", "-")
        existing = discord.utils.get(interaction.guild.text_channels, name=expected_name)
        if existing:
            await interaction.response.send_message(
                f"⚠️ Tu as déjà un ticket support ouvert : {existing.mention}.", ephemeral=True
            )
            return

        await interaction.response.send_message("⏳ Ouverture de ton ticket...", ephemeral=True)
        ticket_channel = await create_support_channel(interaction)
        await interaction.edit_original_response(content=f"✅ Ton ticket a été créé : {ticket_channel.mention}")


# ============================================================
# COG
# ============================================================
class Support(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="panel-support", description="Poste le panel de support")
    @app_commands.default_permissions(manage_guild=True)
    @is_staff()
    async def panel_support(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🆘・SUPPORT",
            description=(
                "Une question ou un problème ? Clique sur le bouton ci-dessous pour ouvrir "
                "un ticket privé avec notre équipe.\n\n"
                "⏱️ Temps de réponse : généralement dans les 24 heures."
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message("✅ Panel envoyé.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=SupportPanelView())

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            message = "❌ Seul le staff peut utiliser cette commande."
        else:
            print(f"Erreur dans une commande du Cog Support : {error}")
            message = "❌ Une erreur est survenue lors de l'exécution de la commande."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    bot.add_view(SupportPanelView())
    bot.add_view(SupportInfoView())
    await bot.add_cog(Support(bot))
