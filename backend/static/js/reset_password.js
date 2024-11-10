import VerifyCFCaptcha from "./verify_cf_captcha.js"

$(document).ready(() => {
    const captchaVerifyUrl = $("#reset-password-form").data("captcha-verify-url");
    const cloudflareSiteKey = $("#sitekey").val();
    const idempotencyKey = crypto.randomUUID();

    $("#reset-password").prop("disabled", true);

    VerifyCFCaptcha(captchaVerifyUrl, cloudflareSiteKey, "#reset-password", idempotencyKey)

    $("#reset-password-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const resetPasswordUrl = $("#reset-password-form").data("reset-url");

        $.ajax({
            url: resetPasswordUrl,
            method: "POST",
            dataType: "json",
            contentType: "application/json",
            data: JSON.stringify({
                email: enteredEmail,
            }),
            success: (response, textStatus, xhr) => {
                $("#reset-success").text(response);
            },
            error: (jqXHR, textStatus, errorThrown) => {
                $("#email-error").text(jqXHR.responseJSON.detail);
            }
        });
    });
});
