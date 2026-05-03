import axios from "axios";

// Auth interceptors (token attachment + 401 redirect) are in services/auth.js
// This file just imports auth.js to ensure interceptors are registered.
import "./auth";

const API_URL = import.meta.env.VITE_API_URL;

export const fetchCertificates = async () => {
  const res = await axios.get(`${API_URL}/certificates/`);
  return res.data;
};

export const uploadCertificate = async (file) => {
  let formData = new FormData();
  formData.append("file", file);

  const res = await axios.post(`${API_URL}/certificates/upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const deleteCertificate = async (id) => {
  const res = await axios.delete(`${API_URL}/certificates/${id}`);
  return res.data;
};

export const syncAdminData = async (sheetUrl, folderUrl) => {
  const res = await axios.post(`${API_URL}/admin/sync`, {
    sheet_url: sheetUrl,
    folder_url: folderUrl,
  });
  return res.data;
};
