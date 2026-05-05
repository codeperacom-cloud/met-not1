(function () {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("notiva-theme");
  const initialTheme = savedTheme || "dark";

  function setTheme(theme) {
    root.dataset.theme = theme;
    localStorage.setItem("notiva-theme", theme);
    document.querySelectorAll("#themeToggle").forEach((button) => {
      button.textContent = theme === "dark" ? "☼" : "◐";
      button.title = theme === "dark" ? "Light mode" : "Dark mode";
    });
  }

  setTheme(initialTheme);
  document.addEventListener("click", (event) => {
    if (event.target && event.target.id === "themeToggle") {
      setTheme(root.dataset.theme === "dark" ? "light" : "dark");
    }
  });
})();
