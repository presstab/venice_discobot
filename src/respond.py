import discord

async def post_response(ctx, question, llm_response, bot, server_config, response_time=None):
    """
    Format and send the Venice AI response as a Discord embed message
    
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
    answer = llm_response['answer']
    truncated_answer = (answer[:MAX_LENGTH - 3] + "...") if len(answer) > MAX_LENGTH else answer
    if len(answer) > MAX_LENGTH:
        print(answer)

    if server_config['answer_style'] != "embedded":
        return await ctx.send(truncated_answer)

    # Create an embed for the response
    embed = discord.Embed(
        title=f"{server_config['bot_name']} Response ({server_config['model']})",
        color=discord.Color.blue()
    )
    # embed.add_field(name="Server", value=ctx.guild.name, inline=False)
    # embed.add_field(name="User", value=ctx.author.display_name, inline=False)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=truncated_answer, inline=False)
    citations_str = ""

    for citation in llm_response['citations']:
        citations_str += citation['url'] + "\n"

    if len(llm_response['citations']) > 0:
        embed.add_field(name="Citations", value=citations_str, inline=False)

    # Add response time if available
    if response_time is not None:
        embed.add_field(name="Response Time", value=f"{response_time:.2f} seconds", inline=True)
    
    # Send the message
    return await ctx.send(embed=embed)
