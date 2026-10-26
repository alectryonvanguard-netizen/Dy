
const menuToggle = document.getElementById("menuToggle");
const mainNav = document.getElementById("mainNav");
const installButton = document.getElementById("installButton");
const accountMessage = document.getElementById("accountMessage");

document.getElementById("year").textContent = new Date().getFullYear();

menuToggle.addEventListener("click", () => {
  const isOpen = mainNav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
});

document.querySelectorAll("#mainNav a").forEach(link => {
  link.addEventListener("click", () => {
    mainNav.classList.remove("open");
    menuToggle.setAttribute("aria-expanded", "false");
  });
});

document.querySelectorAll(".nav-link").forEach(link => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-link").forEach(item => item.classList.remove("active"));
    link.classList.add("active");
  });
});

document.getElementById("searchButton").addEventListener("click", () => {
  const query = document.getElementById("marketSearch").value.trim();
  const message = document.getElementById("marketMessage");

  message.innerHTML = `
    <div class="empty-symbol">◇</div>
    <h3>${query ? "Marketplace connection needed" : "Your marketplace starts here"}</h3>
    <p>${query
      ? "Search is ready for the marketplace interface. Product search will work after public listings are connected."
      : "Product listings will appear here once the public marketplace is connected."}</p>
  `;
});

document.getElementById("marketSearch").addEventListener("keydown", event => {
  if (event.key === "Enter") document.getElementById("searchButton").click();
});

document.getElementById("accountInfoButton").addEventListener("click", () => {
  accountMessage.textContent =
    "Account creation is the next step. Your Supabase project will be connected before real accounts are enabled.";
});

let installPrompt = null;

window.addEventListener("beforeinstallprompt", event => {
  event.preventDefault();
  installPrompt = event;
  installButton.classList.remove("hidden");
});

installButton.addEventListener("click", async () => {
  if (!installPrompt) return;
  installPrompt.prompt();
  await installPrompt.userChoice;
  installPrompt = null;
  installButton.classList.add("hidden");
});

window.addEventListener("appinstalled", () => {
  installButton.classList.add("hidden");
});

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  window.addEventListener("load", async () => {
    try {
      await navigator.serviceWorker.register("./sw.js");
    } catch (error) {
      console.error("Service worker registration failed:", error);
    }
  });
}
