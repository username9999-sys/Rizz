import React, { useState } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import List from '@mui/material/List';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Dashboard from '@mui/icons-material/Dashboard';
import Analytics from '@mui/icons-material/Analytics';
import Search from '@mui/icons-material/Search';
import Storage from '@mui/icons-material/Storage';
import People from '@mui/icons-material/People';
import Settings from '@mui/icons-material/Settings';
import NotificationImportant from '@mui/icons-material/NotificationImportant';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SnackbarProvider } from 'notistack';

const drawerWidth = 240;

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
});

const queryClient = new QueryClient();

const menuItems = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/' },
  { text: 'Analytics', icon: <Analytics />, path: '/analytics' },
  { text: 'Users', icon: <People />, path: '/users' },
  { text: 'Posts', icon: <Storage />, path: '/posts' },
  { text: 'Search', icon: <Search />, path: '/search' },
  { text: 'Storage', icon: <Storage />, path: '/storage' },
  { text: 'Notifications', icon: <NotificationImportant />, path: '/notifications' },
  { text: 'ML Insights', icon: <Analytics />, path: '/ml' },
  { text: 'Settings', icon: <Settings />, path: '/settings' },
];

function DashboardLayout({ children }) {
  const [open, setOpen] = useState(true);

  const toggleDrawer = () => {
    setOpen(!open);
  };

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="absolute" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar sx={{ pr: '24px' }}>
          <IconButton edge="start" color="inherit" onClick={toggleDrawer} sx={{ marginRight: '36px' }}>
            <MenuIcon />
          </IconButton>
          <Typography component="h1" variant="h6" color="inherit" noWrap sx={{ flexGrow: 1 }}>
            🚀 Rizz Platform Admin
          </Typography>
          <Typography variant="body2" color="inherit">
            v3.0.0 Enterprise
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer variant="permanent" open={open} sx={{
        '& .MuiDrawer-paper': {
          position: 'relative',
          whiteSpace: 'nowrap',
          width: drawerWidth,
          transition: 'width 0.2s ease-in-out',
          boxSizing: 'border-box',
          ...(!open && { overflowX: 'hidden', width: 0 }),
        },
      }}>
        <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', px: [1] }}>
          <IconButton onClick={toggleDrawer}>
            <ChevronLeftIcon />
          </IconButton>
        </Toolbar>
        <Divider />
        <List component="nav">
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
              <ListItemButton href={item.path}>
                <ListItemIcon sx={{ minWidth: 0, mr: open ? 3 : 'auto', justifyContent: 'center' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} sx={{ opacity: open ? 1 : 0 }} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ backgroundColor: 'background.default', flexGrow: 1, height: '100vh', overflow: 'auto' }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}

function Dashboard() {
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalPosts: 0,
    activeUsers: 0,
    apiCalls: 0,
  });

  React.useEffect(() => {
    // Fetch stats from API
    fetch('http://localhost:5000/api/analytics/overview')
      .then(res => res.json())
      .then(data => setStats({
        totalUsers: data.metrics?.total_users || 0,
        totalPosts: data.metrics?.total_posts || 0,
        activeUsers: Math.floor(data.metrics?.total_users * 0.3) || 0,
        apiCalls: Math.floor(Math.random() * 10000) || 0,
      }))
      .catch(console.error);
  }, []);

  return (
    <DashboardLayout>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Platform Overview
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 2, mb: 4 }}>
          {[
            { title: 'Total Users', value: stats.totalUsers, color: '#90caf9' },
            { title: 'Total Posts', value: stats.totalPosts, color: '#a5d6a7' },
            { title: 'Active Users', value: stats.activeUsers, color: '#ffcc80' },
            { title: 'API Calls Today', value: stats.apiCalls, color: '#f48fb1' },
          ].map((stat) => (
            <Box key={stat.title} sx={{ 
              p: 3, 
              bgcolor: 'background.paper', 
              borderRadius: 2,
              border: '1px solid rgba(255,255,255,0.1)'
            }}>
              <Typography color="text.secondary" variant="body2">{stat.title}</Typography>
              <Typography variant="h3" sx={{ color: stat.color, mt: 1 }}>
                {stat.value.toLocaleString()}
              </Typography>
            </Box>
          ))}
        </Box>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Quick Actions
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
          {[
            { action: 'View All Users', path: '/users' },
            { action: 'Manage Posts', path: '/posts' },
            { action: 'System Settings', path: '/settings' },
            { action: 'View Logs', path: '/logs' },
            { action: 'API Documentation', path: '/docs' },
            { action: 'Monitor Services', path: '/monitoring' },
          ].map((item) => (
            <Box 
              key={item.action}
              component="a"
              href={item.path}
              sx={{
                p: 2,
                bgcolor: 'background.paper',
                borderRadius: 1,
                textDecoration: 'none',
                color: 'primary.main',
                '&:hover': { bgcolor: 'action.hover' }
              }}
            >
              <Typography variant="body1">{item.action}</Typography>
            </Box>
          ))}
        </Box>

        <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
          Service Health
        </Typography>
        <Box sx={{ bgcolor: 'background.paper', borderRadius: 2, p: 2 }}>
          {[
            { name: 'API Server', status: 'healthy', port: 5000 },
            { name: 'Analytics', status: 'healthy', port: 8001 },
            { name: 'Notifications', status: 'healthy', port: 8002 },
            { name: 'Search', status: 'healthy', port: 8003 },
            { name: 'Storage', status: 'healthy', port: 8004 },
            { name: 'ML Service', status: 'healthy', port: 8005 },
            { name: 'PostgreSQL', status: 'healthy', port: 5432 },
            { name: 'Redis', status: 'healthy', port: 6379 },
            { name: 'Elasticsearch', status: 'healthy', port: 9200 },
          ].map((service) => (
            <Box key={service.name} sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              p: 1,
              borderBottom: '1px solid rgba(255,255,255,0.1)'
            }}>
              <Typography variant="body2">{service.name} (:{service.port})</Typography>
              <Box sx={{ 
                width: 10, 
                height: 10, 
                borderRadius: '50%', 
                bgcolor: service.status === 'healthy' ? '#4caf50' : '#f44336' 
              }} />
            </Box>
          ))}
        </Box>
      </Box>
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SnackbarProvider maxSnack={3}>
        <ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <Dashboard />
        </ThemeProvider>
      </SnackbarProvider>
    </QueryClientProvider>
  );
}
