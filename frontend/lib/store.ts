import { create } from 'zustand';

interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
}

interface Message {
  role: 'user' | 'bot';
  text: string;
  created_at: string;
}

interface Session {
  id: string;
  last_active: string;
  first_message?: string | null;
}

interface Notification {
  id: string;
  message: string;
  created_at: string;
  type?: string;
}

interface Store {
  user: User | null;
  token: string | null;
  sessions: Session[];
  currentSessionId: string;
  messages: Message[];
  notifications: Notification[];
  profile: Record<string, any>;
  isLoading: boolean;
  
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setSessions: (sessions: Session[]) => void;
  setCurrentSessionId: (id: string) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setNotifications: (notifications: Notification[]) => void;
  setProfile: (profile: Record<string, any>) => void;
  setIsLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useStore = create<Store>((set) => ({
  user: null,
  token: null,
  sessions: [],
  currentSessionId: 'default',
  messages: [],
  notifications: [],
  profile: {},
  isLoading: false,

  setUser: (user) => set({ user }),
  setToken: (token) => set({ token }),
  setSessions: (sessions) => set({ sessions }),
  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setNotifications: (notifications) => set({ notifications }),
  setProfile: (profile) => set({ profile }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ user: null, token: null, sessions: [], messages: [], notifications: [], profile: {} });
  },
}));
