import verifyCaptcha from "./verify_cf_captcha.js"

$(document).ready(() => {
    const captchaVerifyUrl = $("#reset-password-form").data("captcha-verify-url");
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

    $("#reset-password-form").on("submit", (event) => {
        event.preventDefault();
        const enteredEmail = $("#email").val();
        const resetPasswordUrl = $("#reset-password-form").data("reset-url");

        captchaInit();
        (async () => {
            try {
                const isVerified = await verifyCaptcha(captchaVerifyUrl, captchaToken, idempotencyKey);
                if (isVerified) {
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
                } else {
                    console.error("Captcha verification failed.");
                }
            } catch (error) {
                console.error(error);
            }
        })();
    });
});
