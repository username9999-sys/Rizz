const { REST, Routes } = require('discord.js');
const { readdirSync } = require('fs');
const { join } = require('path');
const { logger } = require('../utils/logger');

async function registerCommands(client) {
  const commands = [];
  const commandFiles = readdirSync(join(__dirname, '../commands')).filter(
    (file) => file.endsWith('.js')
  );

  for (const file of commandFiles) {
    const command = require(`../commands/${file}`);
    client.commands.set(command.data.name, command);
    commands.push(command.data.toJSON());
    logger.info(`Loaded command: ${command.data.name}`);
  }

  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

  try {
    logger.info('Started refreshing application (/) commands.');

    await rest.put(Routes.applicationCommands(process.env.CLIENT_ID), {
      body: commands,
    });

    logger.info('Successfully reloaded application (/) commands.');
  } catch (error) {
    logger.error('Error registering commands:', error);
  }
}

module.exports = { registerCommands };
