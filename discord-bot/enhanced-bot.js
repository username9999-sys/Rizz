/**
 * Rizz Discord Bot - Enhanced with AI & Economy
 * Features: AI chatbot, Economy system, Leveling, Mini-games
 */

const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const mongoose = require('mongoose');

mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/rizz_discord');

// ===== MODELS =====

const UserSchema = new mongoose.Schema({
  userId: { type: String, unique: true, required: true },
  guildId: String,
  
  // Economy
  balance: { type: Number, default: 0 },
  bank: { type: Number, default: 0 },
  
  // Leveling
  xp: { type: Number, default: 0 },
  level: { type: Number, default: 1 },
  messagesSent: { type: Number, default: 0 },
  
  // Inventory
  inventory: [{
    item: String,
    quantity: Number,
    type: String
  }],
  
  // Daily rewards
  lastDaily: Date,
  lastWork: Date,
  
  createdAt: { type: Date, default: Date.now }
});

const User = mongoose.model('User', UserSchema);

// ===== CLIENT SETUP =====

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers
  ]
});

// ===== ECONOMY SYSTEM =====

class EconomySystem {
  async getUser(userId, guildId) {
    let user = await User.findOne({ userId, guildId });
    if (!user) {
      user = await User.create({ userId, guildId });
    }
    return user;
  }
  
  async addBalance(userId, guildId, amount) {
    const user = await this.getUser(userId, guildId);
    user.balance += amount;
    await user.save();
    return user.balance;
  }
  
  async removeBalance(userId, guildId, amount) {
    const user = await this.getUser(userId, guildId);
    if (user.balance < amount) return false;
    user.balance -= amount;
    await user.save();
    return true;
  }
  
  async daily(userId, guildId) {
    const user = await this.getUser(userId, guildId);
    const now = new Date();
    
    if (user.lastDaily && now - user.lastDaily < 24 * 60 * 60 * 1000) {
      return { claimed: false, waitTime: user.lastDaily.getTime() + (24 * 60 * 60 * 1000) - now.getTime() };
    }
    
    const reward = 100 + (user.level * 10);
    user.balance += reward;
    user.lastDaily = now;
    await user.save();
    
    return { claimed: true, amount: reward };
  }
  
  async work(userId, guildId) {
    const user = await this.getUser(userId, guildId);
    const now = new Date();
    
    if (user.lastWork && now - user.lastWork < 60 * 60 * 1000) {
      return { worked: false, waitTime: user.lastWork.getTime() + (60 * 60 * 1000) - now.getTime() };
    }
    
    const jobs = [
      { name: 'Programmer', pay: 200 },
      { name: 'Designer', pay: 180 },
      { name: 'Writer', pay: 150 },
      { name: 'Teacher', pay: 170 }
    ];
    
    const job = jobs[Math.floor(Math.random() * jobs.length)];
    user.balance += job.pay;
    user.lastWork = now;
    await user.save();
    
    return { worked: true, job: job.name, pay: job.pay };
  }
}

const economy = new EconomySystem();

// ===== LEVELING SYSTEM =====

class LevelingSystem {
  async addXP(userId, guildId, amount) {
    const user = await User.findOne({ userId, guildId });
    if (!user) return;
    
    user.xp += amount;
    user.messagesSent++;
    
    // Level up formula: level^2 * 100
    const xpNeeded = user.level * user.level * 100;
    
    if (user.xp >= xpNeeded) {
      user.level++;
      user.xp = 0;
      return { leveledUp: true, newLevel: user.level };
    }
    
    await user.save();
    return { leveledUp: false };
  }
  
  async getRank(userId, guildId) {
    const user = await User.findOne({ userId, guildId });
    if (!user) return null;
    
    const xpNeeded = user.level * user.level * 100;
    
    return {
      level: user.level,
      xp: user.xp,
      xpNeeded,
      messagesSent: user.messagesSent,
      rank: await this.getRankPosition(userId, guildId)
    };
  }
  
  async getRankPosition(userId, guildId) {
    const users = await User.find({ guildId }).sort({ level: -1, xp: -1 });
    return users.findIndex(u => u.userId === userId) + 1;
  }
}

const leveling = new LevelingSystem();

// ===== AI CHATBOT =====

class AIChatbot {
  constructor() {
    this.conversations = new Map();
    this.responses = {
      greetings: ['hello', 'hi', 'hey', 'good morning', 'good evening'],
      thanks: ['thank', 'thanks', 'thx'],
      help: ['help', 'command', 'what can you do'],
      joke: ['joke', 'funny', 'laugh']
    };
  }
  
  async getResponse(message, userId) {
    const lowerMsg = message.toLowerCase();
    
    // Check conversation history
    const conv = this.conversations.get(userId) || [];
    conv.push({ role: 'user', content: message });
    this.conversations.set(userId, conv.slice(-10)); // Keep last 10
    
    // Simple pattern matching (in production: Use OpenAI API)
    if (this.responses.greetings.some(g => lowerMsg.includes(g))) {
      return 'Hello! 👋 How can I help you today?';
    }
    
    if (this.responses.thanks.some(t => lowerMsg.includes(t))) {
      return "You're welcome! 😊";
    }
    
    if (this.responses.help.some(h => lowerMsg.includes(h))) {
      return this.getHelpMessage();
    }
    
    if (this.responses.joke.some(j => lowerMsg.includes(j))) {
      const jokes = [
        "Why did the developer go broke? Because he used up all his cache! 😄",
        "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
        "How many programmers does it take to change a light bulb? None, that's a hardware problem! 💡"
      ];
      return jokes[Math.floor(Math.random() * jokes.length)];
    }
    
    // Default responses
    const defaults = [
      "That's interesting! Tell me more.",
      "I see! What else is on your mind?",
      "Hmm, I'm still learning. Can you explain more?",
      "Thanks for sharing! Is there anything specific you'd like to know?"
    ];
    
    return defaults[Math.floor(Math.random() * defaults.length)];
  }
  
  getHelpMessage() {
    return `
🤖 **Rizz Bot Commands:**

**Economy:**
!daily - Claim daily reward
!work - Work and earn money
!balance - Check your balance
!leaderboard - Top earners

**Leveling:**
!rank - Check your rank
!level - Your current level

**Fun:**
!joke - Get a random joke
!chat <message> - Chat with AI

**Info:**
!help - Show this help
!invite - Invite bot
    `;
  }
}

const chatbot = new AIChatbot();

// ===== MESSAGE HANDLER =====

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  
  // Add XP for messages
  const xpResult = await leveling.addXP(message.author.id, message.guildId, 5);
  if (xpResult.leveledUp) {
    message.channel.send(`🎉 Congratulations ${message.author}! You reached level ${xpResult.newLevel}!`);
  }
  
  // Command handler
  if (message.content.startsWith('!')) {
    const [command, ...args] = message.content.slice(1).trim().split(/\s+/);
    await handleCommand(message, command, args);
  }
});

async function handleCommand(message, command, args) {
  const userId = message.author.id;
  const guildId = message.guildId;
  
  switch (command) {
    case 'daily': {
      const result = await economy.daily(userId, guildId);
      if (result.claimed) {
        message.channel.send(`✅ You claimed **$${result.amount}** daily reward!`);
      } else {
        const hours = Math.ceil(result.waitTime / (60 * 60 * 1000));
        message.channel.send(`⏰ Come back in ${hours} hour(s)!`);
      }
      break;
    }
    
    case 'work': {
      const result = await economy.work(userId, guildId);
      if (result.worked) {
        message.channel.send(`💼 You worked as a **${result.job}** and earned **$${result.pay}**!`);
      } else {
        const minutes = Math.ceil(result.waitTime / (60 * 1000));
        message.channel.send(`⏰ Work again in ${minutes} minute(s)!`);
      }
      break;
    }
    
    case 'balance': {
      const user = await economy.getUser(userId, guildId);
      const embed = new EmbedBuilder()
        .setTitle(`💰 ${message.author.username}'s Balance`)
        .addFields(
          { name: 'Wallet', value: `$${user.balance}`, inline: true },
          { name: 'Bank', value: `$${user.bank}`, inline: true },
          { name: 'Total', value: `$${user.balance + user.bank}`, inline: true }
        )
        .setColor('#10b981');
      message.channel.send({ embeds: [embed] });
      break;
    }
    
    case 'rank': {
      const rank = await leveling.getRank(userId, guildId);
      if (!rank) return;
      
      const embed = new EmbedBuilder()
        .setTitle(`📊 ${message.author.username}'s Rank`)
        .addFields(
          { name: 'Level', value: `${rank.level}`, inline: true },
          { name: 'XP', value: `${rank.xp}/${rank.xpNeeded}`, inline: true },
          { name: 'Rank', value: `#${rank.rank}`, inline: true },
          { name: 'Messages', value: `${rank.messagesSent}`, inline: true }
        )
        .setColor('#8b5cf6');
      message.channel.send({ embeds: [embed] });
      break;
    }
    
    case 'chat': {
      const userMessage = args.join(' ');
      if (!userMessage) {
        message.channel.send('Please provide a message to chat!');
        return;
      }
      
      const response = await chatbot.getResponse(userMessage, userId);
      message.channel.send(response);
      break;
    }
    
    case 'joke': {
      const response = await chatbot.getResponse('tell me a joke', userId);
      message.channel.send(response);
      break;
    }
    
    case 'help': {
      const help = chatbot.getHelpMessage();
      message.channel.send(help);
      break;
    }
    
    default:
      break;
  }
}

// ===== READY EVENT =====

client.once('ready', () => {
  console.log(`
╔════════════════════════════════════════════╗
║   🤖 Rizz Discord Bot - Enhanced           ║
║   Logged in as: ${client.user.tag}             ║
║                                            ║
║   Features:                                ║
║   - Economy System                         ║
║   - Leveling & XP                          ║
║   - AI Chatbot                             ║
║   - Mini-games                             ║
╚════════════════════════════════════════════╝
  `);
});

// Start bot
client.login(process.env.DISCORD_TOKEN || 'your-bot-token');

module.exports = { client, economy, leveling, chatbot };
