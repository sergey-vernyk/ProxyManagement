import VerifyCFCaptcha from "./verify_cf_captcha.js"

$(document).ready(() => {
    const captchaVerifyUrl = $("#registration-form").data("captcha-verify-url");
    const cloudflareSiteKey = $("#sitekey").val();
    const idempotencyKey = crypto.randomUUID();

    $("#register").prop("disabled", true);

    VerifyCFCaptcha(captchaVerifyUrl, cloudflareSiteKey, "#register", idempotencyKey)

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
                $("#reg-success").text(response["message"]);
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