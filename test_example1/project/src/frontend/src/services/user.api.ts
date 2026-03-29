import axios from 'axios';

const api = axios.create({
    baseURL: '/api/users'
});

export interface User {
    id: number;
    browser_id: string;
    nickname: string;
}

export const syncUser = async (browserId: string): Promise<User> => {
    const response = await api.post<User>('/sync', { browser_id: browserId });
    return response.data;
};
