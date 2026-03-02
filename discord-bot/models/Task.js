const mongoose = require('mongoose');

const taskSchema = new mongoose.Schema({
  userId: { type: String, required: true },
  guildId: String,
  title: { type: String, required: true },
  description: String,
  priority: { 
    type: String, 
    enum: ['low', 'medium', 'high'], 
    default: 'medium' 
  },
  status: { 
    type: String, 
    enum: ['pending', 'completed'], 
    default: 'pending' 
  },
  dueDate: String,
  completedAt: Date,
  createdAt: { type: Date, default: Date.now },
  updatedAt: Date,
});

taskSchema.pre('save', function(next) {
  this.updatedAt = Date.now();
  next();
});

taskSchema.statics.findByUser = function(userId, filter = 'all') {
  const query = { userId };
  if (filter !== 'all') {
    query.status = filter;
  }
  return this.find(query).sort({ createdAt: -1 });
};

taskSchema.statics.complete = function(id) {
  return this.findByIdAndUpdate(
    id,
    { 
      status: 'completed',
      completedAt: Date.now()
    }
  );
};

module.exports = mongoose.model('Task', taskSchema);
