/**
 * Verifies the CAPTCHA response by sending the token and idempotency key to the backend.
 * 
 * This function sends an AJAX POST request to the provided `verifyUrl` to validate
 * the CAPTCHA token. If the response from the server indicates success, the promise
 * resolves to `true`. If the verification fails or there is an error, it resolves to
 * `false` or rejects with the error message.
 *
 * @param {string} verifyUrl - The URL of the backend endpoint for CAPTCHA verification.
 * @param {string} token - The CAPTCHA response token to be verified.
 * @param {string} idempotencyKey - The idempotency key for the request.
 * 
 * @returns {Promise<boolean>} - A promise that resolves with `true` if verification
 *   is successful, `false` if unsuccessful, or rejects with the error if the request fails.
 */
const verifyCaptcha = (verifyUrl, token, idempotencyKey) => {
    return new Promise((resolve, reject) => {
        $.ajax({
            url: verifyUrl,
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                token: token,
                idempotency_key: idempotencyKey
            }),
            success: (response, textStatus, xhr) => {
                if (xhr.status === 200) {
                    resolve(true);
                } else {
                    resolve(false);
                }
            },
            error: (jqXHR, textStatus, errorThrown) => {
                if (jqXHR.status == 400) {
                    reject(errorThrown);
                }
            },
        });
    });
};

export default verifyCaptcha