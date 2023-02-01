import axios from "axios";
import config from "@/config";

const httpApi = axios.create({
  baseURL: config.apiUrl,
  headers: {
    "Content-type": "application/json",
    ...config.apiHeaders,
  },
});

axios.interceptors.request.use((axiosConfig) => {
  axiosConfig.headers = config.apiHeaders;
  return axiosConfig;
});

export default httpApi;
