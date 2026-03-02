import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Divider,
  Chip,
  Fab,
  Drawer,
  CssBaseline,
  AppBar,
  Toolbar,
} from '@mui/material';
import {
  Send as SendIcon,
  Menu as MenuIcon,
  SmartToy as BotIcon,
  People as PeopleIcon,
  AttachFile as AttachIcon,
  EmojiEmotions as EmojiIcon,
} from '@mui/icons-material';

const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || 'http://localhost:4000';

export default function ChatApp() {
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [aiMode, setAiMode] = useState(false);
  const [typingUsers, setTypingUsers] = useState([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const newSocket = io(SOCKET_URL);
    setSocket(newSocket);

    // Generate random user
    const user = {
      id: newSocket.id,
      username: `User_${Math.random().toString(36).substr(2, 6)}`,
    };
    setCurrentUser(user);

    newSocket.on('connect', () => {
      newSocket.emit('user_join', user);
    });

    newSocket.on('users_list', (userList) => {
      setUsers(userList.filter((u) => u.id !== user.id));
    });

    newSocket.on('receive_message', (message) => {
      setMessages((prev) => [...prev, message]);
    });

    newSocket.on('user_typing', ({ userId, username }) => {
      setTypingUsers((prev) => [...prev, username]);
    });

    newSocket.on('user_stop_typing', ({ userId }) => {
      setTypingUsers((prev) => prev.filter((_, i) => i !== prev.indexOf(userId)));
    });

    return () => newSocket.close();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = () => {
    if (!inputMessage.trim() || !socket) return;

    const message = {
      text: inputMessage,
      from: currentUser,
      to: aiMode ? 'ai' : null,
      room: 'general',
      type: aiMode ? 'ai_request' : 'text',
    };

    socket.emit('send_message', message);
    
    if (aiMode) {
      // Request AI response
      socket.emit('ai_chat', { message: inputMessage }, (response) => {
        if (response.response) {
          setMessages((prev) => [
            ...prev,
            {
              text: response.response,
              from: { username: '🤖 Rizz AI', id: 'ai' },
              type: 'ai_response',
              timestamp: new Date().toISOString(),
            },
          ]);
        }
      });
    }

    setInputMessage('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleTyping = () => {
    if (socket) {
      socket.emit('typing', { username: currentUser?.username, room: 'general' });
      setTimeout(() => {
        socket.emit('stop_typing', { room: 'general' });
      }, 1000);
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: '#0f172a' }}>
      <CssBaseline />
      
      {/* AppBar */}
      <AppBar position="fixed" sx={{ bgcolor: '#1e293b' }}>
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            onClick={() => setDrawerOpen(true)}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            💬 Rizz Chat
            {aiMode && <Chip label="AI Mode" size="small" sx={{ ml: 1, bgcolor: '#8b5cf6' }} />}
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Drawer */}
      <Drawer anchor="left" open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <Box sx={{ width: 280, bgcolor: '#1e293b', height: '100%' }}>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" color="white">
              👥 Online Users ({users.length})
            </Typography>
          </Box>
          <Divider />
          <List>
            {users.map((user) => (
              <ListItem key={user.id}>
                <ListItemAvatar>
                  <Avatar sx={{ bgcolor: '#10b981' }}>
                    {user.username[0]}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={user.username}
                  secondary="Online"
                  sx={{ color: 'white' }}
                />
              </ListItem>
            ))}
          </List>
          <Divider />
          <Box sx={{ p: 2 }}>
            <Chip
              label={aiMode ? '🤖 AI Mode ON' : '👤 Chat Mode'}
              onClick={() => setAiMode(!aiMode)}
              clickable
              color={aiMode ? 'secondary' : 'primary'}
              fullWidth
            />
          </Box>
        </Box>
      </Drawer>

      {/* Main Chat Area */}
      <Box sx={{ flexGrow: 1, ml: { xs: 0, sm: 0 }, mt: 8, mb: 8 }}>
        <Paper
          elevation={0}
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            bgcolor: '#0f172a',
          }}
        >
          {/* Messages */}
          <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
            <List>
              {messages.map((msg, index) => (
                <ListItem
                  key={msg.id || index}
                  alignItems="flex-start"
                  sx={{
                    justifyContent: msg.from?.id === currentUser?.id ? 'flex-end' : 'flex-start',
                  }}
                >
                  {msg.from?.id !== currentUser?.id && (
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: msg.from?.id === 'ai' ? '#8b5cf6' : '#10b981' }}>
                        {msg.from?.id === 'ai' ? '🤖' : msg.from?.username?.[0]}
                      </Avatar>
                    </ListItemAvatar>
                  )}
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle2" color="white">
                          {msg.from?.username}
                        </Typography>
                        <Typography variant="caption" color="gray">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Paper
                        elevation={0}
                        sx={{
                          mt: 0.5,
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: msg.from?.id === currentUser?.id ? '#6366f1' : '#1e293b',
                          color: 'white',
                          display: 'inline-block',
                        }}
                      >
                        {msg.text}
                      </Paper>
                    }
                  />
                </ListItem>
              ))}
              {typingUsers.length > 0 && (
                <ListItem>
                  <Typography variant="caption" color="gray" sx={{ fontStyle: 'italic' }}>
                    {typingUsers.join(', ')} typing...
                  </Typography>
                </ListItem>
              )}
              <div ref={messagesEndRef} />
            </List>
          </Box>

          {/* Input Area */}
          <Paper
            elevation={0}
            sx={{
              p: 2,
              bgcolor: '#1e293b',
              display: 'flex',
              gap: 1,
              alignItems: 'center',
            }}
          >
            <IconButton size="large">
              <AttachIcon sx={{ color: '#94a3b8' }} />
            </IconButton>
            <TextField
              fullWidth
              placeholder={aiMode ? 'Ask Rizz AI anything...' : 'Type a message...'}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              onInput={handleTyping}
              multiline
              maxRows={4}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: '#0f172a',
                  color: 'white',
                },
              }}
            />
            <IconButton size="large">
              <EmojiIcon sx={{ color: '#94a3b8' }} />
            </IconButton>
            <IconButton
              color="primary"
              onClick={sendMessage}
              disabled={!inputMessage.trim()}
              sx={{ bgcolor: '#10b981' }}
            >
              <SendIcon />
            </IconButton>
          </Paper>
        </Paper>
      </Box>
    </Box>
  );
}
