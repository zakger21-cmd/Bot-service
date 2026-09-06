import io
import discord
from discord import app_commands

from config import STAFF_ROLE_ID, ORDER_CATEGORY_ID, SUPPORT_CATEGORY_ID, LOG_CHANNEL_ID


def is_staff():
    """Décorateur pour restreindre une slash command au rôle Staff (pour utilisation sur les commandes)."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return _is_staff_member(interaction.guild, interaction.user)
    return app_commands.check(predicate)


def _is_staff_member(guild: discord.Guild, member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role = guild.get_role(STAFF_ROLE_ID)
    return role is not None and role in member.roles


def is_ticket_channel(channel: discord.abc.GuildChannel) -> bool:
    """Vérifie qu'un salon fait partie d'une des catégories de tickets (commande ou support)."""
    category_id = getattr(channel, "category_id", None)
    return category_id in (ORDER_CATEGORY_ID, SUPPORT_CATEGORY_ID)


async def build_transcript_file(channel: discord.TextChannel) -> discord.File:
    """Génère un fichier texte contenant tous les messages du salon."""
    messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
    lines = [
        f"[{m.created_at.strftime('%Y-%m-%d %H:%M')}] {m.author}: {m.content}"
        for m in messages
    ]
    transcript = "\n".join(lines) if lines else "Aucun message."
    return discord.File(fp=io.BytesIO(transcript.encode("utf-8")), filename=f"{channel.name}.txt")


async def update_embed_field(message: discord.Message, field_name: str, new_value: str):
    """Met à jour un champ précis dans l'embed d'un message (utilisé pour statut/prise en charge)."""
    embed = message.embeds[0]
    for i, field in enumerate(embed.fields):
        if field.name == field_name:
            embed.set_field_at(i, name=field.name, value=new_value, inline=field.inline)
            break
    return embed


class CloseTicketView(discord.ui.View):
    """Bouton persistant pour fermer un ticket (commande ou support), avec transcript automatique."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fermer le ticket",
        style=discord.ButtonStyle.secondary,
        emoji="🔒",
        custom_id="design_close_ticket",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_staff_member(interaction.guild, interaction.user):
            await interaction.response.send_message(
                "❌ Seul le staff peut fermer ce ticket.", ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Fermeture du ticket dans 5 secondes...")

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            file = await build_transcript_file(interaction.channel)
            await log_channel.send(
                content=f"📁 Ticket fermé : **{interaction.channel.name}** (par {interaction.user})",
                file=file,
            )

        await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")
