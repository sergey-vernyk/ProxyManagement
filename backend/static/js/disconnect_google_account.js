import checkOpenedModalWindows from "./check_opened_modal_windows.js"
import getCookie from "./get_cookies.js"


$(document).ready(() => {
    const googleDisconnectUrl = $("#google-disconnect").attr("href");
    const googleModal = $("#google-disconnect-modal");
    const closeGoogleModalBtn = $("#google-disconnect-close");
    const confirmDisconnectInput = $("#confirm-disconnect-input");
    const confirmDisconnectBtn = $("#confirm-disconnect-btn");
    const modalWindows = $("[id$='modal']").toArray()
    const csrfToken = getCookie("csrftoken");

    // Show the modal when clicking "Disconnect from Google"
    $("#google-disconnect").on("click", (event) => {
        event.preventDefault();
        if (!checkOpenedModalWindows(modalWindows)) {
            googleModal.show();
        }
    });

    // Close the modal when the close button is clicked
    closeGoogleModalBtn.on("click", () => {
        googleModal.hide();
    });

    // Enable the disconnect button only if the input is "disconnect"
    confirmDisconnectInput.on("input", () => {
        const inputVal = confirmDisconnectInput.val().toLowerCase();
        confirmDisconnectBtn.prop("disabled", inputVal !== "disconnect");
    });

    // Handle disconnecting the Google account
    confirmDisconnectBtn.on("click", () => {
        $.ajax({
            url: googleDisconnectUrl,
            method: "POST",
            headers: { "X-CSRFToken": csrfToken },
            success: (response) => {
                console.log("Disconnected");
                window.location.reload();
            },
            error: (jqXHR, textStatus, errorThrown) => {
                console.log(errorThrown);
            }
        });
    });
})