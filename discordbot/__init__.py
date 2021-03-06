import asyncio
from threading import Thread

# pip
import discord


class DiscordBot:

    specifications = {
        "maxMessageLength": 2000,  # https://discordia.me/server-limits#other-limits
        "waitForReply": 5,
        "waitForExpectedReply": 360
    }

    def __init__(self, serv, token, prefix=None):
        """
        prefix - A string or tuple of strings

        """
        self.serv = serv
        self.token = token
        self.client = discord.Client()
        self.prefixes = prefix
        if isinstance(self.prefixes, list):
            self.prefixes = tuple(sorted(self.prefixes, key=len, reverse=True))
        if isinstance(self.prefixes, str) and self.prefixes.strip() == "":
            self.prefixes = None
        self.sentmessages = []

        @self.client.event
        async def on_ready():
            print('DiscordBot logged in')

        @self.client.event
        async def on_message(message):
            self.__on_message(message)

        @self.client.event
        async def on_guild_join(guild):
            self.__on_guild_join(guild)

    def run(self):
        def worker(client, loop, token):
            asyncio.set_event_loop(loop)
            loop.create_task(client.start(token))
            loop.run_forever()

        loop = asyncio.get_event_loop()
        t = Thread(target=worker, args=(self.client, loop, self.token))
        t.daemon = True
        t.start()

        # self.client.run(self.token)

    def __on_guild_join(self, guild):
        msg = {
            "_bot": self,
            "_userId": guild.owner.id,
            "text": "/start",
            "__guild": guild,
            "__message": None,
            "__on_guild_join": True
        }
        channels = []
        for channel in guild.channels:
            if channel.type == discord.ChannelType.text and channel.permissions_for(
                    guild.me).send_messages:
                if channel.name == "general":
                    channel.position = -1
                channels.append(channel)

        if channels:
            channels.sort(key=lambda c: c.position)
            msg["__channel"] = channels[0]
            return self.serv._handleTextMessage(msg)
        return

    def __on_message(self, message):
        if message.author.bot:  # Do not reply to bot messages
            return

        text = message.content

        if self.prefixes is not None:
            if not text.startswith(self.prefixes):
                # Is this message a reply?
                is_reply = False
                for sentmessage in reversed(self.sentmessages):
                    if sentmessage.message and sentmessage.reply_to and sentmessage.message.guild == message.guild and sentmessage.message.channel == message.channel and sentmessage.reply_to.author == message.author:
                        diff = message.timestamp - sentmessage.message.timestamp
                        if (sentmessage.expects_reply and diff.seconds <
                                self.specifications["waitForExpectedReply"]) or diff.seconds < self.specifications["waitForReply"]:
                            is_reply = True
                            self.sentmessages.remove(sentmessage)
                            break
                if not is_reply:
                    # Do not reply to message
                    return
            else:
                # Remove prefix
                for prefix in self.prefixes:
                    if text.startswith(prefix):
                        text = text[len(prefix):].strip()
                        break

        msg = {
            "_bot": self,
            "_userId": message.author.id,
            "text": text,
            "__message": message,
            "__channel": message.channel,
            "__author": message.author,
        }

        return self.serv._handleTextMessage(msg)

    class MessageReply:
        def __init__(self, message, reply_to, expects_reply):
            self.message = message
            self.reply_to = reply_to
            self.expects_reply = expects_reply

    def __formatButtons(self, buttons):
        text = ""
        for button in buttons:
            if isinstance(button[1], str):
                text += "\n%s: %s" % (self.serv._emojize(
                    button[0]), self.serv._emojize(button[1]))
            else:
                text += "\n%s" % (self.serv._emojize(button[0]))
        if text:
            text = "\n" + text
        return text

    async def __send_message2(self, expects_reply, reply_to, destination, *args, **kwargs):
        m = await destination.send(*args, **kwargs)
        r = DiscordBot.MessageReply(m, reply_to, expects_reply)
        self.sentmessages.append(r)
        if len(self.sentmessages) > 1000:
            self.sentmessages = self.sentmessages[-30:]

    def __send_message(self, msg, expects_reply, *args, **kwargs):
        asyncio.ensure_future(
            self.__send_message2(
                expects_reply,
                msg["__message"],
                msg["__channel"],
                *args,
                **kwargs))

    def sendText(self, msg, text, buttons=None):
        text = self.serv._emojize(text)
        if buttons:
            text += self.__formatButtons(buttons)
        self.__send_message(msg, False, text)

    def sendQuestion(self, msg, text, buttons=None):
        text = self.serv._emojize(text)
        if buttons:
            text += self.__formatButtons(buttons)
        self.__send_message(msg, True, text)

    def sendLink(self, msg, url, buttons=None, text=""):
        # # Just send the raw URL as text
        #
        # if text:
        #     text = url + "\n" + self.serv._emojize(text)
        # else:
        #     text = url
        #
        # self.sendText(msg, text, buttons)
        # embed = discord.Embed(title = url, url = url)

        if buttons:
            text += self.__formatButtons(buttons)
        if text.strip():
            embed.description = text
        self.__send_message(msg, False, embed=embed)

    def sendPhoto(self, msg, url, buttons=None):
        embed = discord.Embed(url=url)
        embed.set_image(url=url)
        embed.set_footer(text=url)
        if buttons:
            text = self.__formatButtons(buttons)
            embed.description = text
        self.__send_message(msg, False, embed=embed)
