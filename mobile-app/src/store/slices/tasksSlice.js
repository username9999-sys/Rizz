import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const loadTasks = createAsyncThunk(
  'tasks/loadTasks',
  async () => {
    const tasks = await AsyncStorage.getItem('tasks');
    return tasks ? JSON.parse(tasks) : [];
  }
);

export const saveTasks = createAsyncThunk(
  'tasks/saveTasks',
  async (tasks) => {
    await AsyncStorage.setItem('tasks', JSON.stringify(tasks));
    return tasks;
  }
);

const tasksSlice = createSlice({
  name: 'tasks',
  initialState: {
    items: [],
    loading: false,
    error: null,
    filters: {
      status: 'all',
      priority: 'all',
      category: 'all',
      search: '',
    },
  },
  reducers: {
    addTask: (state, action) => {
      state.items.push({
        id: Date.now().toString(),
        ...action.payload,
        createdAt: new Date().toISOString(),
        status: 'pending',
      });
    },
    updateTask: (state, action) => {
      const index = state.items.findIndex(t => t.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = { ...state.items[index], ...action.payload };
      }
    },
    deleteTask: (state, action) => {
      state.items = state.items.filter(t => t.id !== action.payload);
    },
    completeTask: (state, action) => {
      const index = state.items.findIndex(t => t.id === action.payload);
      if (index !== -1) {
        state.items[index].status = 'completed';
        state.items[index].completedAt = new Date().toISOString();
      }
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = {
        status: 'all',
        priority: 'all',
        category: 'all',
        search: '',
      };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadTasks.pending, (state) => {
        state.loading = true;
      })
      .addCase(loadTasks.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      .addCase(loadTasks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      .addCase(saveTasks.fulfilled, (state, action) => {
        state.items = action.payload;
      });
  },
});

export const {
  addTask,
  updateTask,
  deleteTask,
  completeTask,
  setFilters,
  clearFilters,
} = tasksSlice.actions;

export default tasksSlice.reducer;
