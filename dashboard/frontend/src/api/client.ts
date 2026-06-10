import axios from 'axios'
import useAuthStore from '../stores/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect to login
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient

// API Functions
export const authAPI = {
  login: (username: string, password: string) =>
    apiClient.post('/auth/login', { username, password }),
  
  register: (data: {
    username: string
    email: string
    password: string
    firstName?: string
    lastName?: string
  }) => apiClient.post('/users', data),
  
  getMe: () => apiClient.get('/me'),
  
  forgotPassword: (email: string) =>
    apiClient.post('/auth/forgot-password', { email }),
  
  resetPassword: (token: string, password: string) =>
    apiClient.post('/auth/reset-password', { token, password }),
  
  verifyEmail: (email: string, code: string) =>
    apiClient.post('/auth/verify-email', { email, code }),
  
  updateProfile: (data: any) =>
    apiClient.put('/me', data),
  
  changePassword: (oldPassword: string, newPassword: string) =>
    apiClient.post('/auth/change-password', { oldPassword, newPassword }),
}

export const suitesAPI = {
  getAll: (skip = 0, limit = 100) => 
    apiClient.get('/suites', { params: { skip, limit } }),
  
  getById: (id: number) => 
    apiClient.get(`/suites/${id}`),
  
  create: (data: any) => 
    apiClient.post('/suites', data),
  
  update: (id: number, data: any) => 
    apiClient.put(`/suites/${id}`, data),
  
  delete: (id: number) => 
    apiClient.delete(`/suites/${id}`),
}

export const casesAPI = {
  getAll: (suiteId?: number, skip = 0, limit = 100) => 
    apiClient.get('/cases', { params: { suite_id: suiteId, skip, limit } }),
  
  getById: (id: number) => 
    apiClient.get(`/cases/${id}`),
  
  create: (data: any) => 
    apiClient.post('/cases', data),
  
  update: (id: number, data: any) => 
    apiClient.put(`/cases/${id}`, data),
  
  delete: (id: number) => 
    apiClient.delete(`/cases/${id}`),
}

export const executionsAPI = {
  getAll: (suiteId?: number, status?: string, skip = 0, limit = 100) => 
    apiClient.get('/executions', { params: { suite_id: suiteId, status, skip, limit } }),
  
  getById: (id: number) => 
    apiClient.get(`/executions/${id}`),
  
  create: (data: any) => 
    apiClient.post('/executions', data),
  
  start: (id: number) => 
    apiClient.post(`/executions/${id}/start`),
  
  stop: (id: number) => 
    apiClient.post(`/executions/${id}/stop`),
}

export const dashboardAPI = {
  getStats: () =>
    apiClient.get('/dashboard/stats'),

  getTrends: (days = 30) =>
    apiClient.get('/dashboard/trends', { params: { days } }),

  getRecentExecutions: (limit = 10) =>
    apiClient.get('/dashboard/recent-executions', { params: { limit } }),
}

export const billingAPI = {
  getPlans: () =>
    apiClient.get('/billing/plans'),

  getSubscription: () =>
    apiClient.get('/billing/subscription'),

  subscribe: (planId: string, paymentMethodId?: string) =>
    apiClient.post('/billing/subscribe', { plan_id: planId, payment_method_id: paymentMethodId }),

  cancel: () =>
    apiClient.post('/billing/cancel'),

  upgrade: (planId: string) =>
    apiClient.post('/billing/upgrade', { plan_id: planId }),

  createCustomer: (email: string, name: string) =>
    apiClient.post('/billing/customer', { email, name }),

  getInvoices: () =>
    apiClient.get('/billing/invoices'),

  getPaymentMethods: () =>
    apiClient.get('/billing/payment-methods'),

  addPaymentMethod: (paymentMethodId: string) =>
    apiClient.post('/billing/payment-methods', { payment_method_id: paymentMethodId }),

  removePaymentMethod: (paymentMethodId: string) =>
    apiClient.delete(`/billing/payment-methods/${paymentMethodId}`),

  setDefaultPaymentMethod: (paymentMethodId: string) =>
    apiClient.put(`/billing/payment-methods/${paymentMethodId}/default`),
}

export const feedbackAPI = {
  submit: (data: {
    feedback_type: string
    category?: string
    title: string
    description: string
    priority?: string
    rating?: number
    tags?: string[]
    page_url?: string
    browser_info?: any
  }) => apiClient.post('/feedback', data),

  getAll: (params?: {
    page?: number
    page_size?: number
    status?: string
    feedback_type?: string
    priority?: string
  }) => apiClient.get('/feedback', { params }),

  getById: (id: number) =>
    apiClient.get(`/feedback/${id}`),

  update: (id: number, data: any) =>
    apiClient.patch(`/feedback/${id}`, data),

  delete: (id: number) =>
    apiClient.delete(`/feedback/${id}`),

  getStats: () =>
    apiClient.get('/feedback/stats'),
}

export const betaAPI = {
  signup: (data: {
    email: string
    company?: string
    use_case?: string
    team_size?: string
    source?: string
  }) => apiClient.post('/beta/signup', data),

  checkEmail: (email: string) =>
    apiClient.get(`/beta/check/${encodeURIComponent(email)}`),

  getAll: (params?: {
    page?: number
    page_size?: number
    status?: string
    source?: string
  }) => apiClient.get('/beta', { params }),

  getById: (id: number) =>
    apiClient.get(`/beta/${id}`),

  update: (id: number, data: any) =>
    apiClient.patch(`/beta/${id}`, data),

  approve: (id: number) =>
    apiClient.post(`/beta/${id}/approve`),

  reject: (id: number) =>
    apiClient.post(`/beta/${id}/reject`),

  delete: (id: number) =>
    apiClient.delete(`/beta/${id}`),

  getStats: () =>
    apiClient.get('/beta/stats'),
}

export const analyticsAPI = {
  getDashboard: () =>
    apiClient.get('/analytics/dashboard'),

  getUsers: (params?: {
    start_date?: string
    end_date?: string
  }) => apiClient.get('/analytics/users', { params }),

  getTests: (params?: {
    start_date?: string
    end_date?: string
  }) => apiClient.get('/analytics/tests', { params }),

  getRevenue: (params?: {
    start_date?: string
    end_date?: string
  }) => apiClient.get('/analytics/revenue', { params }),

  getFeatures: () =>
    apiClient.get('/analytics/features'),
}

export const onboardingAPI = {
  getState: () =>
    apiClient.get('/onboarding'),

  updateStep: (stepName: string, completed: boolean = true) =>
    apiClient.patch('/onboarding/step', { step_name: stepName, completed }),

  complete: () =>
    apiClient.post('/onboarding/complete'),

  skip: () =>
    apiClient.post('/onboarding/skip'),
}

export const waitlistAPI = {
  signup: (data: {
    email: string
    name: string
    role?: string
    company?: string
    use_case?: string
    source?: string
  }) => apiClient.post('/waitlist/signup', data),

  list: (params?: {
    page?: number
    page_size?: number
    status_filter?: string
    role_filter?: string
  }) => apiClient.get('/waitlist/list', { params }),

  getById: (id: number) =>
    apiClient.get(`/waitlist/${id}`),

  approve: (id: number) =>
    apiClient.post(`/waitlist/approve/${id}`),

  reject: (id: number) =>
    apiClient.post(`/waitlist/${id}/reject`),

  delete: (id: number) =>
    apiClient.delete(`/waitlist/${id}`),

  getStats: () =>
    apiClient.get('/waitlist/stats'),

  checkEmail: (email: string) =>
    apiClient.get(`/waitlist/check/${encodeURIComponent(email)}`),
}