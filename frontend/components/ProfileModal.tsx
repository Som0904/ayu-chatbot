'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/lib/store';
import { chatAPI } from '@/lib/api';
import { X } from 'lucide-react';

interface ProfileModalProps {
  onClose: () => void;
}

export default function ProfileModal({ onClose }: ProfileModalProps) {
  const { profile, setProfile, user } = useStore();
  const [editedProfile, setEditedProfile] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    setEditedProfile(profile);
  }, [profile]);

  const handleSave = async (key: string, value: string) => {
    setSaving(true);
    setSaveMessage('');
    try {
      await chatAPI.updateProfile({ key, value });
      setProfile({ ...profile, [key]: value });
      setSaveMessage(`Saved ${key}`);
    } catch (error) {
      console.error('Failed to update profile:', error);
      setSaveMessage(`Failed to save ${key}`);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key: string, value: string) => {
    setEditedProfile({ ...editedProfile, [key]: value });
  };

  const handleBlur = (key: string) => {
    if (editedProfile[key] !== profile[key]) {
      handleSave(key, editedProfile[key]);
    }
  };

  const fields = [
    { key: 'age', label: 'Age', type: 'number' },
    { key: 'city', label: 'City', type: 'text' },
    { key: 'country', label: 'Country', type: 'text' },
    { key: 'occupation', label: 'Occupation', type: 'text' },
    { key: 'interests', label: 'Interests', type: 'text' },
    { key: 'preferences', label: 'Preferences', type: 'text' },
  ];

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        <div className="p-6 border-b border-border flex items-center justify-between bg-secondary">
          <div>
            <h2 className="text-2xl font-bold text-foreground">Profile</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {user?.email} | {user?.username}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 bg-background">
          <div className="space-y-4">
            <div className="p-4 bg-secondary rounded-lg border border-border">
              <p className="text-sm text-muted-foreground">
                Your profile is automatically updated when you share personal information in conversations.
                You can also manually edit any field below.
              </p>
              {saveMessage && <p className="text-xs mt-2 text-foreground">{saveMessage}</p>}
            </div>

            {fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-foreground mb-2">
                  {field.label}
                </label>
                <input
                  type={field.type}
                  value={editedProfile[field.key] || ''}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                  onBlur={() => handleBlur(field.key)}
                  className="w-full px-4 py-2 bg-secondary border border-input rounded-md text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all"
                  placeholder={`Enter your ${field.label.toLowerCase()}`}
                />
              </div>
            ))}

            {Object.keys(editedProfile).filter(key => !fields.find(f => f.key === key)).length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-foreground mb-3">Additional Information</h3>
                <div className="space-y-3">
                  {Object.keys(editedProfile)
                    .filter(key => !fields.find(f => f.key === key))
                    .map((key) => (
                      <div key={key} className="flex items-center gap-3">
                        <span className="text-sm font-medium text-muted-foreground min-w-[120px] capitalize">
                          {key}:
                        </span>
                        <input
                          type="text"
                          value={editedProfile[key] || ''}
                          onChange={(e) => handleChange(key, e.target.value)}
                          onBlur={() => handleBlur(key)}
                          className="flex-1 px-3 py-1 bg-secondary border border-input rounded text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-6 border-t border-border flex justify-end gap-3 bg-secondary">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-foreground hover:bg-accent rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
}
