const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('help')
    .setDescription('Get help with bot commands'),
  
  async execute(interaction) {
    const embed = new EmbedBuilder()
      .setColor('#6366f1')
      .setTitle('🤖 Rizz Bot - Help Menu')
      .setDescription('Here are all the available commands:')
      .addFields(
        {
          name: '📋 Task Management',
          value: '`/task add` - Add a new task\n`/task list` - View your tasks\n`/task complete` - Mark task done\n`/task delete` - Remove a task',
          inline: false,
        },
        {
          name: '📊 Statistics',
          value: '`/stats` - View your task statistics\n`/leaderboard` - Server leaderboard',
          inline: false,
        },
        {
          name: '⚙️ Settings',
          value: '`/settings` - Configure bot settings\n`/notifications` - Manage notifications',
          inline: false,
        },
        {
          name: '🎮 Fun',
          value: '`/roll` - Roll a dice\n`/coinflip` - Flip a coin\n`/quote` - Get inspirational quote',
          inline: false,
        },
        {
          name: '📖 Links',
          value: '[GitHub](https://github.com/username9999-sys/Rizz)\n[Documentation](https://rizz.dev/docs)',
          inline: false,
        }
      )
      .setFooter({ text: 'Made with ❤️ by username9999' })
      .setTimestamp();

    await interaction.reply({ embeds: [embed] });
  },
};
