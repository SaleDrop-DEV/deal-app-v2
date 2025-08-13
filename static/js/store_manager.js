document.addEventListener('DOMContentLoaded', () => {
    // --- Add New Store Email Logic ---
    const newStoreEmailInputsContainer = document.getElementById('emailInputsContainer');
    const addNewStoreEmailBtn = document.getElementById('add-email-btn');

    // The button's onclick attribute already calls the function,
    // so we don't need a separate event listener here.

    // --- Edit Store Modal Logic ---
    const editStoreModal = document.getElementById('editStoreModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const editStoreForm = document.getElementById('editStoreForm');
    const editEmailInputsContainer = document.getElementById('edit-email-inputs-container');
    const addEditEmailBtn = document.getElementById('add-edit-email-btn');

    document.querySelectorAll('.edit-store-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const storeCard = event.target.closest('.store-card');
            const storeId = storeCard.dataset.storeId;
            const storeName = storeCard.dataset.storeName;
            const storeHomeUrl = storeCard.dataset.storeHomeUrl;
            const storeSaleUrl = storeCard.dataset.storeSaleUrl;
            const storeImageUrl = storeCard.dataset.storeImageUrl;
            const storeEmails = storeCard.dataset.storeEmails ? storeCard.dataset.storeEmails.split(',') : [];

            // Populate the modal form
            document.getElementById('edit_store_id').value = storeId;
            document.getElementById('edit_name').value = storeName;
            document.getElementById('edit_home_url').value = storeHomeUrl;
            if (storeSaleUrl && storeSaleUrl != 'None') {
                document.getElementById('edit_sale_url').value = storeSaleUrl;
            }
            
            // Clear previous email inputs in the modal
            const existingModalEmailWrappers = editEmailInputsContainer.querySelectorAll('.modal-email-input-wrapper');
            existingModalEmailWrappers.forEach(wrapper => wrapper.remove());

            // Add existing emails to the modal form
            if (storeEmails.length > 0) {
                storeEmails.forEach(email => {
                    addEmailInput(editEmailInputsContainer, 'edit_email_addresses', email.trim());
                });
            } else {
                 // Add an empty input if no emails exist
                 addEmailInput(editEmailInputsContainer, 'edit_email_addresses', '');
            }

            // Show the modal
            editStoreModal.classList.add('active');
        });
    });

    closeModalBtn.addEventListener('click', () => {
        editStoreModal.classList.remove('active');
    });

    // Add new email input in the edit modal
    addEditEmailBtn.addEventListener('click', () => {
        addEmailInput(editEmailInputsContainer, 'edit_email_addresses');
    });

    // Handle form submission for editing
    editStoreForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(this);
        const storeId = formData.get('store_id');

        const updateUrl = `/deals/stores-manager/edit/${storeId}/`;

        const emailInputs = editEmailInputsContainer.querySelectorAll('input[name="edit_email_addresses"]');
        const emails = Array.from(emailInputs).map(input => input.value.trim()).filter(email => email !== '');

        formData.delete('edit_email_addresses');
        formData.append('email_addresses', emails.join(','));

        fetch(updateUrl, {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                if (response.headers.get('content-type')?.includes('application/json')) {
                    return response.json().then(data => { throw new Error(data.error || 'Server error'); });
                }
                throw new Error('Network response was not ok.');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(data.message || 'Store updated successfully!');
                editStoreModal.classList.remove('active');
                location.reload();
            } else {
                alert(data.error || 'Failed to update store.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        });
    });

    const deleteStoreBtn = document.getElementById('deleteStoreBtn');

    deleteStoreBtn.addEventListener('click', () => {
        if (!confirm('Weet je zeker dat je deze winkel wilt verwijderen? Dit kan niet ongedaan gemaakt worden.')) {
            return;
        }

        const storeId = document.getElementById('edit_store_id').value;
        const deleteUrl = `/deals/stores-manager/delete/${storeId}/`;

        fetch(deleteUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Fout bij verwijderen van winkel.');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(data.message || 'Winkel succesvol verwijderd!');
                editStoreModal.classList.remove('active');
                location.reload();
            } else {
                alert(data.error || 'Verwijderen mislukt.');
            }
        })
        .catch(error => {
            alert('Er is een fout opgetreden: ' + error.message);
        });
    });

    // Helper to get CSRF token from cookies (needed for POST)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
