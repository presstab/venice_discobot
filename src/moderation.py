import discord

async def post_response(ctx, question, answer, bot, llm_model):
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
        title=f"Venice AI Response ({llm_model})",
        color=discord.Color.blue()
    )
    # embed.add_field(name="Server", value=ctx.guild.name, inline=False)
    # embed.add_field(name="User", value=ctx.author.display_name, inline=False)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=answer, inline=False)
    
    # Send the moderation message
    message = await ctx.send(embed=embed)
    #message = await ctx.send(answer)
