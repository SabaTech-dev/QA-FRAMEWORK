import { ReactNode, useState } from 'react'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Folder as FolderIcon,
  BugReport as BugReportIcon,
  PlayArrow as PlayArrowIcon,
  Payment as PaymentIcon,
  AutoFixHigh as AutoFixHighIcon,
  Extension as ExtensionIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  Help as HelpIcon,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../stores/authStore'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import KeyboardShortcutsDialog from './common/KeyboardShortcutsDialog'
import DynamicBreadcrumb from './common/Breadcrumb'
import NotificationDropdown from './notifications/NotificationDropdown'

const drawerWidth = 240

interface LayoutProps {
  children: ReactNode
  sidebarOpen: boolean
  onSidebarToggle: () => void
}

export default function Layout({ children, sidebarOpen, onSidebarToggle }: LayoutProps) {
  const navigate = useNavigate()
  const { logout, user } = useAuthStore()
  const [isHelpOpen, setIsHelpOpen] = useState(false)

  const toggleHelp = () => setIsHelpOpen(!isHelpOpen)

  // Register keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: '/',
        description: 'Focus search',
        action: () => {
          // Focus search input if exists
          const searchInput = document.querySelector('input[type="text"]') as HTMLInputElement;
          if (searchInput) searchInput.focus();
        },
      },
      {
        key: 'n',
        description: 'New test',
        action: () => navigate('/suites'),
      },
      {
        key: 'h',
        description: 'Go home',
        action: () => navigate('/'),
      },
      {
        key: '?',
        description: 'Show shortcuts',
        action: toggleHelp,
      },
    ],
  });

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Test Suites', icon: <FolderIcon />, path: '/suites' },
    { text: 'Test Cases', icon: <BugReportIcon />, path: '/cases' },
    { text: 'Executions', icon: <PlayArrowIcon />, path: '/executions' },
    { text: 'Integrations', icon: <ExtensionIcon />, path: '/integrations' },
    { text: 'Self-Healing', icon: <AutoFixHighIcon />, path: '/self-healing' },
    { text: 'Billing', icon: <PaymentIcon />, path: '/billing' },
  ]

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: sidebarOpen ? `calc(100% - ${drawerWidth}px)` : '100%',
          ml: sidebarOpen ? `${drawerWidth}px` : 0,
          transition: 'all 0.3s',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={onSidebarToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            QA Framework Dashboard
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.username}
          </Typography>
          <NotificationDropdown />
          <IconButton
            color="inherit"
            onClick={toggleHelp}
            title="Keyboard Shortcuts (?)"
            sx={{ mr: 1 }}
          >
            <HelpIcon />
          </IconButton>
          <IconButton color="inherit" onClick={handleLogout} title="Logout">
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="persistent"
        anchor="left"
        open={sidebarOpen}
      >
        <Toolbar />
        <Divider />
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton onClick={() => navigate(item.path)}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Divider />
        <List>
          <ListItem disablePadding>
            <ListItemButton onClick={() => navigate('/settings')}>
              <ListItemIcon>
                <SettingsIcon />
              </ListItemIcon>
              <ListItemText primary="Settings" />
            </ListItemButton>
          </ListItem>
        </List>
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
          width: sidebarOpen ? `calc(100% - ${drawerWidth}px)` : '100%',
          ml: sidebarOpen ? `${drawerWidth}px` : 0,
          transition: 'all 0.3s',
        }}
      >
        <Toolbar />
        <DynamicBreadcrumb />
        {children}
      </Box>

      {/* Keyboard Shortcuts Dialog */}
      <KeyboardShortcutsDialog
        open={isHelpOpen}
        onClose={toggleHelp}
      />
    </Box>
  )
}
