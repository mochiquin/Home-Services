import axios, { AxiosInstance } from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
const timeout = Number(process.env.NEXT_PUBLIC_API_TIMEOUT || 10000);

export const apiClient: AxiosInstance = axios.create({
	baseURL,
	timeout,
	headers: {
		"Content-Type": "application/json",
	},
});

apiClient.interceptors.request.use((config) => {
	if (typeof window !== "undefined") {
		const token = localStorage.getItem("access_token");
		if (token) {
			config.headers = config.headers ?? {};
			config.headers.Authorization = `Bearer ${token}`;
		}
	}
	return config;
});

apiClient.interceptors.response.use(
	(response) => response,
	(error) => {
		return Promise.reject(error);
	}
);
