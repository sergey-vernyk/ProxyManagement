/**
 * Checks if there is at least one modal window opened.
 * @param {Array<HTMLElement>} existingModals - The array of modal window HTML elements to check.
 * @returns {boolean} True if at least one modal window is opened; otherwise, false.
 */
const checkOpenedModalWindows = (existingModals) => {
    for (let i = 0; i < existingModals.length; i++) {
        let currentDisplay = $(existingModals[i]).css("display");
        if (currentDisplay !== "none") {
            return true;
        }
    }
    return false;
}

export default checkOpenedModalWindows