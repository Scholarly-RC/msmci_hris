// Function to toggle Password Visibility
const togglePasswordVisibility = (content) => {
    const toggleCurrentPasswordButton = content.querySelector("#toggle_current_password_visibility");
    const currentPasswordInput = content.querySelector("#current_password");
    const toggleNewPasswordButton = content.querySelector("#toggle_new_password_visibility");
    const newPasswordInput = content.querySelector("#new_password");
    const toggleConfirmPasswordButton = content.querySelector("#toggle_confirm_password_visibility");
    const confirmPasswordInput = content.querySelector("#confirm_password");
        
    function updateIconVisibility(input, button) {
        const isPassword = input.type === "password";
        button.querySelector('svg:nth-child(1)').classList.toggle("hidden", !isPassword);
        button.querySelector('svg:nth-child(2)').classList.toggle("hidden", isPassword);
    }

    [toggleCurrentPasswordButton, toggleNewPasswordButton, toggleConfirmPasswordButton].forEach((button, index) => {
        if (button) {
            button.addEventListener("click", function () {
                const input = index === 0 ? currentPasswordInput : index === 1 ? newPasswordInput : confirmPasswordInput;
                input.type = input.type === "password" ? "text" : "password";
                updateIconVisibility(input, button);
            });
            updateIconVisibility(index === 0 ? currentPasswordInput : index === 1 ? newPasswordInput : confirmPasswordInput, button);
        }
    });
};

htmx.onLoad(function (content) {
    togglePasswordVisibility(content);
})