import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  username: string
  email: string
  full_name?: string | null
  subscription_plan?: string | null
  subscription_status?: string | null
  is_active: boolean
  is_superuser: boolean
  onboarding_completed?: boolean
  onboarding_state?: {
    current_step: number
    steps: Record<string, boolean>
  }
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  needsOnboarding: boolean
  login: (token: string, user: User) => void
  logout: () => void
  updateUser: (user: User) => void
  setToken: (token: string) => void
  setNeedsOnboarding: (value: boolean) => void
}

const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      needsOnboarding: false,
      login: (token, user) => set({
        token,
        user,
        isAuthenticated: true,
        needsOnboarding: !user.onboarding_completed,
      }),
      logout: () => set({ token: null, user: null, isAuthenticated: false, needsOnboarding: false }),
      updateUser: (user) => set({ user, needsOnboarding: !user.onboarding_completed }),
      setToken: (token) => set({ token }),
      setNeedsOnboarding: (value) => set({ needsOnboarding: value }),
    }),
    {
      name: 'auth-storage',
    }
  )
)

export default useAuthStore