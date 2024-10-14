$(document).ready(() => {
    $("#new-password-form").on("submit", (event) => {
        event.preventDefault();
        const newPassword = $("#new-password").val();
        const confirmPassword = $("#confirm-password").val();
        const resetConfirmUrl = $("#new-password-form").data("reset-confirm-url");
        const uid = $("#uid").val();
        const token = $("#token").val();

        $.ajax({
            url: resetConfirmUrl,
            method: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                new_password: newPassword,
                confirm_password: confirmPassword,
                uid: uid,
                token: token,
            }),
            success: (response, textStatus, xhr) => {
                $("#new-password-error").text("");
                $("#confirm-password-error").text("");
                $("#reset-success").text(response);
            },
            error: (jqXHR, textStatus, errorThrown) => {
                $("#new-password-error").text("");
                $("#confirm-password-error").text("");

                if (jqXHR.status === 422) {
                    const errors = jqXHR.responseJSON.detail;

                    // iterate over the errors and display messages
                    errors.forEach(error => {
                        const field = error.loc[1]; // get the field name
                        const message = error.msg;  // get the error message

                        if (field === "new_password") {
                            $("#new-password-error").text(`${message}.`);
                        } else if (field === "confirm_password") {
                            $("#confirm-password-error").text(`${message}.`);
                        }
                    });
                } else {
                    // Display a general error message for other status codes
                    $("#confirm-password-error").text(jqXHR.responseJSON.detail);
                }
            }
        });
    });
});
