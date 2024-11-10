/**
 * Verifies Cloudflare CAPTCHA token and enables a button upon successful verification.
 *
 * @param {string} verifyUrl - The URL endpoint to send the CAPTCHA token for backend verification.
 * @param {string} sitekey - The Cloudflare site key required for CAPTCHA rendering and execution.
 * @param {string} buttonToDisable - The selector for the button element to enable/disable based on CAPTCHA status.
 * @param {string} idempotencyKey - A unique identifier to prevent duplicate CAPTCHA verifications for the same request.
 *
 * This function uses Cloudflare's CAPTCHA widget to generate a token on client-side, then sends the token to the
 * specified backend verification endpoint. Upon successful token verification, the specified button is enabled.
 *
 * - `callback`: Triggered when CAPTCHA is completed, sending the token to the backend for verification.
 * - `error`: Logs an error if an issue occurs with CAPTCHA execution.
 * - `expired-callback` & `timeout-callback`: Triggered when the CAPTCHA token expires or times out, disabling the specified button.
 *
 * @returns {void}
 */

const VerifyCFCaptcha = (verifyUrl, sitekey, buttonToDisable, idempotencyKey) => {
    // sends token from CF response to backend endpoint
    // in order to verify the token and proceed auth process
    const callback = (token) => {
        $.ajax({
            url: verifyUrl,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                token: token,
                idempotency_key: idempotencyKey
            }),
            success: (response) => {
                const verificationResult = response.message;
                if (verificationResult === "success") {
                    $(`${buttonToDisable}`).prop("disabled", false);
                }
            },
            error: (xhr, status, error) => {
                console.log("Verification error:", error);
            },
        });
    };

    window.onloadTurnstileCallback = () => {
        turnstile.execute("#cloudflare-captcha", {
            sitekey: sitekey,
            callback: callback,
            error: () => {
                console.log("Some error occurred.");
            },
            "expired-callback": () => {
                $(`${buttonToDisable}`).prop("disabled", true);
            },
            "timeout-callback": () => {
                $(`${buttonToDisable}`).prop("disabled", true);
            }
        });
    };
}

export default VerifyCFCaptcha