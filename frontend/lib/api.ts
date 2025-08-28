import axios, { AxiosInstance } from "axios";
import type { AuthResponse } from "./types/auth";
import type { UpdateProfilePayload } from "./types/user";

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

// ---- Auth & User APIs ----

const persistTokens = (data: AuthResponse) => {
	if (typeof window === "undefined") return;
	if (data.access) localStorage.setItem("access_token", data.access);
	if (data.refresh) localStorage.setItem("refresh_token", data.refresh);
};

// Login with email + password
export async function login(email: string, password: string): Promise<AuthResponse> {
	const { data } = await apiClient.post<AuthResponse>("/auth/login/", { email, password });
	persistTokens(data);
	return data;
}

// Register with email + password (backend requires password_confirm)
export async function register(email: string, password: string): Promise<AuthResponse> {
	const { data } = await apiClient.post<AuthResponse>("/auth/register/", {
		email,
		password,
		password_confirm: password,
	});
	persistTokens(data);
	return data;
}

// Update profile fields: contact_email, first_name, last_name, optional avatar

export async function updateProfile(payload: UpdateProfilePayload) {
	// If avatar is provided as File/Blob, use multipart/form-data; otherwise JSON
	if (payload.avatar instanceof Blob) {
		const form = new FormData();
		if (payload.contact_email !== undefined) form.append("contact_email", payload.contact_email);
		if (payload.first_name !== undefined) form.append("first_name", payload.first_name);
		if (payload.last_name !== undefined) form.append("last_name", payload.last_name);
		form.append("avatar", payload.avatar);
		const { data } = await apiClient.patch("/users/update_profile/", form, {
			headers: { "Content-Type": "multipart/form-data" },
		});
		return data;
	}

	const body: Record<string, any> = {};
	if (payload.contact_email !== undefined) body.contact_email = payload.contact_email;
	if (payload.first_name !== undefined) body.first_name = payload.first_name;
	if (payload.last_name !== undefined) body.last_name = payload.last_name;
	const { data } = await apiClient.patch("/users/update_profile/", body);
	return data;
}

// Change password: old_password, new_password, new_password_confirm
export async function changePassword(oldPassword: string, newPassword: string) {
	const { data } = await apiClient.post("/users/change_password/", {
		old_password: oldPassword,
		new_password: newPassword,
		new_password_confirm: newPassword,
	});
	return data;
}

export function logout() {
	if (typeof window === "undefined") return;
	localStorage.removeItem("access_token");
	localStorage.removeItem("refresh_token");
}