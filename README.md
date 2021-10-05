# discord-archiver
Archives a Discord server: messages and audit logs.

Uses discord.py and a bot with Administrative permissions to your server.

## Usage (bash)
```
# Set up config.json:
mv config.json{.template,}
nano config.json

# Run it:
python3 archive.py
```

## Caveats

* Threads aren't supported
* Role information isn't captured (beyond audit logs, which you could probably use to reconstruct what happened?)


## Contributing

If you want to tweak what this script does, I recommend taking a look at the discord.py API documentation:
https://discordpy.readthedocs.io/en/stable/api.html

Should be pretty straightforward to find things which you can add from there.
