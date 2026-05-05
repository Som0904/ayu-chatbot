'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { chatAPI } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import ChatArea from '@/components/ChatArea';
import ProfileModal from '@/components/ProfileModal';

type Session = {
  id: string;
  last_active: string;
  first_message?: string | null;
};

export default function ChatPage() {
  const router = useRouter();
  const { user, setUser, setSessions, setCurrentSessionId, setMessages, setNotifications, setProfile } = useStore();
  const [showProfile, setShowProfile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');

    if (!token || !userStr) {
      router.push('/login');
      return;
    }

    setUser(JSON.parse(userStr));
    loadData();
  }, []);

  useEffect(() => {
    if (!user) return;

    const notifInterval = setInterval(() => {
      loadNotifications();
    }, 10000);

    return () => clearInterval(notifInterval);
  }, [user]);

  const loadData = async () => {
    try {
      const [sessionsRes, profileRes, notifsRes] = await Promise.all([
        chatAPI.getSessions(),
        chatAPI.getProfile(),
        chatAPI.getNotifications(),
      ]);

      const sessionsData: Session[] = Array.isArray(sessionsRes.data)
        ? sessionsRes.data
        : sessionsRes.data?.sessions || [];

      setSessions(sessionsData);
      setProfile(profileRes.data);
      setNotifications(notifsRes.data);

      // Restore last session from localStorage or use first session
      const savedSessionId = localStorage.getItem('currentSessionId');
      if (savedSessionId && sessionsData.some((s) => s.id === savedSessionId)) {
        setCurrentSessionId(savedSessionId);
        loadSessionHistory(savedSessionId);
      } else if (sessionsData.length > 0) {
        const firstSession = sessionsData[0].id;
        setCurrentSessionId(firstSession);
        localStorage.setItem('currentSessionId', firstSession);
        loadSessionHistory(firstSession);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const loadSessionHistory = async (sessionId: string) => {
    try {
      const res = await chatAPI.getSessionHistory(sessionId);
      setMessages(res.data);
    } catch (error) {
      console.error('Failed to load session history:', error);
    }
  };

  const loadNotifications = async () => {
    try {
      const res = await chatAPI.getNotifications();
      setNotifications(res.data);
    } catch (error) {
      console.error('Failed to load notifications:', error);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onProfileClick={() => setShowProfile(true)}
        onSessionChange={loadSessionHistory}
      />
      <ChatArea sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} />}
    </div>
  );
}
