$(document).ready(() => {
    $("#google-oauth").on("click", () => {
        const googleAuthUrl = $("#registration-form").data("oauth-google-url");
        window.location.href = googleAuthUrl;
    });

    $("#registration-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const enteredPassword = $("#password").val();
        const regUrl = $("#registration-form").data("reg-url");
        $("#password-error").text("");
        $("#email-error").text("");

        $.ajax({
            url: regUrl,
            method: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                email: enteredEmail,
                password: enteredPassword,
            }),
            success: (response, textStatus, xhr) => {
                // redirect to page with text about successful registration.
                const redirectUrl = response.redirect_url;
                window.location.href = redirectUrl;
            },
            error: (jqXHR, textStatus, errorThrown) => {
                if (jqXHR.status === 422) {
                    $("#password-error").text(`${jqXHR.responseJSON.detail[0].msg}.`);
                }

                if (jqXHR.status === 400) {
                    if (jqXHR.responseJSON.detail["email_invalid"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["email_invalid"])
                    }

                    if (jqXHR.responseJSON.detail["user_exists"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["user_exists"])
                    }
                }
            }
        });
    })
})