/**
 * User Preferences Service
 * Manages user-specific settings stored in localStorage
 */

export interface UserPreferences {
    autoSpellCheck: boolean;
}

const PREFERENCES_KEY = 'docuserve_preferences';

const DEFAULT_PREFERENCES: UserPreferences = {
    autoSpellCheck: false
};

/**
 * Get user preferences from localStorage
 */
export const getPreferences = (): UserPreferences => {
    try {
        const stored = localStorage.getItem(PREFERENCES_KEY);
        if (stored) {
            const parsed = JSON.parse(stored);
            return { ...DEFAULT_PREFERENCES, ...parsed };
        }
    } catch (error) {
        console.error('Failed to load preferences:', error);
    }
    return { ...DEFAULT_PREFERENCES };
};

/**
 * Save user preferences to localStorage
 */
export const setPreferences = (prefs: Partial<UserPreferences>): void => {
    try {
        const current = getPreferences();
        const updated = { ...current, ...prefs };
        localStorage.setItem(PREFERENCES_KEY, JSON.stringify(updated));
    } catch (error) {
        console.error('Failed to save preferences:', error);
    }
};

/**
 * Toggle a specific preference
 */
export const togglePreference = (key: keyof UserPreferences): void => {
    const current = getPreferences();
    setPreferences({ [key]: !current[key] });
};
