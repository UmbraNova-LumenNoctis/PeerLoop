import { useState, useCallback } from 'react';
import axios, { AxiosError } from 'axios';
import { ensureAccessToken, refreshAccessToken, resolveApiBaseUrl } from '@/utils/authSession';
import { formatApiErrorMessage } from '@/utils/errorMessages';

interface ExecuteOptions<T = any>
{
	url: string;
	method?: "GET" | "POST" | "DELETE" | "PUT" | "PATCH";
	body?: T | null;
	params?: Record<string, any> | null; 
	useToken?: boolean;
}

interface APIData<T = any>
{
	data: T | null;
  	error: any;
	isLoading: boolean,
	execute(
		options: ExecuteOptions<T>
	): Promise<T>;
}

const api = axios.create({
	baseURL: resolveApiBaseUrl(),
	timeout: 60000
});

const useApi = <T = any>(): APIData<T> => {
	const [data, setData] = useState<T | null>(null);
	const [error, setError] = useState<any>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);

	const execute = useCallback(
	async ({
		url,
		useToken = false,
		method = "GET",
		body = null,
		params = null
	}: ExecuteOptions<T>): Promise<T> => {
		setError(null);
		setIsLoading(true);

		try {
			const headers: Record<string, string> = {};
			if (useToken) {
				const token = await ensureAccessToken();
				if (token) headers['Authorization'] = `Bearer ${token}`;
			}

			const requestConfig = {
				url, 
				method, 
				headers,
				data: body,
				params
			} as const;

			const response = await api(requestConfig);

			setData(response.data);
			return (response.data);
		} catch (err: any) {
			const axiosError = err as AxiosError<{ message?: string }>;
			if (useToken && axiosError.response?.status === 401) {
				try {
					const refreshedToken = await refreshAccessToken();
					if (refreshedToken) {
						const retryHeaders: Record<string, string> = {
							...((axiosError.config?.headers as Record<string, string> | undefined) || {}),
							Authorization: `Bearer ${refreshedToken}`
						};
						const retryResponse = await api({
							url,
							method,
							headers: retryHeaders,
							data: body,
							params
						});
						setData(retryResponse.data);
						return retryResponse.data;
					}
				} catch {
					// Fall through to error handling below.
				}
			}
			const backendMessage = axiosError.response?.data?.message || err.message || 'Something went wrong';
			const errorMessage = formatApiErrorMessage({
				statusCode: axiosError.response?.status,
				detail: backendMessage,
				endpoint: url,
			});

			setError(errorMessage);
			throw new Error(errorMessage);
		} finally {
			setIsLoading(false);
		}
	}, []);

	return ({ data, error, isLoading, execute });
};

export default useApi;
