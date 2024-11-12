import verifyCaptcha from "./verify_cf_captcha.js"

$(document).ready(() => {
    const captchaVerifyUrl = $("#authentication-form").data("captcha-verify-url");
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

        captchaInit();

        (async () => {
            try {
                const isVerified = await verifyCaptcha(captchaVerifyUrl, captchaToken, idempotencyKey);
                if (isVerified) {
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
                            // Redirect the user after the cookie is set
                            window.location.href = response.redirect_url;
                        },
                        error: (jqXHR, textStatus, errorThrown) => {
                            if (jqXHR.status === 422) {
                                $("#password-error").text(`${jqXHR.responseJSON.detail[0].msg}.`);
                            }

                            if (jqXHR.status === 400) {
                                if (jqXHR.responseJSON.detail["email_invalid"] !== undefined) {
                                    $("#email-error").text(jqXHR.responseJSON.detail["email_invalid"])
                                }

                                if (jqXHR.responseJSON.detail["incorrect_email_or_password"] !== undefined) {
                                    $("#password-error").text(jqXHR.responseJSON.detail["incorrect_email_or_password"])
                                }
                            }

                            if (jqXHR.status === 404) {
                                if (jqXHR.responseJSON.detail["user_not_exists"] !== undefined) {
                                    $("#email-error").text(jqXHR.responseJSON.detail["user_not_exists"])
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
});
