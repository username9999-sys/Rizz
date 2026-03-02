const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const Task = require('../models/Task');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('task')
    .setDescription('Manage your tasks')
    .addSubcommand((subcommand) =>
      subcommand
        .setName('add')
        .setDescription('Add a new task')
        .addStringOption((option) =>
          option.setName('title').setDescription('Task title').setRequired(true)
        )
        .addStringOption((option) =>
          option.setName('description').setDescription('Task description')
        )
        .addStringOption((option) =>
          option.setName('priority')
            .setDescription('Task priority')
            .setChoices(
              { name: 'Low', value: 'low' },
              { name: 'Medium', value: 'medium' },
              { name: 'High', value: 'high' }
            )
        )
        .addStringOption((option) =>
          option.setName('due_date').setDescription('Due date (YYYY-MM-DD)')
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('list')
        .setDescription('List your tasks')
        .addStringOption((option) =>
          option.setName('filter')
            .setDescription('Filter tasks')
            .setChoices(
              { name: 'All', value: 'all' },
              { name: 'Pending', value: 'pending' },
              { name: 'Completed', value: 'completed' }
            )
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('complete')
        .setDescription('Mark a task as completed')
        .addStringOption((option) =>
          option.setName('id').setDescription('Task ID').setRequired(true)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('delete')
        .setDescription('Delete a task')
        .addStringOption((option) =>
          option.setName('id').setDescription('Task ID').setRequired(true)
        )
    ),

  async execute(interaction) {
    const subcommand = interaction.options.getSubcommand();
    const userId = interaction.user.id;

    try {
      switch (subcommand) {
        case 'add': {
          const title = interaction.options.getString('title');
          const description = interaction.options.getString('description') || '';
          const priority = interaction.options.getString('priority') || 'medium';
          const dueDate = interaction.options.getString('due_date');

          const task = await Task.create({
            userId,
            title,
            description,
            priority,
            dueDate,
          });

          const embed = new EmbedBuilder()
            .setColor('#10b981')
            .setTitle('✅ Task Created')
            .addFields(
              { name: 'Title', value: title, inline: true },
              { name: 'Priority', value: priority, inline: true },
              { name: 'ID', value: task._id.toString(), inline: true }
            )
            .setTimestamp();

          await interaction.reply({ embeds: [embed] });
          break;
        }

        case 'list': {
          const filter = interaction.options.getString('filter') || 'all';
          const tasks = await Task.findByUser(userId, filter);

          if (tasks.length === 0) {
            await interaction.reply({
              content: '📭 No tasks found!',
              ephemeral: true,
            });
            return;
          }

          const embed = new EmbedBuilder()
            .setColor('#6366f1')
            .setTitle(`📋 Your Tasks (${tasks.length})`)
            .setDescription(
              tasks
                .slice(0, 10)
                .map(
                  (t) =>
                    `**${t.priority === 'high' ? '🔴' : t.priority === 'medium' ? '🟡' : '🟢'}** ${t.title}`
                )
                .join('\n')
            )
            .setFooter({ text: `Showing ${Math.min(tasks.length, 10)} of ${tasks.length} tasks` });

          await interaction.reply({ embeds: [embed] });
          break;
        }

        case 'complete': {
          const taskId = interaction.options.getString('id');
          const task = await Task.findById(taskId);

          if (!task || task.userId !== userId) {
            await interaction.reply({
              content: '❌ Task not found!',
              ephemeral: true,
            });
            return;
          }

          await Task.complete(taskId);
          await interaction.reply({ content: '✅ Task completed!' });
          break;
        }

        case 'delete': {
          const taskId = interaction.options.getString('id');
          const task = await Task.findById(taskId);

          if (!task || task.userId !== userId) {
            await interaction.reply({
              content: '❌ Task not found!',
              ephemeral: true,
            });
            return;
          }

          await Task.delete(taskId);
          await interaction.reply({ content: '🗑️ Task deleted!' });
          break;
        }
      }
    } catch (error) {
      logger.error('Task command error:', error);
      await interaction.reply({
        content: '❌ An error occurred!',
        ephemeral: true,
      });
    }
  },
};
