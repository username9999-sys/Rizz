import { configureStore } from '@reduxjs/toolkit';
import tasksReducer from './slices/tasksSlice';
import userReducer from './slices/userSlice';
import settingsReducer from './slices/settingsSlice';

export const store = configureStore({
  reducer: {
    tasks: tasksReducer,
    user: userReducer,
    settings: settingsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export default store;
