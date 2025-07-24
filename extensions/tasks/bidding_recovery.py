"""
Task to recover bidding sessions after bot restart
"""

import asyncio
import hikari
import lightbulb
from datetime import datetime, timezone
from bson import ObjectId

from utils.mongo import MongoClient

loader = lightbulb.Loader()

# Global variables
bot_instance = None
mongo_client = None
recovery_complete = False


@loader.listener(hikari.StartedEvent)
@lightbulb.di.with_di
async def on_bot_started(
    event: hikari.StartedEvent,
    mongo: MongoClient = lightbulb.di.INJECTED
) -> None:
    """Recover bidding sessions on bot startup"""
    global bot_instance, mongo_client, recovery_complete
    
    bot_instance = event.app
    mongo_client = mongo
    
    # Wait a bit for other systems to initialize
    await asyncio.sleep(5)
    
    print("[Bidding Recovery] Starting bidding session recovery...")
    
    try:
        # Find all active bidding sessions
        active_sessions = await mongo.button_store.find({
            "type": "bidding_session"
        }).to_list(length=None)
        
        if not active_sessions:
            print("[Bidding Recovery] No active bidding sessions found")
            recovery_complete = True
            return
        
        print(f"[Bidding Recovery] Found {len(active_sessions)} active bidding session(s)")
        
        now = datetime.now(timezone.utc)
        recovered_count = 0
        expired_count = 0
        
        for session in active_sessions:
            try:
                bid_end_time = session.get("bidEndTime")
                if not bid_end_time:
                    print(f"[Bidding Recovery] Session {session['_id']} missing bidEndTime, skipping")
                    continue
                
                # If bid_end_time is naive (no timezone), make it aware by assuming UTC
                if bid_end_time.tzinfo is None:
                    bid_end_time = bid_end_time.replace(tzinfo=timezone.utc)
                
                # Check if session has expired
                if bid_end_time <= now:
                    # Process immediately
                    print(f"[Bidding Recovery] Session {session['_id']} has expired, processing immediately")
                    await process_expired_bidding(session)
                    expired_count += 1
                else:
                    # Calculate remaining time and create new timer
                    remaining_seconds = (bid_end_time - now).total_seconds()
                    print(f"[Bidding Recovery] Session {session['_id']} has {remaining_seconds:.0f} seconds remaining")
                    
                    # Create recovery task
                    asyncio.create_task(
                        resume_bidding_timer(session, remaining_seconds)
                    )
                    recovered_count += 1
                    
            except Exception as e:
                print(f"[Bidding Recovery] Error processing session {session.get('_id')}: {e}")
        
        print(f"[Bidding Recovery] Recovery complete: {recovered_count} resumed, {expired_count} expired")
        recovery_complete = True
        
    except Exception as e:
        print(f"[Bidding Recovery] Fatal error during recovery: {e}")
        recovery_complete = True


async def resume_bidding_timer(session: dict, remaining_seconds: float):
    """Resume a bidding timer with remaining time"""
    try:
        # Wait for remaining time
        await asyncio.sleep(remaining_seconds)
        
        # Process the bidding end
        await process_expired_bidding(session)
        
    except asyncio.CancelledError:
        print(f"[Bidding Recovery] Timer cancelled for session {session['_id']}")
    except Exception as e:
        print(f"[Bidding Recovery] Error in resumed timer for session {session['_id']}: {e}")


async def process_expired_bidding(session: dict):
    """Process a bidding session that has expired"""
    from extensions.commands.recruit.bidding import process_bidding_end
    
    try:
        recruit_id = session.get("recruitId")
        session_id = session.get("_id")
        thread_id = int(session.get("threadId", 0))
        message_id = int(session.get("messageId", 0))
        
        if not all([recruit_id, session_id, thread_id]):
            print(f"[Bidding Recovery] Missing required data for session {session_id}")
            return
        
        print(f"[Bidding Recovery] Processing bidding end for recruit {recruit_id}")
        
        # Call the bidding end processor
        await process_bidding_end(
            bot_instance,
            mongo_client,
            recruit_id,
            session_id,
            thread_id,
            message_id
        )
        
        print(f"[Bidding Recovery] Successfully processed bidding for recruit {recruit_id}")
        
    except Exception as e:
        print(f"[Bidding Recovery] Error processing bidding end: {e}")
        
        # Try to at least reset the recruit's activeBid flag
        try:
            if session.get("recruitId"):
                # Check if it's a channel not found error
                update_fields = {"activeBid": False}
                if "Unknown Channel" in str(e) or "404" in str(e):
                    # Channel doesn't exist, mark ticket as closed
                    update_fields["ticket_open"] = False
                    print(f"[Bidding Recovery] Channel not found, marking ticket as closed")
                
                await mongo_client.new_recruits.update_one(
                    {"_id": ObjectId(session["recruitId"])},
                    {"$set": update_fields}
                )
                print(f"[Bidding Recovery] Reset activeBid flag for recruit {session['recruitId']}")
                
                # Clean up the failed session so it doesn't get reprocessed
                await mongo_client.button_store.delete_one({"_id": session.get("_id")})
                print(f"[Bidding Recovery] Cleaned up failed session {session.get('_id')}")
        except Exception as reset_error:
            print(f"[Bidding Recovery] Failed to reset activeBid: {reset_error}")


@loader.command
class BiddingRecoveryStatus(
    lightbulb.SlashCommand,
    name="bidding-recovery-status",
    description="Check the status of bidding recovery",
    default_member_permissions=hikari.Permissions.ADMINISTRATOR
):
    @lightbulb.invoke
    @lightbulb.di.with_di
    async def invoke(
        self,
        ctx: lightbulb.Context,
        mongo: MongoClient = lightbulb.di.INJECTED
    ) -> None:
        await ctx.defer(ephemeral=True)
        
        # Check active sessions
        active_sessions = await mongo.button_store.find({
            "type": "bidding_session"
        }).to_list(length=None)
        
        # Check stuck recruits
        stuck_recruits = await mongo.new_recruits.find({
            "activeBid": True
        }).to_list(length=None)
        
        now = datetime.now(timezone.utc)
        
        response = f"## 🎯 Bidding Recovery Status\n\n"
        response += f"**Recovery Complete:** {'✅ Yes' if recovery_complete else '❌ No'}\n"
        response += f"**Active Bidding Sessions:** {len(active_sessions)}\n"
        response += f"**Recruits with activeBid=true:** {len(stuck_recruits)}\n\n"
        
        if active_sessions:
            response += "**Active Sessions:**\n"
            for session in active_sessions[:5]:  # Show first 5
                bid_end_time = session.get("bidEndTime")
                if bid_end_time:
                    if bid_end_time > now:
                        remaining = (bid_end_time - now).total_seconds() / 60
                        response += f"• {session.get('playerName', 'Unknown')} - {remaining:.1f} min remaining\n"
                    else:
                        response += f"• {session.get('playerName', 'Unknown')} - EXPIRED\n"
                else:
                    response += f"• {session.get('playerName', 'Unknown')} - No end time\n"
        
        await ctx.respond(response, ephemeral=True)