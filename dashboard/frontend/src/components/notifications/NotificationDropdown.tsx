import { useState, useEffect, useRef } from 'react'
import {
  IconButton,
  Badge,
  Menu,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Typography,
  Box,
  Button,
  Divider,
  CircularProgress,
  IconButton as MuiIconButton,
  Tooltip,
  Fade,
  Chip,
  Skeleton,
} from '@mui/material'
import {
  Notifications as NotificationsIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Folder as FolderIcon,
  Payment as PaymentIcon,
  SystemUpdate as SystemIcon,
  Delete as DeleteIcon,
  DoneAll as DoneAllIcon,
  NotificationsNone as EmptyIcon,
} from '@mui/icons-material'
import useNotificationsStore from '../../stores/notificationsStore'
import { Notification } from '../../api/notifications'
import { useQuery } from 'react-query'

// Mock data for development (remove when backend is ready)
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'test_completed',
    title: 'Test Suite Completed',
    message: 'Login Flow Test completed with 100% pass rate',
    data: { suite_id: 123, execution_id: 456 },
    read: false,
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 min ago
  },
  {
    id: '2',
    type: 'test_failed',
    title: 'Test Failed',
    message: 'Checkout Test Suite failed: 3/10 tests failed',
    data: { suite_id: 124, execution_id: 457 },
    read: false,
    created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 min ago
  },
  {
    id: '3',
    type: 'suite_created',
    title: 'New Test Suite',
    message: 'API Integration Tests suite has been created',
    data: { suite_id: 125 },
    read: true,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
  },
  {
    id: '4',
    type: 'billing',
    title: 'Payment Successful',
    message: 'Your Pro plan subscription has been renewed',
    data: { invoice_id: 'INV-001' },
    read: true,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
  },
  {
    id: '5',
    type: 'system',
    title: 'System Maintenance',
    message: 'Scheduled maintenance on March 15, 2026 at 02:00 UTC',
    data: {},
    read: false,
    created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
  },
]

// Notification type to icon mapping
const getNotificationIcon = (type: Notification['type']) => {
  const iconMap = {
    test_completed: <CheckCircleIcon sx={{ color: 'success.main' }} />,
    test_failed: <ErrorIcon sx={{ color: 'error.main' }} />,
    suite_created: <FolderIcon sx={{ color: 'primary.main' }} />,
    billing: <PaymentIcon sx={{ color: 'warning.main' }} />,
    system: <SystemIcon sx={{ color: 'info.main' }} />,
  }
  return iconMap[type] || <NotificationsIcon />
}

// Notification type to chip color mapping
const getNotificationChipColor = (type: Notification['type']): 'success' | 'error' | 'primary' | 'warning' | 'info' => {
  const colorMap = {
    test_completed: 'success',
    test_failed: 'error',
    suite_created: 'primary',
    billing: 'warning',
    system: 'info',
  } as const
  return colorMap[type] || 'info'
}

// Format relative time
const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`
  return date.toLocaleDateString()
}

export default function NotificationDropdown() {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [isUsingMock, setIsUsingMock] = useState(false)
  const open = Boolean(anchorEl)

  const {
    notifications,
    unreadCount,
    isLoading,
    error,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    addNotification,
  } = useNotificationsStore()

  // Fetch notifications on mount and when dropdown opens
  useEffect(() => {
    fetchNotifications().catch(() => {
      // If API fails, use mock data
      setIsUsingMock(true)
      mockNotifications.forEach(n => addNotification(n))
    })
  }, [fetchNotifications])

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleMarkAsRead = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      await markAsRead(id)
    } catch {
      // For mock mode, just update local state
      if (isUsingMock) {
        useNotificationsStore.setState((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
          unreadCount: Math.max(0, state.unreadCount - 1),
        }))
      }
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      await markAllAsRead()
    } catch {
      // For mock mode, just update local state
      if (isUsingMock) {
        useNotificationsStore.setState((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, read: true })),
          unreadCount: 0,
        }))
      }
    }
  }

  const handleDelete = async (id: string, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      await deleteNotification(id)
    } catch {
      // For mock mode, just update local state
      if (isUsingMock) {
        useNotificationsStore.setState((state) => {
          const notification = state.notifications.find((n) => n.id === id)
          const wasUnread = notification && !notification.read
          return {
            notifications: state.notifications.filter((n) => n.id !== id),
            unreadCount: wasUnread ? Math.max(0, state.unreadCount - 1) : state.unreadCount,
          }
        })
      }
    }
  }

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton
          color="inherit"
          onClick={handleClick}
          aria-label={`${unreadCount} unread notifications`}
          aria-controls={open ? 'notification-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
        >
          <Badge
            badgeContent={unreadCount}
            color="error"
            max={99}
            overlap="circular"
          >
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>

      <Menu
        id="notification-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        slotProps={{ transition: Fade, paper: {
          elevation: 3,
          sx: {
            width: { xs: '100vw', sm: 400 },
            maxHeight: { xs: '100vh', sm: 500 },
            display: 'flex',
            flexDirection: 'column',
            borderRadius: 2,
            mt: 1,
          },
        }, list: {
          sx: { p: 0 },
        } }}
        
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: 1,
            borderColor: 'divider',
            bgcolor: 'background.default',
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Notifications
          </Typography>
          {unreadCount > 0 && (
            <Button
              size="small"
              startIcon={<DoneAllIcon />}
              onClick={handleMarkAllAsRead}
              sx={{ textTransform: 'none' }}
            >
              Mark all read
            </Button>
          )}
          {isUsingMock && (
            <Chip
              label="Mock Data"
              size="small"
              color="warning"
              variant="outlined"
            />
          )}
        </Box>

        {/* Loading State */}
        {isLoading && (
          <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress size={32} />
          </Box>
        )}

        {/* Error State */}
        {error && !isUsingMock && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="error" variant="body2">
              {error}
            </Typography>
            <Button
              size="small"
              onClick={() => fetchNotifications()}
              sx={{ mt: 1 }}
            >
              Retry
            </Button>
          </Box>
        )}

        {/* Empty State */}
        {!isLoading && notifications.length === 0 && (
          <Box
            sx={{
              p: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <EmptyIcon sx={{ fontSize: 48, color: 'text.disabled' }} />
            <Typography variant="body1" color="text.secondary">
              No notifications yet
            </Typography>
          </Box>
        )}

        {/* Notifications List */}
        {!isLoading && notifications.length > 0 && (
          <List sx={{ p: 0, overflow: 'auto', flex: 1 }}>
            {notifications.map((notification, index) => (
              <Box key={notification.id}>
                <ListItem
                  sx={{
                    px: 2,
                    py: 1.5,
                    bgcolor: notification.read ? 'transparent' : 'action.hover',
                    transition: 'background-color 0.2s',
                    '&:hover': {
                      bgcolor: 'action.selected',
                    },
                  }}
                  secondaryAction={
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {!notification.read && (
                        <Tooltip title="Mark as read">
                          <MuiIconButton
                            size="small"
                            edge="end"
                            onClick={(e) => handleMarkAsRead(notification.id, e)}
                          >
                            <DoneAllIcon fontSize="small" />
                          </MuiIconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="Delete">
                        <MuiIconButton
                          size="small"
                          edge="end"
                          onClick={(e) => handleDelete(notification.id, e)}
                          sx={{ ml: notification.read ? 0 : 0.5 }}
                        >
                          <DeleteIcon fontSize="small" />
                        </MuiIconButton>
                      </Tooltip>
                    </Box>
                  }
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {getNotificationIcon(notification.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                        <Typography
                          variant="subtitle2"
                          sx={{
                            fontWeight: notification.read ? 400 : 600,
                            flex: 1,
                          }}
                        >
                          {notification.title}
                        </Typography>
                        <Chip
                          label={notification.type.replace('_', ' ')}
                          size="small"
                          color={getNotificationChipColor(notification.type)}
                          sx={{
                            textTransform: 'capitalize',
                            height: 20,
                            fontSize: '0.65rem',
                          }}
                        />
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            mb: 0.5,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                          }}
                        >
                          {notification.message}
                        </Typography>
                        <Typography variant="caption" color="text.disabled">
                          {formatRelativeTime(notification.created_at)}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
                {index < notifications.length - 1 && <Divider />}
              </Box>
            ))}
          </List>
        )}

        {/* Footer */}
        {notifications.length > 0 && (
          <Box
            sx={{
              p: 1.5,
              borderTop: 1,
              borderColor: 'divider',
              textAlign: 'center',
            }}
          >
            <Button
              size="small"
              onClick={handleClose}
              sx={{ textTransform: 'none' }}
            >
              Close
            </Button>
          </Box>
        )}
      </Menu>
    </>
  )
}
