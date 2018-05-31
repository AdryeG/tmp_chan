from disco.bot.plugin import Plugin

import logging
import random


class VocalCrewsPlugin(Plugin):
    known_guilds = set()
    crew_creators = set()
    used_names = {}

    def load(self, ctx):
        super(VocalCrewsPlugin, self).load(ctx)
        if self.config['enabled']:
            self.register_listener(self.on_guild_create, 'event', 'GuildCreate')

    def create_crew_channel(self, channel, user):
        self.crew_creators.remove(channel.id)
        category_config = self.config['categories'].get(str(channel.parent.id), {})
        crew_names = category_config.get('crew_names', self.config['crew_names'])
        crew_formatter = category_config.get('crew_formatter', self.config['crew_formatter'])
        if channel.parent.id not in self.used_names:
            self.used_names[channel.parent.id] = set()
        used_names = self.used_names[channel.parent.id]
        available_names = set(crew_names).difference(used_names)
        chosen_name = random.choice(list(available_names))
        used_names.add(chosen_name)
        if len(used_names) == len(crew_names):
            used_names.clear()
        new_channel_name = crew_formatter.format(chosen_name)
        logging.info(
            'Creating Crew "{}" (#{}) (requested by {})'.format(
                new_channel_name,
                channel.id,
                str(user)
            )
        )
        channel.set_name(new_channel_name)
        return channel

    def create_creator_channel(self, category):
        category_config = self.config['categories'].get(str(category.id), {})
        channel_name = category_config.get('new_crew_name', self.config['new_crew_name'])
        channel_limit = category_config.get('crew_size', self.config['crew_size'])
        creator = category.create_voice_channel(channel_name, user_limit=channel_limit)
        self.crew_creators.add(creator.id)
        return creator

    def on_guild_create(self, event):
        guild = event.guild
        if guild.id in self.known_guilds:
            return
        logging.info('Setuping voice channels for guild "{}" (#{})'.format(guild.name, guild.id))
        config_categories = [int(c) for c in self.config['categories']]
        categories = set(guild.channels).intersection(config_categories)
        for category_id in categories:
            category = guild.channels[category_id]
            logging.info('Setting category "{}" (#{}) as vocal crew category'.format(category.name, category.id))
            guild_channels = list(category.guild.channels.values())
            for channel in guild_channels:
                if channel.parent_id and channel.parent_id == category_id:
                    delete_channel = True
                    voice_states = list(channel.guild.voice_states.values())
                    for voice_state in voice_states:
                        if voice_state.channel_id == channel.id:
                            delete_channel = False
                            break
                    if delete_channel:
                        logging.info('Deleting unknown voice channel "{}" (#{})'.format(channel.name, channel.id))
                        channel.delete()
                    else:
                        logging.warning(
                            'Leaving non-empty unknown voice channel "{}" (#{})'.format(channel.name, channel.id)
                        )
            self.create_creator_channel(category)
        if not self.known_guilds:
            self.register_listener(self.on_voice_state_update, 'event', 'VoiceStateUpdate')
        self.known_guilds.add(guild.id)

    def on_voice_state_update(self, event):
        if event.state.channel_id in self.crew_creators:
            channel = self.create_crew_channel(event.state.channel, user=event.state.user)
            self.create_creator_channel(channel.parent)
        guild_channels = list(event.state.guild.channels.values())
        deleting_crew_channels = []
        managed_categories = [int(c) for c in self.config['categories']]
        for channel in guild_channels:
            if channel.parent_id in managed_categories and channel.id not in self.crew_creators:
                deleting_crew_channels.append(channel.id)
        voice_states = list(event.state.guild.voice_states.values())
        for voice_state in voice_states:
            if voice_state.channel_id in deleting_crew_channels:
                deleting_crew_channels.remove(voice_state.channel_id)
        for channel_id in deleting_crew_channels:
            channel = event.state.guild.channels[channel_id]
            logging.info('Deleting empty channel "{}" (#{})'.format(channel.name, channel.id))
            channel.delete()
