const API = {
  async request(url, options = {}) {
    const response = await fetch(url, { headers: {'Content-Type':'application/json', ...(options.headers||{})}, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Something went wrong');
    return data;
  },
  login: (email,password) => API.request('/api/login',{method:'POST',body:JSON.stringify({email,password})}),
  register: (name,email,password) => API.request('/api/register',{method:'POST',body:JSON.stringify({name,email,password})}),
  logout: () => API.request('/api/logout',{method:'POST'}),
  me: () => API.request('/api/me'),
  tasks: () => API.request('/api/tasks'),
  createTask: task => API.request('/api/tasks',{method:'POST',body:JSON.stringify(task)}),
  updateTask: (id,task) => API.request(`/api/tasks/${id}`,{method:'PUT',body:JSON.stringify(task)}),
  deleteTask: id => API.request(`/api/tasks/${id}`,{method:'DELETE'}),
  completeTask: id => API.request(`/api/tasks/${id}/complete`,{method:'PATCH'}),
  profile: data => API.request('/api/profile',{method:'PUT',body:JSON.stringify(data)}),
  settings: data => API.request('/api/settings',{method:'PUT',body:JSON.stringify(data)}),
  password: password => API.request('/api/password',{method:'PUT',body:JSON.stringify({password})}),
  reports: () => API.request('/api/reports')
};
