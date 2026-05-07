'use client';

import { useState, useRef, useEffect } from 'react';
import { useStore } from '@/lib/store';
import { chatAPI } from '@/lib/api';
import { Send, Menu, Settings, Eye, EyeOff } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatAreaProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export default function ChatArea({ sidebarOpen, onToggleSidebar }: ChatAreaProps) {
  const { messages, currentSessionId, addMessage, setIsLoading, isLoading, customApiKey, setCustomApiKey, clearCustomApiKey } = useStore();
  const [input, setInput] = useState('');
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [showApiKeyValue, setShowApiKeyValue] = useState(false);
  const [draftApiKey, setDraftApiKey] = useState('');
  const [apiKeyError, setApiKeyError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const suggestions = [
    'Find hospitals in Delhi',
    'Remind me to drink water in 30 minutes',
    'Tell me about yourself',
    'I am 25 years old',
  ];

  useEffect(() => {
    const timer = setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
    return () => clearTimeout(timer);
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  useEffect(() => {
    const savedKey = localStorage.getItem('customGeminiApiKey');
    if (savedKey) {
      setCustomApiKey(savedKey);
      setDraftApiKey(savedKey);
    }
  }, [setCustomApiKey]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user' as const,
      text: input,
      created_at: new Date().toISOString(),
    };

    addMessage(userMessage);
    const userInput = input;
    setInput('');
    setIsLoading(true);

    const maxRetries = 3;
    let retryCount = 0;
    let delay = 1000; 

    const attemptSend = async (): Promise<void> => {
      try {
        const response = await chatAPI.sendMessage({
          user_input: userInput,
          session_id: currentSessionId,
          ...(customApiKey ? { api_key: customApiKey } : {}),
        });

        const botMessage = {
          role: 'bot' as const,
          text: response.data.response,
          created_at: new Date().toISOString(),
        };

        addMessage(botMessage);
      } catch (error: any) {
        console.error('Failed to send message:', error);
        
        if (error.response?.status === 429 && retryCount < maxRetries) {
          retryCount++;
          const waitTime = delay * Math.pow(2, retryCount - 1);
          
          const retryMessage = {
            role: 'bot' as const,
            text: `Rate limit reached. Retrying in ${waitTime / 1000} seconds... (Attempt ${retryCount}/${maxRetries})`,
            created_at: new Date().toISOString(),
          };
          addMessage(retryMessage);
          
          await new Promise(resolve => setTimeout(resolve, waitTime));
          return attemptSend();
        }
        
        let errorText = 'Sorry, I encountered an error. Please try again.';
        
        if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
          errorText = 'Request timed out. Please check your connection and try again.';
        } else if (error.response?.status === 429) {
          errorText = 'Too many requests. Please wait a moment before trying again.';
        } else if (error.response?.status >= 500) {
          errorText = 'Server error. Our team has been notified. Please try again later.';
        } else if (error.response?.status === 401) {
          errorText = 'Your session has expired. Please log in again.';
          setTimeout(() => {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
          }, 2000);
        } else if (error.response?.data?.detail) {
          errorText = error.response.data.detail;
        }
        
        const errorMessage = {
          role: 'bot' as const,
          text: errorText,
          created_at: new Date().toISOString(),
        };
        addMessage(errorMessage);
      } finally {
        setIsLoading(false);
      }
    };

    await attemptSend();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleSuggestionClick = (text: string) => {
    setInput(text);
    textareaRef.current?.focus();
  };

  const handleConnectApiKey = () => {
    const trimmed = draftApiKey.trim();
    if (!trimmed) return;
    if (!/^AIza[0-9A-Za-z\-_]{20,}$/.test(trimmed)) {
      setApiKeyError('Invalid Gemini API key format.');
      return;
    }
    setApiKeyError('');
    setCustomApiKey(trimmed);
    setShowApiKeyModal(false);
  };

  const handleDisconnectApiKey = () => {
    clearCustomApiKey();
    setDraftApiKey('');
    setShowApiKeyValue(false);
    setApiKeyError('');
  };

  const handleOpenApiKeyModal = () => {
    setDraftApiKey(customApiKey);
    setApiKeyError('');
    setShowApiKeyModal(true);
  };

  return (
    <div className="flex-1 flex flex-col h-screen">
      <div className="p-4 border-b border-border flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {!sidebarOpen && (
          <button
            onClick={onToggleSidebar}
            className="p-2 hover:bg-accent rounded-md"
          >
            <Menu className="w-5 h-5" />
          </button>
          )}
          <span className={`text-xs px-2 py-1 rounded-full border ${customApiKey ? 'border-emerald-500/40 text-emerald-600' : 'border-border text-muted-foreground'}`}>
            {customApiKey ? 'Connected: Custom key' : 'Using default backend key'}
          </span>
        </div>
        <button
          type="button"
          onClick={handleOpenApiKeyModal}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-input rounded-md hover:bg-accent"
        >
          <Settings className="w-4 h-4" />
          API Key
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-4">
              <h2 className="text-2xl font-bold text-foreground">Welcome to Ayu ChatBot</h2>
              <p className="text-muted-foreground">Start a conversation by typing a message below</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 max-w-2xl">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="p-4 border border-border rounded-lg hover:bg-accent/50 text-left"
                  >
                    <p className="text-sm font-medium">{suggestion}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-secondary-foreground'
                  }`}
                >
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.text}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-secondary rounded-lg p-4">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <div className="p-4 border-t border-border">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Shift+Enter for new line)"
            className="flex-1 px-4 py-3 bg-background border border-input rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none max-h-32"
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>

      {showApiKeyModal && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-background border border-border rounded-lg p-4 space-y-4">
            <div>
              <h3 className="text-base font-semibold text-foreground">Gemini API Key</h3>
              <p className="text-sm text-muted-foreground">Paste Gemini API Key</p>
            </div>

            <div className="relative">
              <input
                type={showApiKeyValue ? 'text' : 'password'}
                value={draftApiKey}
                onChange={(e) => {
                  setDraftApiKey(e.target.value);
                  if (apiKeyError) setApiKeyError('');
                }}
                placeholder="AIza..."
                className="w-full pr-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button
                type="button"
                onClick={() => setShowApiKeyValue((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
              >
                {showApiKeyValue ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {apiKeyError && <p className="text-sm text-destructive">{apiKeyError}</p>}

            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={handleDisconnectApiKey}
                className="px-3 py-2 text-sm border border-input rounded-md hover:bg-accent"
              >
                Disconnect / Reset
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowApiKeyModal(false)}
                  className="px-3 py-2 text-sm border border-input rounded-md hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConnectApiKey}
                  disabled={!draftApiKey.trim()}
                  className="px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                  Connect / Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
