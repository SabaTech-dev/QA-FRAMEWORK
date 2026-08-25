import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react'
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import {
  lightTheme,
  darkTheme,
  ThemeMode,
  getSystemTheme,
  getStoredTheme,
  setStoredTheme,
} from './theme'

interface ThemeContextType {
  mode: ThemeMode
  actualMode: 'light' | 'dark'
  toggleTheme: () => void
  setMode: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export const useThemeContext = (): ThemeContextType => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useThemeContext must be used within a ThemeProvider')
  }
  return context
}

interface ThemeProviderProps {
  children: React.ReactNode
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // Initialize from localStorage or default to system
  const [mode, setModeState] = useState<ThemeMode>(() => {
    return getStoredTheme()
  })

  // Track actual rendered mode (resolves 'system' to 'light' or 'dark')
  const [actualMode, setActualMode] = useState<'light' | 'dark'>(() => {
    const stored = getStoredTheme()
    return stored === 'system' ? getSystemTheme() : stored
  })

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = (e: MediaQueryListEvent) => {
      if (mode === 'system') {
        setActualMode(e.matches ? 'dark' : 'light')
      }
    }

    // Set initial value
    if (mode === 'system') {
      setActualMode(mediaQuery.matches ? 'dark' : 'light')
    }

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange)
    
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [mode])

  // Update actual mode when mode changes
  useEffect(() => {
    if (mode === 'system') {
      setActualMode(getSystemTheme())
    } else {
      setActualMode(mode)
    }
  }, [mode])

  // Set mode and persist
  const setMode = useCallback((newMode: ThemeMode) => {
    setModeState(newMode)
    setStoredTheme(newMode)
  }, [])

  // Toggle between light, dark, and system
  const toggleTheme = useCallback(() => {
    if (mode === 'light') {
      setMode('dark')
    } else if (mode === 'dark') {
      setMode('system')
    } else {
      setMode('light')
    }
  }, [mode, setMode])

  // Memoize theme object
  const theme = useMemo(() => {
    return actualMode === 'dark' ? darkTheme : lightTheme
  }, [actualMode])

  // Context value
  const contextValue = useMemo(
    () => ({
      mode,
      actualMode,
      toggleTheme,
      setMode,
    }),
    [mode, actualMode, toggleTheme, setMode]
  )

  return (
    <ThemeContext.Provider value={contextValue}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  )
}

export default ThemeProvider
