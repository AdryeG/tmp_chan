from disco.bot.plugin import Plugin

import logging
import random


class VocalCrewsPlugin(Plugin):
    crew_creators = set()
    used_names = set()

    def load(self, ctx):
        super(VocalCrewsPlugin, self).load(ctx)
        if self.config['enabled']:
            self.register_listener(self.on_guild_create, 'event', 'GuildCreate')

    def on_guild_create(self, event):
        guild = event.guild
        logging.info('Setuping voice channels for guild "{}" (#{})'.format(guild.name, guild.id))
        categories = set(guild.channels).intersection(self.config['categories'])
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
            creator = category.create_voice_channel(
                self.config['new_crew_name'],
                user_limit=self.config['crew_size']
            )
            self.crew_creators.add(creator.id)
        self.register_listener(self.on_voice_state_update, 'event', 'VoiceStateUpdate')

    def on_voice_state_update(self, event):
        guild_channels = list(event.state.guild.channels.values())
        deleting_crew_channels = []
        for channel in guild_channels:
            if channel.parent_id in self.config['categories'] and channel.id not in self.crew_creators:
                deleting_crew_channels.append(channel.id)
        voice_states = list(event.state.guild.voice_states.values())
        for voice_state in voice_states:
            if voice_state.channel_id in deleting_crew_channels:
                deleting_crew_channels.remove(voice_state.channel_id)
        for channel_id in deleting_crew_channels:
            channel = event.state.guild.channels[channel_id]
            logging.info('Deleting empty channel "{}" (#{})'.format(channel.name, channel.id))
            channel.delete()
        if event.state.channel_id in self.crew_creators:
            channel = event.state.channel
            available_names = set(self.config['crew_names']).difference(self.used_names)
            chosen_name = random.choice(list(available_names))
            self.used_names.add(chosen_name)
            if len(self.used_names) == len(self.config['crew_names']):
                self.used_names = set()
            new_channel_name = self.config['crew_formatter'].format(chosen_name)
            logging.info(
                'Creating Crew "{}" (#{}) (requested by {})'.format(
                    new_channel_name,
                    channel.id,
                    str(event.state.user)
                )
            )
            channel.set_name(new_channel_name)
            creator = channel.parent.create_voice_channel(
                self.config['new_crew_name'],
                user_limit=self.config['crew_size']
            )
            self.crew_creators.remove(channel.id)
            self.crew_creators.add(creator.id)
