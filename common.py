import discord
from discord import app_commands
from discord.ext import commands

from cogs.utils import is_staff, is_ticket_channel, CloseTicketView


class CommonTickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket-ajouter", description="Ajoute un membre au ticket actuel (réservé au staff)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(membre="Le membre à ajouter au ticket")
    @is_staff()
    async def ticket_ajouter(self, interaction: discord.Interaction, membre: discord.Member):
        if not is_ticket_channel(interaction.channel):
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée dans un salon de ticket.", ephemeral=True
            )
            return

        await interaction.channel.set_permissions(
            membre, view_channel=True, send_messages=True, read_message_history=True
        )
        embed = discord.Embed(
            description=f"➕ {membre.mention} a été ajouté au ticket par {interaction.user.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ticket-retirer", description="Retire un membre du ticket actuel (réservé au staff)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(membre="Le membre à retirer du ticket")
    @is_staff()
    async def ticket_retirer(self, interaction: discord.Interaction, membre: discord.Member):
        if not is_ticket_channel(interaction.channel):
            await interaction.response.send_message(
                "❌ Cette commande doit être utilisée dans un salon de ticket.", ephemeral=True
            )
            return

        await interaction.channel.set_permissions(membre, overwrite=None)
        embed = discord.Embed(
            description=f"➖ {membre.mention} a été retiré du ticket par {interaction.user.mention}.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            message = "❌ Seul le staff peut utiliser cette commande."
        else:
            print(f"Erreur dans une commande du Cog CommonTickets : {error}")
            message = "❌ Une erreur est survenue lors de l'exécution de la commande."

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    bot.add_view(CloseTicketView())
    await bot.add_cog(CommonTickets(bot))
