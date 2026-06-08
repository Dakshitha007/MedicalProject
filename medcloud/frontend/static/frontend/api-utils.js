// API Utilities for Frontend
const API_BASE = '/api';

/**
 * Get CSRF token from cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!localStorage.getItem('access_token');
}

/**
 * Get user info from localStorage
 */
function getUser() {
    const stored = {
        id: localStorage.getItem('user_id'),
        email: localStorage.getItem('user_email'),
        role: localStorage.getItem('user_role')
    };

    if (stored.id || stored.email || stored.role) {
        return stored;
    }

    return window.CURRENT_USER || { id: null, email: '', role: '' };
}

/**
 * Verify role-based access
 */
function requireRole(requiredRole) {
    const user = getUser();
    if (!user.role) {
        window.location.href = '/';
        return false;
    }
    if (user.role !== requiredRole) {
        alert(`Access denied. This page is for ${requiredRole}s only.`);
        window.location.href = '/';
        return false;
    }
    return true;
}

/**
 * Make API request with authentication
 */
async function apiCall(endpoint, method = 'GET', body = null) {
    const token = localStorage.getItem('access_token');
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers,
        credentials: 'include',
    };

    if (body && method !== 'GET') {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);

        if (response.status === 401) {
            if (token) {
                console.warn('Token expired, attempting refresh');
                const refreshed = await refreshToken();
                if (refreshed) {
                    return apiCall(endpoint, method, body);
                }
            }
            localStorage.clear();
            window.location.href = '/';
            return null;
        }

        if (response.status === 403) {
            console.error('Access denied - insufficient permissions');
            alert('You do not have permission to access this resource.');
            return null;
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API call error:', error);
        return null;
    }
}

/**
 * Refresh access token
 */
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        return false;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ refresh: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            return true;
        } else {
            return false;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        return false;
    }
}

/**
 * Logout user
 */
function logout() {
    localStorage.clear();
    window.location.href = '/';
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format number as currency
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}
