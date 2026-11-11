
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

/* =====================================
   PROFILE DROPDOWN
===================================== */

document.addEventListener("DOMContentLoaded", function () {

    const profileMenus = document.querySelectorAll(
        "[data-profile-menu]"
    );

    profileMenus.forEach(function (menu) {

        const toggle = menu.querySelector(
            "[data-profile-toggle]"
        );

        const dropdown = menu.querySelector(
            ".profile-dropdown"
        );

        if (!toggle || !dropdown) {
            return;
        }

        function openDropdown() {
            dropdown.hidden = false;
            toggle.setAttribute("aria-expanded", "true");
        }

        function closeDropdown() {
            dropdown.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
        }

        toggle.addEventListener("click", function (event) {

            event.stopPropagation();

            if (dropdown.hidden) {
                openDropdown();
            } else {
                closeDropdown();
            }

        });

        document.addEventListener("click", function (event) {

            if (!menu.contains(event.target)) {
                closeDropdown();
            }

        });

        document.addEventListener("keydown", function (event) {

            if (event.key === "Escape") {
                closeDropdown();
                toggle.focus();
            }

        });

    });

});

/* ==========================================
   KNOWLEDGE HANDOVER
   WORKSPACE MODAL AND API INTEGRATION
========================================== */

document.addEventListener("DOMContentLoaded", function () {

    const createModal = document.getElementById("createWorkspaceModal");
    const joinModal = document.getElementById("joinWorkspaceModal");

    const createButton = document.getElementById("openCreateWorkspace");
    const joinButton = document.getElementById("openJoinWorkspace");

    const createForm = document.getElementById("createWorkspaceForm");

    const invitationContainer = document.getElementById("workspaceInvitations");

    const createMessage = document.getElementById("createWorkspaceMessage");
    const joinMessage = document.getElementById("joinWorkspaceMessage");

    if (!createModal || !joinModal || !createForm) {
        return;
    }

    // CSRF token
    function getCSRFToken() {

        const cookie = document.cookie
            .split("; ")
            .find(row => row.startsWith("csrftoken="));

        if (cookie) {
            return decodeURIComponent(cookie.split("=")[1]);
        }

        const hiddenToken = createForm.querySelector(
            '[name="csrfmiddlewaretoken"]'
        );

        return hiddenToken ? hiddenToken.value : "";
    }


    // Display API errors
    function getErrorMessage(data) {

        if (typeof data.detail === "string") {
            return data.detail;
        }

        return Object.entries(data)
            .map(([field, errors]) => {

                const message = Array.isArray(errors)
                    ? errors.join(", ")
                    : String(errors);

                return `${field}: ${message}`;

            })
            .join(" | ") || "Something went wrong. Please try again.";
    }


    // Common API request
    async function apiRequest(url, options = {}) {

        const headers = {
            "Accept": "application/json",
            ...options.headers
        };

        if (options.method && options.method !== "GET") {

            headers["Content-Type"] = "application/json";
            headers["X-CSRFToken"] = getCSRFToken();

        }

        const response = await fetch(url, {
            ...options,
            headers,
            credentials: "same-origin"
        });

        if (response.status === 204) {
            return null;
        }

        let data = {};

        try {
            data = await response.json();
        } catch {
            data = {};
        }

        if (!response.ok) {
            throw new Error(getErrorMessage(data));
        }

        return data;
    }


    // Feedback message
    function showMessage(element, message, type) {

        element.textContent = message;
        element.className = `kh-form-message ${type}`;

    }


    // Open modal
    function openModal(modal) {

        modal.hidden = false;
        document.body.style.overflow = "hidden";

    }


    // Close modal
    function closeModal(modal) {

        modal.hidden = true;
        document.body.style.overflow = "";

    }
    
        // ======================================
    // CREATE WORKSPACE
    // ======================================

    if (createButton) {

        createButton.addEventListener("click", function () {

            createForm.reset();

            createMessage.textContent = "";
            createMessage.className = "kh-form-message";

            openModal(createModal);

            document.getElementById("workspaceName").focus();

        });

    }


    createForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const submitButton = document.getElementById(
            "createWorkspaceSubmit"
        );

        const originalText = submitButton.textContent;

        const workspaceData = {

            name: document.getElementById("workspaceName").value.trim(),

            description: document.getElementById(
                "workspaceDescription"
            ).value.trim(),

            workspace_type: document.getElementById(
                "workspaceType"
            ).value

        };

        if (!workspaceData.name || !workspaceData.workspace_type) {

            showMessage(
                createMessage,
                "Please enter workspace name and select workspace type.",
                "error"
            );

            return;

        }

        submitButton.disabled = true;
        submitButton.textContent = "Creating...";

        try {

            const result = await apiRequest(
                "/api/v1/workspaces/",
                {
                    method: "POST",
                    body: JSON.stringify(workspaceData)
                }
            );

            showMessage(
                createMessage,
                `Workspace "${result.name}" created successfully!`,
                "success"
            );

            submitButton.textContent = "Created";

            // Refresh dashboard to load new workspace and counts
            setTimeout(function () {

                window.location.reload();

            }, 800);

        } catch (error) {

            showMessage(
                createMessage,
                error.message,
                "error"
            );

            submitButton.disabled = false;
            submitButton.textContent = originalText;

        }

    });

    // ======================================
    // JOIN WORKSPACE
    // ======================================

    if (joinButton) {

        joinButton.addEventListener("click", function () {

            joinMessage.textContent = "";
            joinMessage.className = "kh-form-message";

            openModal(joinModal);

            loadInvitations();

        });

    }


    // Empty state
    function showEmptyInvitations(message) {

        invitationContainer.replaceChildren();

        const paragraph = document.createElement("p");
        paragraph.textContent = message;

        invitationContainer.appendChild(paragraph);

    }


    // Load pending invitations
    async function loadInvitations() {

        showEmptyInvitations("Loading invitations...");

        try {

            const invitations = await apiRequest(
                "/api/v1/invitations/"
            );

            invitationContainer.replaceChildren();

            if (!Array.isArray(invitations) || invitations.length === 0) {

                showEmptyInvitations(
                    "No pending workspace invitations found for your account."
                );

                return;

            }

            invitations.forEach(function (invitation) {

                const card = document.createElement("div");
                card.className = "kh-invitation-card";

                const title = document.createElement("strong");
                title.textContent = invitation.workspace_name;

                const invitedBy = document.createElement("p");

                invitedBy.textContent =
                    `Invited by: ${invitation.invited_by_username || "Workspace Owner"}`;

                const role = document.createElement("p");

                role.textContent =
                    `Your role: ${invitation.invited_role}`;

                const expiry = document.createElement("p");

                expiry.textContent =
                    `Expires: ${new Date(invitation.expires_at).toLocaleDateString()}`;

                const actions = document.createElement("div");
                actions.className = "kh-invitation-actions";

                const acceptButton = document.createElement("button");
                acceptButton.type = "button";
                acceptButton.textContent = "Accept";
                acceptButton.dataset.action = "accept";
                acceptButton.dataset.token = invitation.token;

                const declineButton = document.createElement("button");
                declineButton.type = "button";
                declineButton.textContent = "Decline";
                declineButton.dataset.action = "decline";
                declineButton.dataset.token = invitation.token;

                actions.appendChild(acceptButton);
                actions.appendChild(declineButton);

                card.appendChild(title);
                card.appendChild(invitedBy);
                card.appendChild(role);
                card.appendChild(expiry);
                card.appendChild(actions);

                invitationContainer.appendChild(card);

            });

        } catch (error) {

            showEmptyInvitations(
                `Could not load invitations: ${error.message}`
            );

        }

    }


    // Accept or decline invitation
    invitationContainer.addEventListener("click", async function (event) {

        const button = event.target.closest("button[data-action]");

        if (!button) {
            return;
        }

        const token = button.dataset.token;
        const action = button.dataset.action;

        if (!token) {
            return;
        }

        const buttons = button.parentElement.querySelectorAll("button");

        buttons.forEach(item => {
            item.disabled = true;
        });

        button.textContent = "Processing...";

        const endpoint =
            `/api/v1/invitations/${encodeURIComponent(token)}/${action}/`;

        try {

            await apiRequest(endpoint, {
                method: "POST",
                body: JSON.stringify({})
            });

            showMessage(
                joinMessage,
                action === "accept"
                    ? "Invitation accepted successfully!"
                    : "Invitation declined successfully.",
                "success"
            );

            setTimeout(function () {

                window.location.reload();

            }, 800);

        } catch (error) {

            showMessage(
                joinMessage,
                error.message,
                "error"
            );

            buttons.forEach(item => {
                item.disabled = false;
            });

            button.textContent =
                action === "accept" ? "Accept" : "Decline";

        }

    });

    // ======================================
    // MODAL CLOSE AND ESCAPE
    // ======================================

    document.querySelectorAll("[data-close-modal]").forEach(
        function (button) {

            button.addEventListener("click", function () {

                const modalId = button.dataset.closeModal;
                const modal = document.getElementById(modalId);

                if (modal) {
                    closeModal(modal);
                }

            });

        }
    );


    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {

            if (!createModal.hidden) {
                closeModal(createModal);
            }

            if (!joinModal.hidden) {
                closeModal(joinModal);
            }

        }

    });

});