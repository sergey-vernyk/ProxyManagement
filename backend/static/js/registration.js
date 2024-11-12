import verifyCaptcha from "./verify_cf_captcha.js"

$(document).ready(() => {
    const captchaVerifyUrl = $("#registration-form").data("captcha-verify-url");
    const cloudflareSiteKey = $("#sitekey").val();
    const idempotencyKey = crypto.randomUUID();

    let captchaToken = null;

    const captchaInit = () => {
        window.onloadTurnstileCallback = () => {
            turnstile.execute("#cloudflare-captcha", {
                sitekey: cloudflareSiteKey,
                callback: (token) => {
                    captchaToken = token;
                },
                error: () => {
                    captchaToken = null;
                },
                "expired-callback": () => {
                    captchaToken = null;
                },
                "timeout-callback": () => {
                    captchaToken = null;
                }
            });
        };
    }

    captchaInit();

    $("#registration-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const enteredPassword = $("#password").val();
        const regUrl = $("#registration-form").data("reg-url");
        $("#password-error").text("");
        $("#email-error").text("");

        captchaInit();

        (async () => {
            try {
                const isVerified = await verifyCaptcha(captchaVerifyUrl, captchaToken, idempotencyKey);
                if (isVerified) {
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
                } else {
                    console.error("Captcha verification failed.");
                }
            } catch (error) {
                console.error(error);
            }
        })();
    })
})