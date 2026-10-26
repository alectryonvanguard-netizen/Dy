
const menuToggle = document.getElementById("menuToggle");
const mainNav = document.getElementById("mainNav");
const installButton = document.getElementById("installButton");
const accountMessage = document.getElementById("accountMessage");
const accountInfoButton = document.getElementById("accountInfoButton");

document.getElementById("year").textContent = new Date().getFullYear();

// Supabase client is created in supabase-config.js.
const db = window.supabaseClient;

let currentAuthMode = "signup";

// Navigation menu
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
    document.querySelectorAll(".nav-link").forEach(item => {
      item.classList.remove("active");
    });
    link.classList.add("active");
  });
});

// Marketplace search placeholder
document.getElementById("searchButton").addEventListener("click", () => {
  const query = document.getElementById("marketSearch").value.trim();
  const message = document.getElementById("marketMessage");

  message.replaceChildren();

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

  message.append(symbol, heading, paragraph);
});

document.getElementById("marketSearch").addEventListener("keydown", event => {
  if (event.key === "Enter") {
    document.getElementById("searchButton").click();
  }
});

// Account form
function showAccountForm(mode = "signup") {
  currentAuthMode = mode;

  accountInfoButton.textContent = "Back to account options";
  accountInfoButton.hidden = false;

  accountMessage.replaceChildren();
  accountMessage.className = "account-message";

  const form = document.createElement("form");
  form.id = "authForm";

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
  email.autocomplete = mode === "signup" ? "email" : "username";
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
  submit.className = "button button-primary button-large";
  submit.textContent = mode === "signup" ? "Create account" : "Sign in";

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

    if (!db) {
      status.textContent =
        "Supabase is not configured. Check supabase-config.js and reload the website.";
      return;
    }

    submit.disabled = true;
    status.textContent = "Please wait...";

    try {
      const emailValue = email.value.trim();
      const passwordValue = password.value;

      let result;

      if (currentAuthMode === "signup") {
        result = await db.auth.signUp({
          email: emailValue,
          password: passwordValue
        });

        if (result.error) throw result.error;

        if (result.data.session) {
          status.textContent =
            "Your account has been created and you are signed in.";
        } else {
          status.textContent =
            "Registration received. Check your email for a confirmation link before signing in.";
        }
      } else {
        result = await db.auth.signInWithPassword({
          email: emailValue,
          password: passwordValue
        });

        if (result.error) throw result.error;

        status.textContent = "Signed in successfully.";
      }

      await updateAuthNavigation();
    } catch (error) {
      console.error("Account error:", error);

      status.textContent = error.message ||
        "We could not complete that request. Please try again.";
    } finally {
      submit.disabled = false;
    }
  });
}

// Show account form when the main account button is pressed.
accountInfoButton.addEventListener("click", () => {
  if (accountMessage.querySelector("#authForm")) {
    accountMessage.replaceChildren();
    accountInfoButton.textContent = "Continue to account setup";
  } else {
    showAccountForm("signup");
  }
});

// Update navigation when signed in.
async function updateAuthNavigation() {
  if (!db) return;

  const { data, error } = await db.auth.getSession();

  if (error) {
    console.error("Could not check session:", error);
    return;
  }

  const existingAuthLink = mainNav.querySelector("#authNavLink");

  if (existingAuthLink) existingAuthLink.remove();

  const authLink = document.createElement("a");
  authLink.id = "authNavLink";
  authLink.className = "button button-primary";

  if (data.session) {
    authLink.href = "#account";
    authLink.textContent = "Sign out";

    authLink.addEventListener("click", async event => {
      event.preventDefault();

      const { error: signOutError } = await db.auth.signOut();

      if (signOutError) {
        accountMessage.textContent = signOutError.message;
        return;
      }

      accountMessage.textContent = "You have signed out.";
      await updateAuthNavigation();
    });
  } else {
    authLink.href = "#account";
    authLink.textContent = "Sign in";

    authLink.addEventListener("click", event => {
      event.preventDefault();
      showAccountForm("signin");
      document.getElementById("account").scrollIntoView({
        behavior: "smooth"
      });
    });
  }

  mainNav.appendChild(authLink);
}

// Installable PWA
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
if (db) {
  updateAuthNavigation();

  db.auth.onAuthStateChange(() => {
    updateAuthNavigation();
  });
} else {
  console.error(
    "Supabase client not found. Check supabase-config.js."
  );
}
