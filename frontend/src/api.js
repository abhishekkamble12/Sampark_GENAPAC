const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('sampark_token') || null;
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('sampark_token', token);
    } else {
      localStorage.removeItem('sampark_token');
    }
  }

  getToken() {
    return this.token;
  }

  isAuthenticated() {
    return !!this.token;
  }

  getUser() {
    if (!this.token) return null;
    try {
      // Simple base64 decode of JWT payload
      const base64Url = this.token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        window
          .atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (e) {
      console.error('Failed to decode token', e);
      return null;
    }
  }

  async request(endpoint, options = {}) {
    const url = `${BASE_URL}${endpoint}`;
    const headers = options.headers || {};
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (response.status === 401) {
      this.setToken(null);
      window.location.reload();
      throw new Error('Unauthorized');
    }

    if (response.status === 204) {
      return null;
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Request failed');
    }
    return data;
  }

  async login(username, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    this.setToken(data.access_token);
    return this.getUser();
  }

  logout() {
    this.setToken(null);
  }

  async reportIssue(description, wardId, lat, lng, session_id, imageUrl = null) {
    return await this.request('/issues', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        description,
        image_url: imageUrl,
        session_id,
        location: {
          lat: parseFloat(lat),
          lng: parseFloat(lng),
          ward_id: wardId
        }
      })
    });
  }

  async getDashboard() {
    return await this.request('/analytics/dashboard');
  }

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const url = `${BASE_URL}/admin/knowledge-base`;
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || 'Upload failed');
    }
    return await response.json();
  }

  async listDocuments() {
    return await this.request('/admin/knowledge-base');
  }

  async deleteDocument(documentId) {
    return await this.request(`/admin/knowledge-base/${encodeURIComponent(documentId)}`, {
      method: 'DELETE'
    });
  }

  getStreamUrl(endpoint) {
    return `${BASE_URL}${endpoint}`;
  }
}

export const api = new ApiClient();
