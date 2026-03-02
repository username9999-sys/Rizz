/**
 * Rizz Mobile App - Enhanced Features
 * Offline-first, Push Notifications, Biometric Auth, Dark Mode
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as LocalAuthentication from 'expo-local-authentication';
import * as Notifications from 'expo-notifications';
import { Ionicons } from '@expo/vector-icons';

// ===== OFFLINE-FIRST DATA SYNC =====

class OfflineFirstSync {
  constructor() {
    this.queue = [];
    this.isOnline = true;
    this.syncInProgress = false;
  }

  // Queue operation for later sync
  async queueOperation(operation) {
    const queuedOps = await AsyncStorage.getItem('queuedOperations');
    const ops = queuedOps ? JSON.parse(queuedOps) : [];
    ops.push({
      ...operation,
      queuedAt: Date.now(),
      id: Date.now() + Math.random()
    });
    await AsyncStorage.setItem('queuedOperations', JSON.stringify(ops));
  }

  // Sync queued operations when online
  async syncQueue() {
    if (this.syncInProgress) return;
    
    this.syncInProgress = true;
    const queuedOps = await AsyncStorage.getItem('queuedOperations');
    const ops = queuedOps ? JSON.parse(queuedOps) : [];

    for (const op of ops) {
      try {
        // In production: Send to actual API
        console.log('Syncing operation:', op);
        ops.shift();
      } catch (error) {
        console.error('Sync failed:', error);
        break;
      }
    }

    await AsyncStorage.setItem('queuedOperations', JSON.stringify(ops));
    this.syncInProgress = false;
  }

  // Check connectivity
  async checkConnectivity() {
    // In production: Use NetInfo
    this.isOnline = true;
    if (this.isOnline) {
      await this.syncQueue();
    }
    return this.isOnline;
  }
}

const offlineSync = new OfflineFirstSync();

// ===== PUSH NOTIFICATIONS =====

class NotificationManager {
  async requestPermissions() {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== 'granted') {
      return false;
    }
    
    const token = (await Notifications.getExpoPushTokenAsync()).data;
    return token;
  }

  async scheduleNotification(title, body, data, trigger) {
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        data,
        sound: true,
      },
      trigger,
    });
  }

  async scheduleTaskReminder(task, dueDate) {
    const trigger = new Date(dueDate);
    trigger.setMinutes(trigger.getMinutes() - 30); // Remind 30 min before
    
    await this.scheduleNotification(
      'Task Reminder',
      `Task "${task.title}" is due soon`,
      { taskId: task.id, type: 'task_reminder' },
      trigger
    );
  }

  async scheduleDealFollowUp(deal, followUpDate) {
    await this.scheduleNotification(
      'Deal Follow-up',
      `Follow up with ${deal.contactName} regarding ${deal.title}`,
      { dealId: deal.id, type: 'deal_followup' },
      new Date(followUpDate)
    );
  }
}

const notificationManager = new NotificationManager();

// ===== BIOMETRIC AUTHENTICATION =====

class BiometricAuth {
  async isAvailable() {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    const isEnrolled = await LocalAuthentication.isEnrolledAsync();
    return hasHardware && isEnrolled;
  }

  async authenticate(promptMessage = 'Authenticate to continue') {
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage,
      fallbackLabel: 'Use Passcode',
    });

    return result.success;
  }

  async secureSave(key, value) {
    // In production: Use Expo SecureStore
    const authenticated = await this.authenticate();
    if (authenticated) {
      await AsyncStorage.setItem(key, value);
      return true;
    }
    return false;
  }
}

const biometricAuth = new BiometricAuth();

// ===== DARK MODE MANAGER =====

class ThemeManager {
  constructor() {
    this.isDark = false;
    this.listeners = [];
  }

  async loadTheme() {
    const saved = await AsyncStorage.getItem('theme');
    this.isDark = saved === 'dark';
    this.notifyListeners();
  }

  toggleTheme() {
    this.isDark = !this.isDark;
    AsyncStorage.setItem('theme', this.isDark ? 'dark' : 'light');
    this.notifyListeners();
  }

  subscribe(listener) {
    this.listeners.push(listener);
  }

  notifyListeners() {
    this.listeners.forEach(listener => listener(this.isDark));
  }

  getColors() {
    return this.isDark ? {
      background: '#0f172a',
      card: '#1e293b',
      text: '#f1f5f9',
      textSecondary: '#94a3b8',
      primary: '#6366f1',
      border: '#334155'
    } : {
      background: '#f8fafc',
      card: '#ffffff',
      text: '#1e293b',
      textSecondary: '#64748b',
      primary: '#6366f1',
      border: '#e2e8f0'
    };
  }
}

const themeManager = new ThemeManager();

// ===== ENHANCED COMPONENTS =====

export function EnhancedTaskList() {
  const [tasks, setTasks] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const colors = themeManager.getColors();

  useEffect(() => {
    loadTasks();
    themeManager.subscribe(() => {
      // Re-render on theme change
    });
  }, []);

  async function loadTasks() {
    try {
      // Try to load from cache first (offline-first)
      const cached = await AsyncStorage.getItem('tasks');
      if (cached) {
        setTasks(JSON.parse(cached));
      }

      // Then sync with server
      const response = await fetch('http://localhost:5000/api/tasks');
      const freshTasks = await response.json();
      setTasks(freshTasks);
      await AsyncStorage.setItem('tasks', JSON.stringify(freshTasks));
    } catch (error) {
      console.error('Error loading tasks:', error);
      // Use cached data if available
    } finally {
      setLoading(false);
    }
  }

  async function refreshTasks() {
    setRefreshing(true);
    await loadTasks();
    setRefreshing(false);
  }

  async function completeTask(taskId) {
    try {
      // Optimistic update
      setTasks(prev => prev.map(t => 
        t.id === taskId ? { ...t, completed: true } : t
      ));

      // Queue for sync if offline
      await offlineSync.queueOperation({
        type: 'complete_task',
        taskId
      });

      // Try to sync immediately if online
      if (await offlineSync.checkConnectivity()) {
        await fetch(`http://localhost:5000/api/tasks/${taskId}/complete`, {
          method: 'POST'
        });
      }

      // Schedule celebration notification
      notificationManager.scheduleNotification(
        'Task Completed! 🎉',
        'Great job staying productive!',
        { type: 'celebration' },
        null
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to complete task');
    }
  }

  if (loading) {
    return (
      <View style={[styles.center, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <FlatList
        data={tasks}
        keyExtractor={item => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={refreshTasks} />
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.taskCard, { backgroundColor: colors.card }]}
            onPress={() => completeTask(item.id)}
          >
            <View style={styles.taskLeft}>
              <Ionicons
                name={item.completed ? 'checkbox' : 'square-outline'}
                size={24}
                color={colors.primary}
              />
              <Text style={[
                styles.taskTitle,
                { color: colors.text },
                item.completed && styles.taskCompleted
              ]}>
                {item.title}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={24} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

// ===== STYLES =====

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  taskCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 15,
    marginHorizontal: 15,
    marginVertical: 5,
    borderRadius: 10,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  taskLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  taskTitle: {
    fontSize: 16,
    marginLeft: 10,
  },
  taskCompleted: {
    textDecorationLine: 'line-through',
    opacity: 0.5,
  },
});

// ===== EXPORT MANAGERS =====

export {
  offlineSync,
  notificationManager,
  biometricAuth,
  themeManager,
  OfflineFirstSync,
  NotificationManager,
  BiometricAuth,
  ThemeManager
};
