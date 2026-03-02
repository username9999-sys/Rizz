/**
 * Rizz Discord Bot
 * Features: Task management, notifications, moderation, fun commands
 */

const { Client, GatewayIntentBits, Collection, ActivityType } = require('discord.js');
const { config } = require('dotenv');
const { logger } = require('./utils/logger');
const { connectDB } = require('./services/database');
const { registerCommands } = require('./services/commandLoader');

config();

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildPresences,
  ],
});

// Command collection
client.commands = new Collection();

// Initialize bot
async function init() {
  try {
    // Connect to database
    await connectDB();
    logger.info('Database connected');

    // Register commands
    await registerCommands(client);
    logger.info('Commands registered');

    // Login
    await client.login(process.env.DISCORD_TOKEN);
    logger.info('Bot logged in successfully');
  } catch (error) {
    logger.error('Initialization failed:', error);
    process.exit(1);
  }
}

// Ready event
client.once('ready', () => {
  logger.info(`Bot ready! Logged in as ${client.user.tag}`);
  
  // Set activity
  client.user.setPresence({
    activities: [{ 
      name: '/help | Rizz Bot', 
      type: ActivityType.Watching 
    }],
    status: 'online',
  });
});

// Error handling
process.on('unhandledRejection', (error) => {
  logger.error('Unhandled promise rejection:', error);
});

process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception:', error);
});

// Start the bot
init();

module.exports = client;
