async function logout() {
  const res = await fetch("/api/logout", {method:"POST"});
  const data = await res.json();
  if (data.redirect) window.location.href = data.redirect;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}
