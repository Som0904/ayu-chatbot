'use client';

import { useStore } from '@/lib/store';
import { chatAPI } from '@/lib/api';
import { formatDate, truncate } from '@/lib/utils';
import { Plus, MessageSquare, Bell, User, LogOut, Menu, X, Trash2 } from 'lucide-react';
import { useState } from 'react';
import Image from 'next/image';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  onProfileClick: () => void;
  onSessionChange: (sessionId: string) => void;
}

export default function Sidebar({ isOpen, onToggle, onProfileClick, onSessionChange }: SidebarProps) {
  const { user, sessions, currentSessionId, notifications, setCurrentSessionId, setSessions, setMessages, setNotifications, logout } = useStore();
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const handleNewChat = () => {
    // Generate unique session ID with timestamp and random string to prevent collisions
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newSession = {
      id: newSessionId,
      last_active: new Date().toISOString(),
      first_message: null
    };
    setSessions([newSession, ...sessions]);
    setCurrentSessionId(newSessionId);
    setMessages([]);
    
    // Persist to localStorage
    localStorage.setItem('currentSessionId', newSessionId);
  };

  const handleSessionClick = async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    localStorage.setItem('currentSessionId', sessionId);
    onSessionChange(sessionId);
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (deleteConfirm === sessionId) {
      try {
        await chatAPI.deleteSession(sessionId);
        const updatedSessions = sessions.filter(s => s.id !== sessionId);
        setSessions(updatedSessions);
        if (currentSessionId === sessionId) {
          if (updatedSessions.length > 0) {
            handleSessionClick(updatedSessions[0].id);
          } else {
            handleNewChat();
          }
        }
        setDeleteConfirm(null);
      } catch (error) {
        console.error('Failed to delete session:', error);
      }
    } else {
      setDeleteConfirm(sessionId);
      setTimeout(() => setDeleteConfirm(null), 3000);
    }
  };

  const handleNotificationClick = async (notif: any) => {
    try {
      await chatAPI.markNotificationRead(notif.id);
      setNotifications(notifications.filter(n => n.id !== notif.id));
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed top-4 left-4 z-50 p-2 bg-secondary rounded-md hover:bg-accent"
      >
        <Menu className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="w-80 bg-secondary border-r border-border flex flex-col h-screen">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Image src="/logo.png" alt="Ayu Bot Logo" width={24} height={24} className="object-contain" />
          {process.env.NEXT_PUBLIC_APP_NAME || 'Ayu Bot'}
        </h2>
        <button onClick={onToggle} className="p-1 hover:bg-accent rounded-md">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide">
        <div className="px-4 py-2">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase mb-2">Sessions</h3>
          <div className="space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSessionClick(session.id)}
                className={`group flex items-center justify-between p-3 rounded-md cursor-pointer ${
                  currentSessionId === session.id
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-accent/50'
                }`}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <MessageSquare className="w-4 h-4 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {truncate(session.first_message || 'New Chat', 30)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(session.last_active)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(session.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/20 rounded"
                >
                  <Trash2 className={`w-4 h-4 ${deleteConfirm === session.id ? 'text-destructive' : ''}`} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {notifications.length > 0 && (
          <div className="px-4 py-2 mt-4">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase mb-2 flex items-center gap-2">
              <Bell className="w-3 h-3" />
              Notifications ({notifications.length})
            </h3>
            <div className="space-y-2">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className="p-3 bg-accent/50 rounded-md cursor-pointer hover:bg-accent"
                >
                  <p className="text-sm">{notif.message}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatDate(notif.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-border space-y-2">
        <button
          onClick={onProfileClick}
          className="w-full flex items-center gap-2 px-4 py-2 hover:bg-accent rounded-md text-sm"
        >
          <User className="w-4 h-4" />
          <span className="flex-1 text-left truncate">{user?.username || 'Profile'}</span>
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-4 py-2 hover:bg-destructive/20 text-destructive rounded-md text-sm"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </div>
  );
}
