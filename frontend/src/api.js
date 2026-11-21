import axios from "axios";

const rawConfiguredUrl = (process.env.REACT_APP_API_URL || "http://localhost:8000")
  .trim()
  .replace(/\/+$/, "");

export const API_ROOT_URL = rawConfiguredUrl.replace(/\/api\/v1$/, "");
export const API_BASE_URL = `${API_ROOT_URL}/api/v1`;

const slowListeners = new Set();
let pendingSlowCount = 0;

function notifySlowState(isSlow) {
  slowListeners.forEach((cb) => cb(isSlow));
}

export function subscribeSlowBackend(callback) {
  slowListeners.add(callback);
  return () => slowListeners.delete(callback);
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 65000,
});

api.interceptors.request.use((config) => {
  config._slowTimer = setTimeout(() => {
    config._markedSlow = true;
    pendingSlowCount += 1;
    notifySlowState(true);
  }, 3000);
  return config;
});

function clearSlowTimer(config) {
  if (config?._slowTimer) {
    clearTimeout(config._slowTimer);
    config._slowTimer = null;
  }
  if (config?._markedSlow) {
    config._markedSlow = false;
    pendingSlowCount = Math.max(0, pendingSlowCount - 1);
    if (pendingSlowCount === 0) {
      notifySlowState(false);
    }
  }
}

api.interceptors.response.use(
  (response) => {
    clearSlowTimer(response.config);
    return response;
  },
  (error) => {
    clearSlowTimer(error.config);
    return Promise.reject(error);
  }
);

export const wakeBackend = async () => {
  const { data } = await axios.get(`${API_ROOT_URL}/health`, { timeout: 35000 });
  return data;
};

export const fetchSystemStatus = async () => {
  const { data } = await api.get("/config/status");
  return data;
};

export const fetchResumes = async () => {
  const { data } = await api.get("/resumes/");
  return data;
};

export const fetchSealedResumes = async () => {
  const { data } = await api.post("/resumes/live");
  return data;
};

export const fetchResumeById = async (id) => {
  const { data } = await api.get(`/resume/${id}`);
  return data;
};

export const deleteResumeById = async (id) => {
  const { data } = await api.delete(`/resume/${id}`);
  return data;
};

export const uploadResumesBatch = async (files) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  const { data } = await api.post("/resume/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const fetchBatchStatus = async (batchId) => {
  const { data } = await api.get(`/resume/batch/${batchId}`);
  return data;
};

export const searchResumes = async (userPrompt, topK = 5) => {
  const { data } = await api.post("/search-resume/", {
    user_prompt: userPrompt,
    top_k: topK,
  });
  return data;
};
