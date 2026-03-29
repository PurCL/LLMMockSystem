import { useState, useEffect } from 'react';
import { AlertCircle, X, Info, CheckCircle, AlertTriangle } from 'lucide-react';

// Simplified event emitter for the global alert
const alertEvents = {
    listeners: [] as ((message: string) => void)[],
    emit(message: string) {
        this.listeners.forEach(l => l(message));
    },
    subscribe(listener: (message: string) => void) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }
};
// Override window.alert globally
if (typeof window !== 'undefined') {
    // Preserve original just in case, though we primarily want to override
    window.alert = (message: any) => {
        // console.log(" Custom alert trigger:", message);
        alertEvents.emit(String(message));
    };
}
/**
 * CustomAlert component for global notifications.
 * It follows the premium DMS design system.
 */
export const CustomAlert = () => {
    const [isVisible, setIsVisible] = useState(false);
    const [config, setConfig] = useState({
        type: 'info' as 'info' | 'success' | 'warning' | 'error',
        message: '',
    });

    useEffect(() => {
        // We can trigger this alert using custom events for now
        // This makes it easy to use from anywhere without complex state management
        const handleShowAlert = (e: any) => {
            const { type, message } = e.detail || {};
            if (message) {
                setConfig({ type: type || 'info', message });
                setIsVisible(true);

                // Auto-hide after 5 seconds
                const timer = setTimeout(() => {
                    setIsVisible(false);
                }, 5000);

                return () => clearTimeout(timer);
            }
        };

        window.addEventListener('dms-alert' as any, handleShowAlert);
        return () => window.removeEventListener('dms-alert' as any, handleShowAlert);
    }, []);

    if (!isVisible) return null;

    const typeStyles = {
        info: {
            container: "bg-indigo-50 border-indigo-200 text-indigo-800",
            icon: "text-indigo-500",
            hover: "hover:bg-indigo-100"
        },
        success: {
            container: "bg-emerald-50 border-emerald-200 text-emerald-800",
            icon: "text-emerald-500",
            hover: "hover:bg-emerald-100"
        },
        warning: {
            container: "bg-amber-50 border-amber-200 text-amber-800",
            icon: "text-amber-500",
            hover: "hover:bg-amber-100"
        },
        error: {
            container: "bg-rose-50 border-rose-200 text-rose-800",
            icon: "text-rose-500",
            hover: "hover:bg-rose-100"
        }
    };

    const style = typeStyles[config.type] || typeStyles.info;
    const Icon = {
        info: Info,
        success: CheckCircle,
        warning: AlertTriangle,
        error: AlertCircle,
    }[config.type] || Info;

    return (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[9999] w-full max-w-lg px-4 pointer-events-none">
            <div className={`
                flex items-center gap-4 p-4 rounded-2xl border shadow-xl backdrop-blur-md
                pointer-events-auto transition-all duration-300 ease-out
                animate-in fade-in slide-in-from-top-8
                ${style.container}
            `}>
                <div className={`p-2 rounded-xl bg-white/50 ${style.icon}`}>
                    <Icon size={22} strokeWidth={2.5} />
                </div>

                <div className="flex-1">
                    <p className="text-sm font-semibold tracking-tight">
                        {config.message}
                    </p>
                </div>

                <button
                    onClick={() => setIsVisible(false)}
                    className={`p-2 rounded-xl transition-all duration-200 ${style.hover}`}
                    aria-label="Close alert"
                >
                    <X size={18} />
                </button>
            </div>
        </div>
    );
};
