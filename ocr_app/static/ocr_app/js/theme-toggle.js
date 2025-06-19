// Theme toggle script
document.addEventListener('DOMContentLoaded', function () {
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', currentTheme);

    if (themeToggle) {
        themeToggle.checked = currentTheme === 'dark';
        themeToggle.addEventListener('change', function () {
            const theme = this.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-bs-theme', theme);
            localStorage.setItem('theme', theme);
        });
    }
});
