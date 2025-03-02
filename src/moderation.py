import discord
from discord.ext import commands
import asyncio

# Store moderator role ID
MODERATOR_ROLE_ID = None  # Set this in config or env var

async def handle_moderation(ctx, question, answer, bot):
    """
    Handle the moderation workflow for Venice AI responses
    
    Args:
        ctx: Discord context
        question: User's original question
        answer: Answer from Venice AI
        bot: Discord bot instance
    """
    # Create an embed for the response
    embed = discord.Embed(
        title="Venice AI Response",
        color=discord.Color.blue()
    )
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=answer, inline=False)
    
    # Add buttons for moderator actions
    view = ModerationView(question, answer, ctx.author, bot)
    
    # Send the moderation message
    mod_message = await ctx.send(embed=embed, view=view)
    
    # Store the message reference for later edits
    view.message = mod_message

class ModerationView(discord.ui.View):
    def __init__(self, question, answer, requester, bot):
        super().__init__(timeout=600)  # 10 minute timeout
        self.question = question
        self.answer = answer
        self.requester = requester
        self.bot = bot
        self.message = None
        
    async def interaction_check(self, interaction):
        """Check if the user has moderation permissions"""
        if MODERATOR_ROLE_ID:
            return MODERATOR_ROLE_ID in [role.id for role in interaction.user.roles]
        # If no moderator role is set, allow only server admins
        return interaction.user.guild_permissions.administrator
    
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction, button):
        """Approve and send the response as is"""
        await interaction.response.defer()
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        # Update the moderation message view
        await self.message.edit(view=self)
        
        # Send the approved message to the original channel
        embed = discord.Embed(
            title="Venice AI",
            description=self.answer,
            color=discord.Color.green()
        )
        await interaction.channel.send(f"<@{self.requester.id}>, here's your answer:", embed=embed)
    
    @discord.ui.button(label="Edit", style=discord.ButtonStyle.primary)
    async def edit_response(self, interaction, button):
        """Open a modal to edit the response"""
        # Create and send the edit modal
        modal = EditResponseModal(self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction, button):
        """Reject the response and don't send it"""
        await interaction.response.defer()
        
        # Disable all buttons
        for child in self.children:
            child.disabled = True
        
        # Update the message
        embed = self.message.embeds[0]
        embed.color = discord.Color.red()
        embed.set_footer(text="Response rejected by moderator")
        await self.message.edit(embed=embed, view=self)
        
        # Notify the requester
        await interaction.channel.send(
            f"<@{self.requester.id}>, sorry, a moderator has rejected the response to your question."
        )

class EditResponseModal(discord.ui.Modal, title="Edit Response"):
    """Modal for editing responses"""
    
    answer = discord.ui.TextInput(
        label="Edit the response",
        style=discord.TextStyle.paragraph,
        placeholder="Edit the response here...",
        required=True,
        max_length=2000
    )
    
    def __init__(self, view):
        super().__init__()
        self.parent_view = view
        self.answer.default = view.answer
    
    async def on_submit(self, interaction):
        # Update the answer in the parent view
        self.parent_view.answer = self.answer.value
        
        # Disable all buttons in parent view
        for child in self.parent_view.children:
            child.disabled = True
        
        # Update the moderation message
        embed = self.parent_view.message.embeds[0]
        embed.set_field_at(1, name="Answer (Edited)", value=self.answer.value, inline=False)
        embed.color = discord.Color.orange()
        embed.set_footer(text=f"Edited by {interaction.user.display_name}")
        
        await self.parent_view.message.edit(embed=embed, view=self.parent_view)
        await interaction.response.defer()
        
        # Send the edited response to the user
        response_embed = discord.Embed(
            title="Venice AI",
            description=self.answer.value,
            color=discord.Color.orange()
        )
        response_embed.set_footer(text="This response was edited by a moderator")
        
        await interaction.channel.send(
            f"<@{self.parent_view.requester.id}>, here's your answer:", 
            embed=response_embed
        )