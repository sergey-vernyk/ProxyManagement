/**
 * Retrieves the value of a specific cookie by its name.
 *
 * @param {string} name - The name of the cookie to retrieve.
 * @returns {string|null} The decoded value of the cookie if found, or `null` if the cookie doesn't exist.
 *
 * @example
 * const csrfToken = getCookie("csrftoken");
 */
const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

export default getCookie