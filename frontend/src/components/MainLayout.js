import React, { useState, useEffect } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Button,
  Switch,
  FormControlLabel,
  Divider,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Chat as ChatIcon,
  Map as MapIcon,
  Upload as UploadIcon,
  Logout as LogoutIcon,
  Layers as LayersIcon,
  Download as DownloadIcon,
  DeveloperMode as DeveloperModeIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';

import ChatPanel from './ChatPanel';
import MapView from './MapView';
import UploadPanel from './UploadPanel';
import LayersPanel from './LayersPanel';
import TileDownloadPanel from './TileDownloadPanel';

const drawerWidth = 240;

function MainLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [activeView, setActiveView] = useState('map');
  const [developerMode, setDeveloperMode] = useState(() => {
    // Load developer mode from localStorage
    const saved = localStorage.getItem('developerMode');
    return saved === 'true';
  });
  const { user, logout } = useAuth();

  // Save developer mode to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('developerMode', developerMode.toString());
  }, [developerMode]);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleLogout = () => {
    logout();
  };

  const handleDeveloperModeToggle = () => {
    setDeveloperMode(!developerMode);
  };

  const menuItems = [
    { text: 'Map View', icon: <MapIcon />, value: 'map' },
    { text: 'Chat', icon: <ChatIcon />, value: 'chat' },
    { text: 'Layers', icon: <LayersIcon />, value: 'layers' },
    { text: 'Upload Data', icon: <UploadIcon />, value: 'upload' },
  ];

  // Add developer menu items if developer mode is enabled
  if (developerMode) {
    menuItems.push({ text: 'Download Tiles', icon: <DownloadIcon />, value: 'download' });
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          LLM Planner
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.value} disablePadding>
            <ListItemButton
              selected={activeView === item.value}
              onClick={() => setActiveView(item.value)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider sx={{ my: 2 }} />
      <Box sx={{ px: 2 }}>
        <FormControlLabel
          control={
            <Switch
              checked={developerMode}
              onChange={handleDeveloperModeToggle}
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DeveloperModeIcon fontSize="small" />
              <Typography variant="body2">Dev Mode</Typography>
            </Box>
          }
        />
      </Box>
    </div>
  );

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Disaster Relief Planning System
          </Typography>
          <Typography variant="body1" sx={{ mr: 2 }}>
            {user?.username}
          </Typography>
          <Button color="inherit" onClick={handleLogout} startIcon={<LogoutIcon />}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 0,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          height: '100vh',
          overflow: 'hidden',
        }}
      >
        <Toolbar />
        <Box sx={{ display: activeView === 'map' ? 'block' : 'none', height: '100%' }}>
          <MapView 
            onNavigateToDownload={() => setActiveView('download')} 
            developerMode={developerMode}
          />
        </Box>
        <Box sx={{ display: activeView === 'chat' ? 'block' : 'none', height: '100%' }}>
          <ChatPanel />
        </Box>
        <Box sx={{ display: activeView === 'layers' ? 'block' : 'none', height: '100%' }}>
          <LayersPanel />
        </Box>
        <Box sx={{ display: activeView === 'upload' ? 'block' : 'none', height: '100%' }}>
          <UploadPanel />
        </Box>
        {developerMode && (
          <Box sx={{ display: activeView === 'download' ? 'block' : 'none', height: '100%' }}>
            <TileDownloadPanel />
          </Box>
        )}
      </Box>
    </Box>
  );
}

export default MainLayout;
