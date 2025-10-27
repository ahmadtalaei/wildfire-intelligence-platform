import axios from 'axios';
import { User } from '../store/slices/authSlice';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080/api';

export interface LoginResponse {
  user: User;
  token: string;
}

export interface LoginCredentials {
  email?: string;
  username?: string;
  password: string;
}

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token expiry
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  // Login user
  login: async (username: string, password: string) => {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/login', {
        username,
        password,
      });
      return response;
    } catch (error) {
      // For demo purposes, return a mock successful login
      // Only allow chief@calfire.gov / admin for Fire Chief Dashboard
      if (username === 'chief@calfire.gov' && password === 'admin') {
        return {
          data: {
            user: {
              id: '1',
              username: 'chief',
              email: 'chief@calfire.gov',
              role: 'fire_chief',
              permissions: ['read_all', 'write_all', 'manage_incidents', 'manage_resources'],
              profile: {
                firstName: 'John',
                lastName: 'Williams',
                department: 'CAL FIRE',
                title: 'Fire Chief',
              },
            },
            token: 'mock-jwt-token-123',
          },
        };
      }
      throw error;
    }
  },

  // Logout user
  logout: async () => {
    try {
      const response = await apiClient.post('/auth/logout');
      localStorage.removeItem('auth_token');
      return response;
    } catch (error) {
      // Even if API call fails, clear local storage
      localStorage.removeItem('auth_token');
      return { data: { message: 'Logged out successfully' } };
    }
  },

  // Get current user
  getCurrentUser: async () => {
    try {
      const response = await apiClient.get<User>('/auth/me');
      return response;
    } catch (error) {
      // For demo purposes, return mock user data if token exists
      const token = localStorage.getItem('auth_token');
      if (token) {
        return {
          data: {
            id: '1',
            username: 'admin',
            email: 'admin@firestation.gov',
            role: 'fire_chief',
            permissions: ['read_all', 'write_all', 'manage_incidents', 'manage_resources'],
            profile: {
              firstName: 'John',
              lastName: 'Williams',
              department: 'Fire Department',
              title: 'Fire Chief',
            },
          },
        };
      }
      throw error;
    }
  },

  // Refresh token
  refreshToken: async () => {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/refresh');
      return response;
    } catch (error) {
      // For demo purposes, return the same token
      const token = localStorage.getItem('auth_token');
      if (token) {
        return {
          data: {
            user: {
              id: '1',
              username: 'admin',
              email: 'admin@firestation.gov',
              role: 'fire_chief',
              permissions: ['read_all', 'write_all', 'manage_incidents', 'manage_resources'],
              profile: {
                firstName: 'John',
                lastName: 'Williams',
                department: 'Fire Department',
                title: 'Fire Chief',
              },
            },
            token: token,
          },
        };
      }
      throw error;
    }
  },

  // Change password
  changePassword: async (currentPassword: string, newPassword: string) => {
    const response = await apiClient.post('/auth/change-password', {
      currentPassword,
      newPassword,
    });
    return response;
  },

  // Reset password request
  requestPasswordReset: async (email: string) => {
    const response = await apiClient.post('/auth/reset-password-request', {
      email,
    });
    return response;
  },

  // Reset password
  resetPassword: async (token: string, newPassword: string) => {
    const response = await apiClient.post('/auth/reset-password', {
      token,
      newPassword,
    });
    return response;
  },
};

export default apiClient;