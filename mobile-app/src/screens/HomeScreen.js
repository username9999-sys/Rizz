import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { Ionicons } from '@expo/vector-icons';
import { loadTasks } from '../store/slices/tasksSlice';

export default function HomeScreen({ navigation }) {
  const dispatch = useDispatch();
  const tasks = useSelector((state) => state.tasks.items);
  const [refreshing, setRefreshing] = React.useState(false);

  useEffect(() => {
    dispatch(loadTasks());
  }, []);

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    dispatch(loadTasks()).then(() => setRefreshing(false));
  }, []);

  const pendingTasks = tasks.filter((t) => t.status === 'pending');
  const completedTasks = tasks.filter((t) => t.status === 'completed');
  const highPriority = tasks.filter(
    (t) => t.priority === 'high' && t.status === 'pending'
  );

  const stats = [
    { label: 'Total', value: tasks.length, icon: 'list', color: '#6366f1' },
    { label: 'Pending', value: pendingTasks.length, icon: 'time', color: '#f59e0b' },
    { label: 'Completed', value: completedTasks.length, icon: 'checkmark-circle', color: '#10b981' },
    { label: 'Urgent', value: highPriority.length, icon: 'warning', color: '#ef4444' },
  ];

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.greeting}>Good Morning! 👋</Text>
        <Text style={styles.subtitle}>Let's get things done today</Text>
      </View>

      <View style={styles.statsContainer}>
        {stats.map((stat, index) => (
          <View key={index} style={[styles.statCard, { borderLeftColor: stat.color }]}>
            <Ionicons name={stat.icon} size={24} color={stat.color} />
            <Text style={styles.statValue}>{stat.value}</Text>
            <Text style={styles.statLabel}>{stat.label}</Text>
          </View>
        ))}
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
        </View>
        <View style={styles.quickActions}>
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: '#6366f1' }]}
            onPress={() => navigation.navigate('AddTask')}
          >
            <Ionicons name="add-circle" size={32} color="#fff" />
            <Text style={styles.actionText}>New Task</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: '#10b981' }]}
            onPress={() => navigation.navigate('Tasks')}
          >
            <Ionicons name="list" size={32} color="#fff" />
            <Text style={styles.actionText}>View All</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: '#f59e0b' }]}
            onPress={() => navigation.navigate('Calendar')}
          >
            <Ionicons name="calendar" size={32} color="#fff" />
            <Text style={styles.actionText}>Schedule</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: '#8b5cf6' }]}
            onPress={() => navigation.navigate('Statistics')}
          >
            <Ionicons name="stats-chart" size={32} color="#fff" />
            <Text style={styles.actionText}>Analytics</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Today's Tasks</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Tasks')}>
            <Text style={styles.seeAll}>See All</Text>
          </TouchableOpacity>
        </View>
        {pendingTasks.slice(0, 5).map((task) => (
          <TouchableOpacity
            key={task.id}
            style={styles.taskCard}
            onPress={() => navigation.navigate('TaskDetail', { taskId: task.id })}
          >
            <View style={styles.taskLeft}>
              <Ionicons
                name={
                  task.priority === 'high'
                    ? 'radio-button-on'
                    : task.priority === 'medium'
                    ? 'ellipse'
                    : 'ellipse-outline'
                }
                size={24}
                color={
                  task.priority === 'high'
                    ? '#ef4444'
                    : task.priority === 'medium'
                    ? '#f59e0b'
                    : '#10b981'
                }
              />
              <Text style={styles.taskTitle} numberOfLines={1}>
                {task.title}
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={24} color="#94a3b8" />
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  header: {
    padding: 20,
    paddingTop: 60,
  },
  greeting: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#f1f5f9',
  },
  subtitle: {
    fontSize: 16,
    color: '#94a3b8',
    marginTop: 5,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 15,
    marginBottom: 20,
  },
  statCard: {
    backgroundColor: '#1e293b',
    borderRadius: 15,
    padding: 15,
    alignItems: 'center',
    borderLeftWidth: 4,
    minWidth: 80,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#f1f5f9',
    marginTop: 5,
  },
  statLabel: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 3,
  },
  section: {
    marginTop: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#f1f5f9',
  },
  seeAll: {
    color: '#6366f1',
    fontSize: 14,
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 15,
  },
  actionButton: {
    width: 80,
    height: 80,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionText: {
    color: '#fff',
    fontSize: 12,
    marginTop: 5,
    fontWeight: '600',
  },
  taskCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    marginHorizontal: 15,
    padding: 15,
    borderRadius: 12,
    marginBottom: 10,
  },
  taskLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  taskTitle: {
    fontSize: 16,
    color: '#f1f5f9',
    marginLeft: 10,
    flex: 1,
  },
});
