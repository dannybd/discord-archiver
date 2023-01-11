#! /usr/bin/python3

import asyncio
import datetime
import discord
import json
import re
import time

intents = discord.Intents.all()
client = discord.Client(intents=intents)

with open("config.json", "r") as f:
    config = json.load(f)
    GUILD = int(config["guild"])
    TOKEN = config["token"]
    LOG_MESSAGES = config["log_messages"]
    LOG_AUDIT_LOGS = config["log_audit_logs"]
    LOG_TO_ALL = config["log_to_all"]
    CATEGORIES_TO_SKIP = config["categories_to_skip"]


@client.event
async def on_ready():
    try:
        print("done!")
        await gen_run()
    except Exception as e:
        print("\nERROR:", e)
    finally:
        await client.close()


async def gen_run():
    print("Loading guild... ", end="")
    guild = client.get_guild(GUILD)
    if guild == None:
        raise Exception("Missing guild!")
    print("done!")

    if LOG_MESSAGES:
        print("Begin archival of messages (see ./logs/messages):")
        await gen_run_for_messages(guild)
        print("Done!")

    if LOG_AUDIT_LOGS:
        print("Begin archival of audit_logs (see ./logs/audit_logs):")
        await gen_run_for_audit_logs(guild)
        print("Done!")

    print("Archival complete.")


async def gen_run_for_messages(guild):
    all_logs = []
    for channel in guild.text_channels:
        if channel.category.name in CATEGORIES_TO_SKIP:
            print(
                f"    Skipping channel #{channel.name} in {channel.category.name}",
            )
            continue
        filename = "logs/messages/{}.{}.json".format(channel.name, channel.id)
        print(
            "    Archiving channel #{} ({}) ... ".format(
                channel.name,
                channel.id,
            ),
            end="",
        )
        logs = []
        async for message in channel.history(limit=None, oldest_first=True):
            log = {
                "created_at": str(message.created_at),
                "id": str(message.id),
                "author": user_data(message.author),
                "channel": basic_data(message.channel),
                "content": message.system_content,
                "type": str(message.type)[12:],
            }
            if message.attachments:
                log["attachments"] = attachments_data(message.attachments)
            if message.embeds:
                log["embeds"] = embeds_data(message.embeds)
            if message.reactions:
                log["reactions"] = await reactions_data(message.reactions)
            if message.edited_at:
                log["edited_at"] = str(message.edited_at)
            if message.pinned:
                log["pinned"] = True

            assert_log_is_json_serializable(log)
            logs.append(log)

        with open(filename, "w") as f:
            json.dump(logs, f)
        print("done.")

        if LOG_TO_ALL:
            all_logs.extend(logs)

    if LOG_TO_ALL:
        print("    Archiving all messages in one file (__all__.json) ... ", end="")
        all_logs.sort(key=lambda log: log["created_at"])
        with open("logs/messages/__all__.json", "w") as f:
            json.dump(all_logs, f)
        print("saved.")


async def gen_run_for_audit_logs(guild):
    all_logs = []
    for action in discord.AuditLogAction:
        logs = []
        action_name = str(action)[15:]
        print(
            "    Archiving audit logs of type {} ... ".format(action_name),
            end="",
        )
        async for entry in guild.audit_logs(limit=None, action=action):
            log = {
                "created_at": str(entry.created_at),
                "id": entry.id,
                "action": str(entry.action)[15:],
                "user": user_data(entry.user),
                "target": audit_target_data(entry.target),
                "type": "audit",
                "before": audit_diff_data(entry.before),
                "after": audit_diff_data(entry.after),
            }
            if entry.reason:
                log["reason"] = entry.reason
            if entry.extra:
                log["extra"] = str(entry.extra)

            assert_log_is_json_serializable(log)
            logs.append(log)

        # Due to a bug in discord.py, we needed to pull these in chronological
        # order. This flips that, then runs the sort just to be sure.
        # By flipping it first we make the sort much more efficient.
        logs.reverse()
        logs.sort(key=lambda log: log["created_at"])
        filename = "logs/audit_logs/" + action_name + ".json"
        with open(filename, "w") as f:
            json.dump(logs, f)
        print("saved.")

        if LOG_TO_ALL:
            all_logs.extend(logs)

    if LOG_TO_ALL:
        print(
            "    Archiving all audit logs in one file (__all__.json) ... ",
            end="",
        )
        all_logs.sort(key=lambda log: log["created_at"])
        with open("logs/audit_logs/__all__.json", "w") as f:
            json.dump(all_logs, f)
        print("saved.")


def user_data(user):
    return {
        "id": str(user.id),
        "name": user.name + "#" + user.discriminator,
    }


def basic_data(channel):
    return {
        "id": str(channel.id),
        "name": channel.name,
    }


def attachments_data(attachments):
    data = []
    for attachment in attachments:
        datum = {
            "id": str(attachment.id),
            "filename": attachment.filename,
            "size": attachment.size,
            "url": attachment.url,
        }
        if attachment.height:
            datum["height"] = attachment.height
        if attachment.width:
            datum["width"] = attachment.width

        data.append(datum)
    return data


def embeds_data(embeds):
    return [
        {
            "title": str(embed.title),
            "description": str(embed.description),
            "url": str(embed.url),
        }
        for embed in embeds
        if embed
    ]


async def reactions_data(reactions):
    data = []
    if not reactions:
        return data
    for reaction in reactions:
        datum = {
            "emoji": str(reaction.emoji),
            "count": reaction.count,
            # "reactors": [],
        }
        # async for user in reaction.users():
        #     datum["reactors"].append(user_data(user))
        data.append(datum)
    return data


def audit_target_data(target):
    if isinstance(target, discord.User):
        data = user_data(target)
        data["type"] = "User"
    elif isinstance(target, discord.Member):
        data = user_data(target)
        data["type"] = "Member"
    elif isinstance(target, discord.abc.GuildChannel):
        data = basic_data(target)
        data["type"] = "Channel"
    elif isinstance(target, discord.Guild):
        data = basic_data(target)
        data["type"] = "Guild"
    elif isinstance(target, discord.Object):
        data = {
            "id": target.id,
            "created_at": str(target.created_at),
            "type": "Object",
        }
    elif isinstance(target, discord.Role):
        data = {
            "id": target.id,
            "created_at": str(target.created_at),
            "name": target.name,
            "type": "Role",
        }
    elif isinstance(target, discord.Invite):
        data = {
            "id": target.id,
            "created_at": str(target.created_at),
            "max_age": target.max_age,
            "temporary": target.temporary,
            "uses": target.uses,
            "max_uses": target.max_uses,
            "inviter": audit_target_data(target.inviter),
            "channel": audit_target_data(target.channel),
            "url": target.url,
            "type": "Invite",
        }
    else:
        data = {"str": str(target), "type": str(type(target))}
    return data


def audit_diff_data(diff):
    return {attr: str(value) for attr, value in iter(diff)}


def assert_log_is_json_serializable(log):
    try:
        json.dumps(log)
    except Exception as e:
        print("Log doesn't serialize properly:", log)
        raise e


@client.event
async def on_error(*args, **kwargs):
    await client.close()


async def main():
    await client.start(TOKEN)


if __name__ == "__main__":
    print("Connecting to Discord bot... ", end="")
    asyncio.run(main())
