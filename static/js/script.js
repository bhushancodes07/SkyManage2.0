const togglePassword = document.getElementById("togglePassword");
const password = document.getElementById("password");

if (togglePassword && password) {

    togglePassword.addEventListener("click", function () {

        if (password.type === "password") {
            password.type = "text";
            togglePassword.textContent = "Hide";
        } else {
            password.type = "password";
            togglePassword.textContent = "Show";
        }

    });

}


const toggleRegisterPassword = document.getElementById("toggleRegisterPassword");
const registerPassword = document.getElementById("password");

if (toggleRegisterPassword && registerPassword) {

    toggleRegisterPassword.addEventListener("click", function () {

        if (registerPassword.type === "password") {
            registerPassword.type = "text";
            toggleRegisterPassword.textContent = "Hide";
        } else {
            registerPassword.type = "password";
            toggleRegisterPassword.textContent = "Show";
        }

    });

}


const toggleConfirmPassword = document.getElementById("toggleConfirmPassword");
const confirmPassword = document.getElementById("confirm_password");

if (toggleConfirmPassword && confirmPassword) {

    toggleConfirmPassword.addEventListener("click", function () {

        if (confirmPassword.type === "password") {
            confirmPassword.type = "text";
            toggleConfirmPassword.textContent = "Hide";
        } else {
            confirmPassword.type = "password";
            toggleConfirmPassword.textContent = "Show";
        }

    });

}