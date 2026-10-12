const loginForm = document.getElementById('loginForm');
if (loginForm) loginForm.addEventListener('submit', async e => {
  e.preventDefault();
  const button = loginForm.querySelector('button[type="submit"]');
  try {
    if (button) button.disabled = true;
    await API.login(document.getElementById('email').value.trim(), document.getElementById('password').value);
    location.href = 'dashboard.html';
  } catch (err) {
    alert(err.message);
  } finally {
    if (button) button.disabled = false;
  }
});

const registerForm = document.getElementById('registerForm');
if (registerForm) registerForm.addEventListener('submit', async e => {
  e.preventDefault();
  const password = document.getElementById('registerPassword').value;
  const confirm = document.getElementById('confirmPassword').value;
  if (password !== confirm) return alert('Passwords do not match!');
  const button = registerForm.querySelector('button[type="submit"]');
  try {
    if (button) button.disabled = true;
    await API.register(
      document.getElementById('name').value.trim(),
      document.getElementById('registerEmail').value.trim(),
      password
    );
    location.href = 'dashboard.html';
  } catch (err) {
    alert(err.message);
  } finally {
    if (button) button.disabled = false;
  }
});

async function protectPage() {
  if (document.body.classList.contains('auth-page')) {
    try {
      const result = await API.me();
      if (result.authenticated) location.href = 'dashboard.html';
    } catch (_) {}
    return;
  }
  try {
    const result = await API.me();
    if (!result.authenticated) {
      location.href = 'index.html';
      return;
    }
    document.body.classList.toggle('dark-mode', result.user.darkTheme === true);
  } catch (_) {
    location.href = 'index.html';
  }
}

async function logout() {
  try { await API.logout(); }
  finally { location.href = 'index.html'; }
}

document.addEventListener('DOMContentLoaded', protectPage);
