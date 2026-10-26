const menuToggle = document.getElementById("menuToggle");
const mainNav = document.getElementById("mainNav");
const installButton = document.getElementById("installButton");
const accountMessage = document.getElementById("accountMessage");
const accountInfoButton = document.getElementById("accountInfoButton");

document.getElementById("year").textContent = new Date().getFullYear();

// Supabase client is created in supabase-config.js.
const db = window.supabaseClient;

let currentAuthMode = "signup";
let authLinkCreatedByApp = false;

// Navigation menu
if (menuToggle && mainNav) {
menuToggle.addEventListener("click", () => {
const isOpen = mainNav.classList.toggle("open");
menuToggle.setAttribute("aria-expanded", String(isOpen));
});

mainNav.querySelectorAll("a").forEach(link => {
link.addEventListener("click", () => {
mainNav.classList.remove("open");
menuToggle.setAttribute("aria-expanded", "false");
});
});
}

document.querySelectorAll(".nav-link").forEach(link => {
link.addEventListener("click", () => {
document.querySelectorAll(".nav-link").forEach(item => {
item.classList.remove("active");
});
link.classList.add("active");
});
});

// Marketplace search placeholder
const searchButton = document.getElementById("searchButton");
const marketSearch = document.getElementById("marketSearch");
const marketMessage = document.getElementById("marketMessage");

if (searchButton && marketSearch && marketMessage) {
searchButton.addEventListener("click", () => {
const query = marketSearch.value.trim();

marketMessage.replaceChildren();

const symbol = document.createElement("div");
symbol.className = "empty-symbol";
symbol.textContent = "◇";

const heading = document.createElement("h3");
heading.textContent = query
  ? "Marketplace connection needed"
  : "Your marketplace starts here";

const paragraph = document.createElement("p");
paragraph.textContent = query
  ? "Product search will become available when public product listings are connected."
  : "Product listings will appear here once the public marketplace is connected.";

marketMessage.append(symbol, heading, paragraph);

});

marketSearch.addEventListener("keydown", event => {
if (event.key === "Enter") {
searchButton.click();
}
});
}

// Display a message safely.
function showAccountMessage(message, type = "") {
if (!accountMessage) return;

accountMessage.replaceChildren();
accountMessage.className = "account-message";

if (type) {
accountMessage.dataset.type = type;
} else {
delete accountMessage.dataset.type;
}

accountMessage.textContent = message;
}

// Account registration and sign-in form
function showAccountForm(mode = "signup") {
currentAuthMode = mode;

if (!accountMessage || !accountInfoButton) return;

accountInfoButton.textContent = "Back to account options";
accountInfoButton.hidden = false;

accountMessage.replaceChildren();
accountMessage.className = "account-message";
delete accountMessage.dataset.type;

const form = document.createElement("form");
form.id = "authForm";
form.className = "account-form";

const heading = document.createElement("h3");
heading.textContent = mode === "signup"
? "Create your OLYNTAQ account"
: "Sign in to OLYNTAQ";

const emailLabel = document.createElement("label");
emailLabel.htmlFor = "authEmail";
emailLabel.textContent = "Email address";

const email = document.createElement("input");
email.id = "authEmail";
email.name = "email";
email.type = "email";
email.autocomplete = "email";
email.placeholder = "you@example.com";
email.required = true;

const passwordLabel = document.createElement("label");
passwordLabel.htmlFor = "authPassword";
passwordLabel.textContent = "Password";

const password = document.createElement("input");
password.id = "authPassword";
password.name = "password";
password.type = "password";
password.autocomplete = mode === "signup"
? "new-password"
: "current-password";
password.placeholder = mode === "signup"
? "At least 8 characters"
: "Enter your password";
password.minLength = mode === "signup" ? 8 : 1;
password.required = true;

const submit = document.createElement("button");
submit.type = "submit";
submit.className = "button button-primary button-large account-submit";
submit.textContent = mode === "signup"
? "Create account"
: "Sign in";

const switchButton = document.createElement("button");
switchButton.type = "button";
switchButton.className = "button button-ghost";
switchButton.textContent = mode === "signup"
? "Already have an account? Sign in"
: "New here? Create an account";

switchButton.addEventListener("click", () => {
showAccountForm(mode === "signup" ? "signin" : "signup");
});

const status = document.createElement("p");
status.id = "authStatus";
status.className = "account-message";
status.setAttribute("role", "status");
status.setAttribute("aria-live", "polite");

form.append(
heading,
emailLabel,
email,
passwordLabel,
password,
submit,
switchButton,
status
);

accountMessage.appendChild(form);

form.addEventListener("submit", async event => {
event.preventDefault();

if (!db || !db.auth) {
  status.textContent =
    "Supabase is not configured. Check supabase-config.js and reload the website.";
  status.dataset.type = "error";
  return;
}

submit.disabled = true;
status.textContent = "Please wait...";
delete status.dataset.type;

try {
  const emailValue = email.value.trim();
  const passwordValue = password.value;

  let result;

  if (mode === "signup") {
    result = await db.auth.signUp({
      email: emailValue,
      password: passwordValue
    });

    if (result.error) throw result.error;

    if (result.data.session) {
      status.textContent =
        "Your account has been created and you are signed in.";
      status.dataset.type = "success";
    } else {
      status.textContent =
        "Registration received. Check your email for a confirmation link before signing in.";
      status.dataset.type = "success";
    }
  } else {
    result = await db.auth.signInWithPassword({
      email: emailValue,
      password: passwordValue
    });

    if (result.error) throw result.error;

    status.textContent = "Signed in successfully.";
    status.dataset.type = "success";
  }
} catch (error) {
  console.error("Account error:", error);

  status.textContent = error.message ||
    "We could not complete that request. Please try again.";
  status.dataset.type = "error";
} finally {
  submit.disabled = false;
}

});
}

// Main account button
if (accountInfoButton && accountMessage) {
accountInfoButton.addEventListener("click", () => {
if (accountMessage.querySelector("#authForm")) {
accountMessage.replaceChildren();
accountMessage.className = "account-message";
delete accountMessage.dataset.type;
accountInfoButton.textContent = "Continue to account setup";
} else {
showAccountForm("signup");
}
});
}

// Find the existing Sign in navigation link instead of adding duplicates.
function getAuthNavigationLink() {
let link = mainNav?.querySelector("#authNavLink");

if (link) return link;

const links = mainNav
? Array.from(mainNav.querySelectorAll("a"))
: [];

link = links.find(item =>
item.textContent.trim().toLowerCase() === "sign in"
);

if (link) {
link.id = "authNavLink";
return link;
}

if (!mainNav) return null;

link = document.createElement("a");
link.id = "authNavLink";
link.className = "button button-primary";
link.href = "#account";
mainNav.appendChild(link);
authLinkCreatedByApp = true;

return link;
}

// Update the navigation using the provided session when available.
async function updateAuthNavigation(session) {
if (!db || !db.auth || !mainNav) return;

let activeSession = session;

// Fetch the session only during initial setup.
if (typeof activeSession === "undefined") {
const { data, error } = await db.auth.getSession();

if (error) {
  console.error("Could not check session:", error);
  return;
}

activeSession = data.session;

}

let authLink = getAuthNavigationLink();
if (!authLink) return;

// Replace the link to remove old click handlers.
const replacement = authLink.cloneNode(true);
authLink.replaceWith(replacement);
authLink = replacement;

authLink.className = activeSession
? "button button-primary"
: "nav-link";

authLink.textContent = activeSession ? "Sign out" : "Sign in";
authLink.href = "#account";

authLink.addEventListener("click", async event => {
event.preventDefault();

mainNav.classList.remove("open");
menuToggle?.setAttribute("aria-expanded", "false");

if (activeSession) {
  const { error } = await db.auth.signOut();

  if (error) {
    showAccountMessage(
      "Sign out failed: " + error.message,
      "error"
    );
  } else {
    showAccountMessage("You have signed out.", "success");
  }
} else {
  showAccountForm("signin");

  document.getElementById("account")?.scrollIntoView({
    behavior: "smooth"
  });
}

});
}

// Installable PWA
let installPrompt = null;

if (installButton) {
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
}

// Register service worker
if ("serviceWorker" in navigator && location.protocol !== "file:") {
window.addEventListener("load", async () => {
try {
await navigator.serviceWorker.register("./sw.js");
} catch (error) {
console.error("Service worker registration failed:", error);
}
});
}

// Initialize authentication
if (db && db.auth) {
updateAuthNavigation();

db.auth.onAuthStateChange((_event, session) => {
// Use the supplied session; don't call getSession() from this callback.
updateAuthNavigation(session);
});
} else {
console.error(
"Supabase client not found. Check that the Supabase library and supabase-config.js load before app.js."
);
showAccountMessage(
"The account service could not load. Please check the website configuration and reload.",
"error"
);
  }
