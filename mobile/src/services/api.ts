import axios from 'axios';

// Emulyator uchun 10.0.2.2:5050 yoki kompyuteringizning mahalliy IP manzili (masalan: 192.168.1.100:5050)
export const API_BASE_URL = 'http://10.0.2.2:5050';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export const getGarments = async () => {
  const res = await apiClient.get('/api/garments');
  return res.data;
};

export const getHistory = async () => {
  const res = await apiClient.get('/api/history');
  return res.data;
};

export const deleteHistoryItem = async (id: number) => {
  const res = await apiClient.delete(`/api/history/${id}`);
  return res.data;
};

export const clearAllHistory = async () => {
  const res = await apiClient.delete('/api/history');
  return res.data;
};

export const performTryOn = async (userImageUri: string, garmentUrl: string, size: string) => {
  const formData = new FormData();
  
  formData.append('user_image', {
    uri: userImageUri,
    type: 'image/jpeg',
    name: 'user_photo.jpg',
  } as any);

  formData.append('garment_url', garmentUrl);
  formData.append('selected_size', size);

  const res = await apiClient.post('/api/tryon', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return res.data;
};
