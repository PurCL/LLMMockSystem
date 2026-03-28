export const getBrowserId = (): string => {
    const key = 'docuserve_browser_id';
    // Use localStorage for persistence across sessions/tabs
    let id = localStorage.getItem(key);
    if (!id) {
        // Generate a more robust ID (e.g., using date + random) to avoid collisions
        id = 'user_' + Math.random().toString(36).substring(2, 9);
        localStorage.setItem(key, id);
    }
    return id;
};
