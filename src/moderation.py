import discord

async def post_response(ctx, question, answer, bot, llm_model, response_time=None):
    """
    Handle the moderation workflow for Venice AI responses
    
    Args:
        ctx: Discord context
        question: User's original question
        answer: Answer from Venice AI
        bot: Discord bot instance
        llm_model: Model name used for the response
        response_time: Time taken to generate the response (in seconds)
    """
    # Truncate answer if it's too long
    MAX_LENGTH = 1024
    truncated_answer = (answer[:MAX_LENGTH - 3] + "...") if len(answer) > MAX_LENGTH else answer
    if len(answer) > MAX_LENGTH:
        print(answer)

    # Create an embed for the response
    embed = discord.Embed(
        title=f"Venice AI Response ({llm_model})",
        color=discord.Color.blue()
    )
    # embed.add_field(name="Server", value=ctx.guild.name, inline=False)
    # embed.add_field(name="User", value=ctx.author.display_name, inline=False)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=truncated_answer, inline=False)
    
    # Add response time if available
    if response_time is not None:
        embed.add_field(name="Response Time", value=f"{response_time:.2f} seconds", inline=True)
    
    # Send the moderation message
    message = await ctx.send(embed=embed)
    #message = await ctx.send(answer)
