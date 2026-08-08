const themeToggle = document.querySelector("[data-theme-toggle]");
const root = document.documentElement;

function setTheme(theme) {
    const isLight = theme === "light";
    root.classList.toggle("light-theme", isLight);
    themeToggle.setAttribute("aria-pressed", String(isLight));
    themeToggle.textContent = isLight ? "Use dark mode" : "Use light mode";
    localStorage.setItem("pocketsocket-theme", theme);
}

const savedTheme = localStorage.getItem("pocketsocket-theme");
setTheme(savedTheme === "light" ? "light" : "dark");

themeToggle.addEventListener("click", () => {
    setTheme(root.classList.contains("light-theme") ? "dark" : "light");
});


const { createApp, ref } = Vue

createApp({
    setup() {
      const message = ref('Hello vue!')
      return {
        message
      }
    }
}).mount('#app')