import toast, { type ToastOptions } from 'react-hot-toast';

// Custom toast configurations matching DocuServe premium design
export const showSuccess = (message: string, options?: ToastOptions) => {
    toast.success(message, {
        duration: 3000,
        ...options,
        style: {
            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            color: '#fff',
            padding: '16px',
            borderRadius: '12px',
            fontWeight: 500,
            boxShadow: '0 10px 40px rgba(16, 185, 129, 0.3)',
            ...options?.style,
        },
        iconTheme: {
            primary: '#fff',
            secondary: '#10b981',
        },
    });
};

export const showError = (message: string) => {
    toast.error(message, {
        duration: 4000,
        style: {
            background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
            color: '#fff',
            padding: '16px',
            borderRadius: '12px',
            fontWeight: 500,
            boxShadow: '0 10px 40px rgba(239, 68, 68, 0.3)',
        },
        iconTheme: {
            primary: '#fff',
            secondary: '#ef4444',
        },
    });
};

export const showInfo = (message: string) => {
    toast(message, {
        duration: 3000,
        icon: 'ℹ️',
        style: {
            background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
            color: '#fff',
            padding: '16px',
            borderRadius: '12px',
            fontWeight: 500,
            boxShadow: '0 10px 40px rgba(59, 130, 246, 0.3)',
        },
    });
};

export const showWarning = (message: string, options?: ToastOptions) => {
    toast(message, {
        duration: 3500,
        icon: '⚠️',
        ...options,
        style: {
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            color: '#fff',
            padding: '16px',
            borderRadius: '12px',
            fontWeight: 500,
            boxShadow: '0 10px 40px rgba(245, 158, 11, 0.3)',
            ...options?.style,
        },
    });
};
