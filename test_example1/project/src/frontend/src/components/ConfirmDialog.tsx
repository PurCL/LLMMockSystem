import React from 'react';
import { X, AlertTriangle } from 'lucide-react';
interface ConfirmDialogProps {
    isOpen: boolean;
    title: string;
    message: React.ReactNode;
    onConfirm: () => void;
    onCancel: () => void;
    confirmText?: string;
    cancelText?: string;
    danger?: boolean;
}
export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
    isOpen,
    title,
    message,
    onConfirm,
    onCancel,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    danger = false,
}) => {
    if (!isOpen) return null;
    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(2px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            animation: 'fadeIn 0.2s ease-out'
        }}>
            <div style={{
                backgroundColor: 'white',
                borderRadius: '12px',
                width: '100%',
                maxWidth: '420px',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
                overflow: 'hidden',
                margin: '0 1rem',
                border: '1px solid var(--border-color)',
                animation: 'slideUp 0.3s ease-out'
            }}>
                {/* Header */}
                <div style={{
                    padding: '1.25rem 1.5rem',
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: danger ? '#fef2f2' : 'white' // Subtle red bg for danger
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '8px',
                            backgroundColor: danger ? '#fee2e2' : '#f3f4f6',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: danger ? '#ef4444' : 'var(--text-secondary)'
                        }}>
                            {danger ? <AlertTriangle size={18} /> : <AlertTriangle size={18} />}
                        </div>
                        <h3 style={{
                            margin: 0,
                            fontSize: '1.125rem',
                            fontWeight: 600,
                            color: danger ? '#b91c1c' : 'var(--text-primary)'
                        }}>
                            {title}
                        </h3>
                    </div>
                    <button
                        onClick={onCancel}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--text-tertiary)',
                            padding: '4px',
                            display: 'flex'
                        }}
                    >
                        <X size={20} />
                    </button>
                </div>
                {/* Body */}
                <div style={{
                    padding: '1.5rem',
                    color: 'var(--text-secondary)',
                    lineHeight: '1.6',
                    fontSize: '0.95rem'
                }}>
                    {message}
                </div>
                {/* Footer */}
                <div style={{
                    padding: '1rem 1.5rem',
                    backgroundColor: '#f9fafb',
                    borderTop: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'flex-end',
                    gap: '0.75rem'
                }}>
                    <button
                        onClick={onCancel}
                        className="btn"
                        style={{
                            backgroundColor: 'white',
                            border: '1px solid var(--border-color)',
                            color: 'var(--text-primary)',
                            padding: '0.5rem 1rem',
                            borderRadius: '6px',
                            fontWeight: 500,
                            cursor: 'pointer'
                        }}
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={onConfirm}
                        className="btn"
                        style={{
                            backgroundColor: danger ? '#ef4444' : 'var(--primary)',
                            color: 'white',
                            border: 'none',
                            padding: '0.5rem 1rem',
                            borderRadius: '6px',
                            fontWeight: 500,
                            boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                            cursor: 'pointer'
                        }}
                    >
                        {confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
};
