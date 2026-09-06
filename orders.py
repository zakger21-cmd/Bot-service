import discord
from discord import app_commands
from discord.ext import commands

from config import STAFF_ROLE_ID, ORDER_CATEGORY_ID
from cogs.utils import is_staff, _is_staff_member, update_embed_field, CloseTicketView


ORDER_STATUS_MAP = {
    "attente_paiement": ("🟡 En attente de paiement", discord.Color.gold()),
    "en_cours": ("🟠 En cours de création", discord.Color.orange()),
    "livre": ("✅ Livré", discord.Color.green()),
    "annule": ("❌ Annulé", discord.Color.red()),
}


# ============================================================
# FORMULAIRE COURT DE COMMANDE
# ============================================================
class OrderModal(discord.ui.Modal, title="Nouvelle commande de design"):
    type_design = discord.ui.TextInput(
        label="Type de design souhaité",
        placeholder="Ex: Logo, bannière, icône, publicité...",
        max_length=100,
    )
    description = discord.ui.TextInput(
        label="Décris ta demande",
        style=discord.TextStyle.paragraph,
        placeholder="Style, couleurs, éléments à inclure...",
        max_length=1000,
    )
    budget = discord.ui.TextInput(
        label="Budget (en Robux)",
        placeholder="Ex: 200 Robux",
        max_length=50,
    )
    reference = discord.ui.TextInput(
        label="Référence (lien image, optionnel)",
        required=False,
        placeholder="Lien vers une image/inspiration",
        max_length=300,
    )
    deadline = discord.ui.TextInput(
        label="Délai souhaité (optionnel)",
        required=False,
        placeholder="Ex: avant vendredi, pas urgent...",
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Création de ta commande en cours...", ephemeral=True)
        ticket_channel = await create_order_channel(interaction, self)
        await interaction.edit_original_response(
            content=f"✅ Ta commande a été créée : {ticket_channel.mention}"
        )


async def create_order_channel(interaction: discord.Interaction, modal: OrderModal) -> discord.TextChannel:
    guild = interaction.guild
    category = guild.get_channel(ORDER_CATEGORY_ID)
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

    channel_name = f"commande-{interaction.user.name}".lower().replace(" ", "-")
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=f"Commande de {interaction.user} (ID: {interaction.user.id})",
    )

    info_embed = discord.Embed(title="🛒 Nouvelle commande", color=ORDER_STATUS_MAP["attente_paiement"][1])
    info_embed.add_field(name="👤 Client", value=interaction.user.mention, inline=True)
    info_embed.add_field(name="📌 Statut", value=ORDER_STATUS_MAP["attente_paiement"][0], inline=True)
    info_embed.add_field(name="🙋 Pris en charge par", value="Personne pour l'instant", inline=True)
    info_embed.add_field(name="🎨 Type de design", value=modal.type_design.value, inline=False)
    info_embed.add_field(name="📝 Description", value=modal.description.value, inline=False)
    info_embed.add_field(name="💰 Budget", value=modal.budget.value, inline=True)
    if modal.deadline.value:
        info_embed.add_field(name="⏱️ Délai souhaité", value=modal.deadline.value, inline=True)
    if modal.reference.value:
        info_embed.add_field(name="🔗 Référence", value=modal.reference.value, inline=False)
    info_embed.set_footer(text=f"ID du client : {interaction.user.id}")

    ping = staff_role.mention if staff_role else ""
    await ticket_channel.send(
        content=f"{interaction.user.mention} {ping}", embed=info_embed, view=OrderInfoView()
    )
    await ticket_channel.send(
        content="💳 Rappel : le paiement sera confirmé avant la livraison du design.",
        view=CloseTicketView(),
    )

    return ticket_channel


# ============================================================
# PANEL D'INFOS DE LA COMMANDE : statut + prise en charge
# ============================================================
class OrderStatusSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="En attente de paiement", emoji="🟡", value="attente_paiement"),
            discord.SelectOption(label="En cours de création", emoji="🟠", value="en_cours"),
            discord.SelectOption(label="Livré", emoji="✅", value="livre"),
            discord.SelectOption(label="Annulé", emoji="❌", value="annule"),
        ]
        super().__init__(
            placeholder="Changer le statut de la commande...",
            options=options,
            custom_id="design_order_status_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not _is_staff_member(interaction.guild, interaction.user):
            await interaction.response.send_message(
                "❌ Seul le staff peut changer le statut.", ephemeral=True
            )
            return

        label, color = ORDER_STATUS_MAP[self.values[0]]
        embed = await update_embed_field(interaction.message, "📌 Statut", label)
        embed.color = color
        await interaction.response.edit_message(embed=embed)
        await interaction.channel.send(f"📌 Statut changé en **{label}** par {interaction.user.mention}.")


class OrderInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OrderStatusSelect())

    @discord.ui.button(
        label="Prendre en charge",
        style=discord.ButtonStyle.primary,
        emoji="🙋",
        custom_id="design_order_claim",
        row=1,
    )
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_staff_member(interaction.guild, interaction.user):
            await interaction.response.send_message(
                "❌ Seul le staff peut prendre en charge une commande.", ephemeral=True
            )
            return

        embed = await update_embed_field(interaction.message, "🙋 Pris en charge par", interaction.user.mention)
        await interaction.response.edit_message(embed=embed)
        await interaction.channel.send(
            f"🙋 Cette commande est maintenant prise en charge par {interaction.user.mention}."
        )


# ============================================================
# BOUTON PERSISTANT : PANEL DE COMMANDE
# ============================================================
class OrderPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Commander",
        style=discord.ButtonStyle.success,
        emoji="🛒",
        custom_id="design_open_order",
    )
    async def open_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        expected_name = f"commande-{interaction.user.name}".lower().replace(" ", "-")
        existing = discord.utils.get(interaction.guild.text_channels, name=expected_name)
        if existing:
            await interaction.response.send_message(
                f"⚠️ Tu as déjà une commande en cours : {existing.mention}.", ephemeral=True
            )
            return
        await interaction.response.send_modal(OrderModal())


# ============================================================
# COG
# ============================================================
class Orders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="panel-commande", description="Poste le panel de commandes de design")
    @app_commands.default_permissions(manage_guild=True)
    @is_staff()
    async def panel_commande(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒・SYSTÈME DE COMMANDE",
            description=(
                "Clique sur le bouton ci-dessous pour commencer une commande. Tu devras remplir "
                "un court formulaire avec les informations nécessaires concernant ton design.\n\n"
                "💰 **Paiement :** Robux\n"
                "🎨 **Services :** Logos, bannières, icônes, publicités et demandes personnalisées.\n\n"
                "📌 **Avant de commander :**\n"
                "Assure-toi d'être prêt à payer avant d'ouvrir une commande. Ne crée pas de commande "
                "si tu n'es pas prêt à procéder au paiement.\n"
                "💳 Le paiement sera confirmé avant la livraison du design.\n"
                "⏱️ Temps de réponse : généralement dans les 24 heures.\n\n"
                "⭐ **Après la livraison :**\n"
                "N'hésite pas à laisser un avis après avoir reçu et testé ton design."
            ),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message("✅ Panel envoyé.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=OrderPanelView())

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            message = "❌ Seul le staff peut utiliser cette commande."
        else:
            print(f"Erreur dans une commande du Cog Orders : {error}")
            message = "❌ Une erreur est survenue lors de l'exécution de la commande."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    bot.add_view(OrderPanelView())
    bot.add_view(OrderInfoView())
    await bot.add_cog(Orders(bot))
