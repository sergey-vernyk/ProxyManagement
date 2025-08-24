import checkOpenedModalWindows from "./check_opened_modal_windows.js"
import getCookie from "./get_cookies.js"


$(document).ready(() => {
    const deleteAccountUrl = $("#delete-account").attr("href");
    const modal = $("#delete-account-modal");
    const closeBtn = $(".close");
    const confirmInput = $("#confirm-delete-input");
    const confirmDeleteBtn = $("#confirm-delete-btn");
    const modalWindows = $("[id$='modal']").toArray()
    const csrfToken = getCookie("csrftoken");

    // Show the modal when clicking "Delete account"
    $("#delete-account").on("click", (event) => {
        event.preventDefault();
        if (!checkOpenedModalWindows(modalWindows)) {
            modal.show();
            confirmDeleteBtn.prop("disabled", true);
        }
    });

    // Close the modal
    closeBtn.on("click", () => {
        modal.hide();
    });

    // Enable the delete button only if the input is "delete"
    confirmInput.on("input", () => {
        const inputVal = confirmInput.val().toLowerCase();
        confirmDeleteBtn.prop("disabled", inputVal !== "delete");
    });

    // Handle account deletion
    confirmDeleteBtn.on("click", (event) => {
        event.preventDefault();
        const inputVal = confirmInput.val().toLowerCase();
        if (inputVal === "delete") {
            $.ajax({
                url: deleteAccountUrl,
                method: "DELETE",
                headers: { "X-CSRFToken": csrfToken },
                success: (response, textStatus, xhr) => {
                    window.location.href = response.redirect_url;
                },
                error: (jqXHR, textStatus, errorThrown) => {
                    console.log(errorThrown);
                }
            });
        } else {
            confirmDeleteBtn.prop("disabled", true);
        }
    });
});