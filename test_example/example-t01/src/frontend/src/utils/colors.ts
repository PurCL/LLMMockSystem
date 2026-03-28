export const stringToColor = (str: string) => {
    // Predefined vibrant palette (Google Docs style)
    const palette = [
        '#4285F4', // Blue
        '#EA4335', // Red
        '#FBBC05', // Yellow
        '#34A853', // Green
        '#FF6D00', // Orange
        '#46BDC6', // Cyan
        '#7B1FA2', // Purple
        '#C2185B', // Pink
        '#0097A7', // Dark Cyan
        '#5D4037', // Brown
    ];

    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }

    // Use the hash to pick a color from the palette
    const index = Math.abs(hash) % palette.length;
    return palette[index];
};
