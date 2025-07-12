# commands/clan/report/member_left.py

"""Member left reporting functionality (placeholder)"""

import lightbulb

loader = lightbulb.Loader()

# async def show_member_left_flow(ctx: lightbulb.components.MenuContext, user_id: str):
#     """Placeholder for member left functionality"""
#     await ctx.respond(
#         "⚠️ This feature is coming soon!",
#         ephemeral=True
#     )
#
#     # Example integration for clan report-points "Member Left" button
#
#     async def get_members_who_left_recently(mongo, clan_tag: str) -> list:
#         """
#         For the report-points "Member Left" button
#         Gets all players who:
#         1. Joined THIS clan in the last 12 days
#         2. Have now left the clan
#         Returns their info including bid points
#         """
#         from datetime import datetime, timedelta
#
#         # Find recruits who joined this clan in last 12 days and left
#         pipeline = [
#             {
#                 "$match": {
#                     "is_expired": False,  # Still within 12-day window
#                     "recruitment_history": {
#                         "$elemMatch": {
#                             "clan_tag": clan_tag,
#                             "recruited_at": {"$gte": datetime.utcnow() - timedelta(days=12)},
#                             "left_at": {"$ne": None}  # They have left
#                         }
#                     }
#                 }
#             },
#             {
#                 "$project": {
#                     "player_tag": 1,
#                     "player_name": 1,
#                     "player_th_level": 1,
#                     "discord_user_id": 1,
#                     # Extract the specific recruitment for this clan
#                     "clan_recruitment": {
#                         "$filter": {
#                             "input": "$recruitment_history",
#                             "as": "recruitment",
#                             "cond": {"$eq": ["$$recruitment.clan_tag", clan_tag]}
#                         }
#                     }
#                 }
#             }
#         ]
#
#         results = await mongo.new_recruits.aggregate(pipeline).to_list(length=None)
#
#         # Format for display
#         members_who_left = []
#         for recruit in results:
#             if recruit["clan_recruitment"]:
#                 recruitment = recruit["clan_recruitment"][0]
#                 members_who_left.append({
#                     "player_tag": recruit["player_tag"],
#                     "player_name": recruit["player_name"],
#                     "th_level": recruit["player_th_level"],
#                     "bid_points": recruitment["bid_amount"],
#                     "joined_at": recruitment["recruited_at"],
#                     "left_at": recruitment["left_at"],
#                     "duration_days": recruitment["duration_days"],
#                     "discord_user_id": recruit["discord_user_id"]
#                 })
#
#         return members_who_left
#
#     async def handle_member_left_button(ctx, clan_tag: str, mongo):
#         """
#         Example handler for the "Member Left" button in clan report-points
#         """
#         members = await get_members_who_left_recently(mongo, clan_tag)
#
#         if not members:
#             await ctx.respond("No members have left this clan in the last 12 days.", ephemeral=True)
#             return
#
#         # Build response showing members who left
#         response_text = "**Members who left in the last 12 days:**\n\n"
#
#         for member in members:
#             response_text += (
#                 f"**{member['player_name']}** ({member['player_tag']})\n"
#                 f"• TH Level: {member['th_level']}\n"
#                 f"• Bid Points: {member['bid_points']}\n"
#                 f"• Stayed for: {member['duration_days']} days\n"
#                 f"• Discord: <@{member['discord_user_id']}>\n\n"
#             )
#
#         # You could add buttons here to reclaim points, etc.
#         await ctx.respond(response_text, ephemeral=True)
#
#     # When a member joins a clan (after winning bid)
#     async def on_bid_finalized(mongo, player_tag: str, clan_tag: str, clan_name: str,
#                                recruited_by: str, bid_amount: int):
#         """
#         Call this when a bid is finalized and player joins a clan
#         Links with your existing clan_bidding collection
#         """
#         # Update new_recruits collection
#         await record_recruitment(
#             mongo,
#             player_tag=player_tag,
#             clan_tag=clan_tag,
#             clan_name=clan_name,
#             recruited_by=recruited_by,
#             bid_amount=bid_amount
#         )
#
#         # Your existing clan_bidding finalization logic continues...
#
#     # When detecting a member left (via API or event)
#     async def on_member_left_clan(mongo, player_tag: str, clan_tag: str):
#         """
#         Call this when you detect a member has left a clan
#         """
#         success = await record_member_left(mongo, player_tag, clan_tag)
#
#         if success:
#             # Could trigger point reclamation logic here
#             # Could notify the clan leader
#             # etc.
#             pass