
document.addEventListener("DOMContentLoaded", function () {

    const buttons = document.querySelectorAll(".filter-btn");
    const cards = document.querySelectorAll(".project-card");

    buttons.forEach(function (button) {

        button.addEventListener("click", function () {

            buttons.forEach(function (btn) {
                btn.classList.remove("active");
            });

            button.classList.add("active");

            const filter = button.dataset.filter;

            cards.forEach(function (card) {

                const status = card.dataset.status;

                if (filter === "all" || filter === status) {
                    card.style.display = "";
                } else {
                    card.style.display = "none";
                }

            });

        });

    });

});



// ## for setting ke liye##


document.addEventListener("DOMContentLoaded", function () {

    const tabs = document.querySelectorAll(".settings-tab");
    const panels = document.querySelectorAll(".settings-panel");

    tabs.forEach(function (tab) {

        tab.addEventListener("click", function () {

            // Sabhi tabs se active class remove
            tabs.forEach(function (item) {
                item.classList.remove("active");
            });

            // Click kiye gaye tab ko active karo
            tab.classList.add("active");

            // Click kiye gaye tab ki ID
            const selectedTab = tab.dataset.tab;

            // Sabhi panels hide karo
            panels.forEach(function (panel) {
                panel.hidden = true;
            });

            // Selected panel show karo
            const selectedPanel = document.getElementById(selectedTab);

            if (selectedPanel) {
                selectedPanel.hidden = false;
            }

        });

    });

});









document.addEventListener("DOMContentLoaded", function () {


    
    // 1. SIDEBAR TOGGLE
    

    const dashboard = document.getElementById("dashboard");
    const menuToggle = document.getElementById("menuToggle");

    if (dashboard && menuToggle) {

        menuToggle.addEventListener("click", function () {

            const isCollapsed =
                dashboard.classList.toggle("sidebar-collapsed");

            menuToggle.setAttribute(
                "aria-expanded",
                String(!isCollapsed)
            );

            menuToggle.setAttribute(
                "aria-label",
                isCollapsed ? "Show sidebar" : "Hide sidebar"
            );

        });

    }



    
    // 2. SETTINGS TAB SWITCHING
    

    const settingsPage = document.querySelector("[data-settings-page]");

    if (!settingsPage) {
        return;
    }

    const tabs = settingsPage.querySelectorAll(".settings-tab");
    const panels = settingsPage.querySelectorAll(".settings-panel");


    function activateTab(selectedTab, moveFocus = false) {

        const selectedName = selectedTab.dataset.tab;

        // Remove active state from every tab
        tabs.forEach(function (tab) {

            const isActive = tab === selectedTab;

            tab.classList.toggle("active", isActive);

            tab.setAttribute(
                "aria-selected",
                String(isActive)
            );

            tab.setAttribute(
                "tabindex",
                isActive ? "0" : "-1"
            );

        });


        // Hide all settings panels
        panels.forEach(function (panel) {

            panel.hidden = true;

            panel.classList.remove("active");

        });


        // Show selected panel
        const selectedPanel = settingsPage.querySelector(
            '[data-panel="' + selectedName + '"]'
        );

        if (selectedPanel) {

            selectedPanel.hidden = false;

            selectedPanel.classList.add("active");

            if (moveFocus) {
                selectedPanel.focus();
            }

        }

        if (moveFocus) {
            selectedTab.focus();
        }

    }


    // Tab click
    tabs.forEach(function (tab) {

        tab.addEventListener("click", function () {

            activateTab(tab);

        });


        // Keyboard navigation
        tab.addEventListener("keydown", function (event) {

            const tabArray = Array.from(tabs);

            const currentIndex = tabArray.indexOf(tab);

            let nextIndex = currentIndex;

            if (event.key === "ArrowDown" ||
                event.key === "ArrowRight") {

                nextIndex = (currentIndex + 1) % tabArray.length;

            }

            else if (event.key === "ArrowUp" ||
                     event.key === "ArrowLeft") {

                nextIndex =
                    (currentIndex - 1 + tabArray.length) %
                    tabArray.length;

            }

            else if (event.key === "Home") {

                nextIndex = 0;

            }

            else if (event.key === "End") {

                nextIndex = tabArray.length - 1;

            }

            else {
                return;
            }

            event.preventDefault();

            activateTab(tabArray[nextIndex], false);

            tabArray[nextIndex].focus();

        });

    });



    
    // 3. FEEDBACK MESSAGE
    

    function showFeedback(form, message, type = "success") {

        const feedback = form.querySelector("[data-feedback]");

        if (!feedback) {
            return;
        }

        feedback.textContent = message;

        feedback.classList.remove(
            "feedback-success",
            "feedback-error"
        );

        feedback.classList.add(
            type === "error"
                ? "feedback-error"
                : "feedback-success"
        );

    }



    
    // 4. PROFILE PHOTO PREVIEW
    

    const photoInput =
        document.getElementById("profilePhotoInput");

    const photoPreview =
        document.getElementById("profilePhotoPreview");

    const avatarInitials =
        document.getElementById("avatarInitials");


    if (photoInput && photoPreview) {

        photoInput.addEventListener("change", function () {

            const file = photoInput.files[0];

            if (!file) {
                return;
            }


            // Check file type
            const allowedTypes = [
                "image/jpeg",
                "image/png",
                "image/webp"
            ];

            if (!allowedTypes.includes(file.type)) {

                alert("Please select a JPG, PNG or WEBP image.");

                photoInput.value = "";

                return;
            }


            // Check file size (5 MB)
            if (file.size > 5 * 1024 * 1024) {

                alert("Image size must be less than 5 MB.");

                photoInput.value = "";

                return;
            }


            // Preview uploaded image
            const reader = new FileReader();

            reader.onload = function (event) {

                photoPreview.src = event.target.result;

                photoPreview.hidden = false;

                if (avatarInitials) {
                    avatarInitials.hidden = true;
                }

            };

            reader.readAsDataURL(file);

        });

    }



    
    // 5. UPDATE PROFILE INITIALS
    

    const firstNameInput =
        document.getElementById("firstName");

    const lastNameInput =
        document.getElementById("lastName");


    function updateInitials() {

        if (!avatarInitials) {
            return;
        }

        const firstName =
            firstNameInput?.value.trim() || "";

        const lastName =
            lastNameInput?.value.trim() || "";

        const initials =
            (firstName.charAt(0) + lastName.charAt(0)).toUpperCase();

        if (!photoPreview || photoPreview.hidden) {
            avatarInitials.textContent = initials || "M";
        }

    }


    firstNameInput?.addEventListener("input", updateInitials);

    lastNameInput?.addEventListener("input", updateInitials);



    
    // 6. PASSWORD CONFIRMATION
    

    const newPassword =
        document.getElementById("newPassword");

    const confirmPassword =
        document.getElementById("confirmPassword");


    function validatePasswordMatch() {

        if (!newPassword || !confirmPassword) {
            return;
        }

        if (
            confirmPassword.value &&
            newPassword.value !== confirmPassword.value
        ) {

            confirmPassword.setCustomValidity(
                "Passwords do not match."
            );

        } else {

            confirmPassword.setCustomValidity("");

        }

    }


    newPassword?.addEventListener(
        "input",
        validatePasswordMatch
    );

    confirmPassword?.addEventListener(
        "input",
        validatePasswordMatch
    );



    
// ##SETTINGS FORm SUBMISSION
    

    const settingsForms =
        settingsPage.querySelectorAll("[data-settings-form]");


    settingsForms.forEach(function (form) {

        form.addEventListener("submit", function (event) {

            event.preventDefault();


            // Check browser form validation
            if (!form.checkValidity()) {

                form.reportValidity();

                return;
            }


            const formType = form.dataset.settingsForm;


            // Security form extra validation
            if (formType === "security") {

                if (newPassword.value ===
                    document.getElementById("currentPassword").value) {

                    showFeedback(
                        form,
                        "New password must be different from current password.",
                        "error"
                    );

                    return;

                }

                if (newPassword.value !== confirmPassword.value) {

                    showFeedback(
                        form,
                        "New password and confirm password do not match.",
                        "error"
                    );

                    return;

                }

            }


            // Demo feedback messages
            const messages = {

                profile:
                    "Profile form is working. Connect the backend to save your details.",

                account:
                    "Account form is working. Connect the backend to save your preferences.",

                notifications:
                    "Notification preferences selected. Backend is required to save them.",

                appearance:
                    "Appearance preferences selected. Backend is required to save them.",

                security:
                    "Password validation successful. Connect the backend to update your password.",

                workspace:
                    "Workspace form is working. Connect the backend to save your changes."

            };


            showFeedback(
                form,
                messages[formType] || "Form submitted successfully."
            );

        });

    });


});

