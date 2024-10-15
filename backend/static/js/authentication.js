$(document).ready(() => {
    $("#google-oauth").on("click", () => {
        const googleLoginUrl = $("#authentication-form").data("google-login-url");
        window.location.href = googleLoginUrl;
    });

    $("#authentication-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const enteredPassword = $("#password").val();
        const basicLoginUrl = $("#authentication-form").data("basic-login-url");
        $("#password-error").text("");
        $("#email-error").text("");

        $.ajax({
            url: basicLoginUrl,
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data: new URLSearchParams({
                "email": enteredEmail,
                "password": enteredPassword,
            }).toString(),
            success: (response, textStatus, xhr) => {
                console.log(textStatus);
            },
            error: (jqXHR, textStatus, errorThrown) => {
                if (jqXHR.status === 422) {
                    $("#password-error").text(`${jqXHR.responseJSON.detail[0].msg}.`);
                }

                if (jqXHR.status === 400) {
                    if (jqXHR.responseJSON.detail["email_invalid"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["email_invalid"])
                    }

                    if (jqXHR.responseJSON.detail["user_not_exists"] !== undefined) {
                        $("#email-error").text(jqXHR.responseJSON.detail["user_not_exists"])
                    }

                    if (jqXHR.responseJSON.detail["incorrect_email_or_password"] !== undefined) {
                        $("#password-error").text(jqXHR.responseJSON.detail["incorrect_email_or_password"])
                    }
                }
            }
        });
    })
})