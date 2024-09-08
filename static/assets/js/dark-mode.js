// Select DOM elements for theme toggle functionality
const themeToggleDarkIcon = document.getElementById("theme-toggle-dark-icon");
const themeToggleLightIcon = document.getElementById("theme-toggle-light-icon");
const themeToggleBtn = document.getElementById("theme-toggle");

// Function to apply the saved theme from localStorage
function applyTheme() {
  // Retrieve the saved theme from localStorage
  const savedTheme = localStorage.getItem("color-theme");

  // Apply the saved theme to the document
  if (savedTheme === "dark") {
    document.documentElement.classList.add("dark");
    themeToggleLightIcon.classList.remove("hidden");
    themeToggleDarkIcon.classList.add("hidden");
  } else {
    document.documentElement.classList.remove("dark");
    themeToggleLightIcon.classList.add("hidden");
    themeToggleDarkIcon.classList.remove("hidden");
  }
}

// Apply the saved theme on page load
applyTheme();

// Event listener for the theme toggle button
themeToggleBtn.addEventListener("click", function () {
  // Toggle the visibility of theme icons
  themeToggleDarkIcon.classList.toggle("hidden");
  themeToggleLightIcon.classList.toggle("hidden");

  // Toggle the theme between dark and light
  if (document.documentElement.classList.contains("dark")) {
    document.documentElement.classList.remove("dark");
    localStorage.setItem("color-theme", "light");
  } else {
    document.documentElement.classList.add("dark");
    localStorage.setItem("color-theme", "dark");
  }

  // Dispatch a custom event to notify other parts of the application
  document.dispatchEvent(new Event("dark-mode"));
});
