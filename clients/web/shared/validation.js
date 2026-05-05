export function getEmailError(email) {
  if (!email) return "Email is required";
  if (!email.includes("@")) return "Email looks invalid";
  return "";
}

export function getPasswordError(password) {
  if (!password) return "Password is required";
  return "";
}

export function getUsernameError(username) {
  if (!username) return "Username is required";
  if (username.length < 1 || username.length > 32) {
    return "Username must be between 1 and 32 characters";
  }
  return "";
}
