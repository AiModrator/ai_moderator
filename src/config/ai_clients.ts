import axios, { AxiosInstance } from 'axios';

export const huggingFaceTranslatorClient: AxiosInstance = axios.create({
  baseURL: 'https://router.huggingface.co/hf-inference',
  timeout: 30000,
  headers: {
    'Authorization': `Bearer ${process.env.HF_TOKEN || ''}`,
    'Content-Type': 'application/json',
  },
});

export default huggingFaceTranslatorClient;




