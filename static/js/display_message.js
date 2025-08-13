document.addEventListener('DOMContentLoaded', () => {
    // Get message container elements
    const successMessageDiv = document.getElementById('successMessage');
    const errorMessageDiv = document.getElementById('errorMessage');

    // Function to hide a message element
    const hideMessage = (element) => {
        element.classList.remove('show');
        element.classList.add('fade-out');
        setTimeout(() => {
            element.style.display = 'none';
            setTimeout(() => {
                element.classList.remove('fade-out');
            }, 10);
        }, 320)
    };

    // Function to display a message
    window.displayMessage = function(type, message) {
        if (!successMessageDiv || !errorMessageDiv) {
            return;
        }

        let targetMessageDiv;
        let otherMessageDiv;

        if (type === 'success') {
            targetMessageDiv = successMessageDiv;
            otherMessageDiv = errorMessageDiv;
        } else if (type === 'error') {
            targetMessageDiv = errorMessageDiv;
            otherMessageDiv = successMessageDiv;
        } else {
            console.error('Invalid message type. Use "success" or "error".');
            return;
        }

        // Hide the other message if it's currently visible
        if (otherMessageDiv.classList.contains('show')) {
            hideMessage(otherMessageDiv);
        }

        // Set the message text and display the target message div
        const messageTextElement = targetMessageDiv.querySelector('.message-text');
        messageTextElement.textContent = message;

        targetMessageDiv.classList.add('show');
        targetMessageDiv.classList.remove('fade-out');
        targetMessageDiv.style.display = 'flex';

        // Set up the hide logic based on the message type
        if (type === 'success') {
            // Automatically hide success message after 5 seconds
            setTimeout(() => hideMessage(targetMessageDiv), 5000);
        } else if (type === 'error') {
            // Add click listener to the close button for the error message
            const closeButton = targetMessageDiv.querySelector('.close-btn');
            closeButton.onclick = () => hideMessage(targetMessageDiv);
        }
    };
});