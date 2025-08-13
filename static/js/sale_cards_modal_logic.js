document.addEventListener('DOMContentLoaded', function() {
    const action_btn_for_small_screens = document.getElementById('small-screen-action-btn');
        // --- Product Detail View Functionality ---
    const productOverlay = document.getElementById('productOverlay');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const productContentWrapper = productOverlay.querySelector('.product-content-wrapper'); // Get the mobile slide-up panel
    const productModal = modalBackdrop.querySelector('.product-modal'); // Get the desktop modal
    const productCloseBtns = document.querySelectorAll('.product-close-btn'); // Both overlay and modal close buttons
    const viewDetailsButtons = document.querySelectorAll('.view-details-btn');



    // Get references to all elements that will be populated (for both overlay and modal)
    const productTitleElements = document.querySelectorAll('.product-title');
    const productGrabberElements = document.querySelectorAll('.product-grabber');
    const productDescriptionElements = document.querySelectorAll('.product-description');
    const highlightedProductsSliderElements = document.querySelectorAll('.highlighted-products-slider');
    const storeNameDetailElements = document.querySelectorAll('.store-name-detail');
    const storeLogoElements = document.querySelectorAll('.store-logo');
    const productMainLinkElements = document.querySelectorAll('.product-main-link');

    // Variables for swipe-down-to-close
    let startY = 0;
    let currentY = 0;
    let diffY = 0;
    let isSwipingDown = false;
    const swipeThreshold = 10; // Pixels to swipe down to trigger dismiss

    // Function to populate and show the product detail view
    function showProductDetails(dealData) {
        // Populate content for all instances (overlay and modal)
        productTitleElements.forEach(el => el.textContent = dealData.title || 'No Title');
        productGrabberElements.forEach(el => el.textContent = dealData.grabber || 'No Grabber');
        productDescriptionElements.forEach(el => el.textContent = dealData.description || 'No Description');
        storeNameDetailElements.forEach(el => el.textContent = dealData.store ? dealData.store.name : 'Unknown Store');
        productMainLinkElements.forEach(el => {
            el.href = dealData.main_link || '#';
            el.style.display = dealData.main_link ? 'inline-block' : 'none'; // Hide button if no link
        });
        storeLogoElements.forEach(el => {
            el.src = dealData.store && dealData.store.image_url ? dealData.store.image_url : 'https://placehold.co/50x50/F5F5F7/86868B?text=Store';
            el.alt = dealData.store && dealData.store.name ? `${dealData.store.name} Logo` : 'Store Logo';
        });

        // Populate highlighted products slider
        highlightedProductsSliderElements.forEach(slider => {
            slider.innerHTML = ''; // Clear previous products
            if (dealData.highlighted_products && Array.isArray(dealData.highlighted_products) && dealData.highlighted_products.length > 0) {
                dealData.highlighted_products.forEach(product => {
                    const productDiv = document.createElement('div');
                    productDiv.classList.add('highlighted-product-item');
                    const old_price = product.old_price;
                    const new_price = product.new_price;
                    let price_p = ''
                    if (old_price && new_price) {
                        price_p = `<p class="product-item-price">${product.new_price && product.new_price !== 'N/A' ? `€${parseFloat(product.new_price).toFixed(2)}` : (product.old_price && product.old_price !== 'N/A' ? `€${parseFloat(product.old_price).toFixed(2)}` : '')}</p>`
                    }

                    productDiv.innerHTML = `
                        <img src="${product.product_image_url || 'https://placehold.co/100x100/F5F5F7/86868B?text=Product'}" alt="${product.title || 'Product'} Image">
                        <p class="product-item-name">${product.title || 'Onbekend'}</p>
                        ${price_p}
                    `;
                    slider.appendChild(productDiv);
                });
                document.getElementsByClassName('highlighted-products-section')[0].style.display = 'block';
                document.getElementsByClassName('highlighted-products-section')[1].style.display = 'block';
            } else {
                document.getElementsByClassName('highlighted-products-section')[0].style.display = 'none';
                document.getElementsByClassName('highlighted-products-section')[1].style.display = 'none';
                slider.innerHTML = '<p class="no-products-message">Geen uitgelichte producten gevonden.</p>';
            }
        });

        // Determine screen size and show appropriate view
        if (window.matchMedia('(max-width: 767px)').matches) {
            // Small screen: slide-up overlay
            productOverlay.classList.add('show');
            action_btn_for_small_screens.classList.remove('hide-action-btn')
            action_btn_for_small_screens.classList.add('show-action-btn');
            action_btn_for_small_screens.onclick = () => {
                go_to_sale(dealData.main_link);
            }
            document.body.style.overflow = 'hidden'; // Prevent scrolling body
            // Reset transform in case it was moved by a previous failed swipe
            productContentWrapper.style.transform = 'translateY(0)';
            productContentWrapper.style.transition = 'transform 0.3s ease-out'; // Ensure transition is active
        } else {
            // Large screen: modal pop-up
            modalBackdrop.classList.add('show');
            document.getElementById("action-btn-large-screens").onclick = () => {
                go_to_sale(dealData.main_link);
            }
            // document.getElementById("action-btn-large-screens").style.top = top_offset - (60 - 32) + "px";
            document.body.style.overflow = 'hidden'; // Prevent scrolling body
            // Reset transform for modal as well
            productModal.style.transform = 'scale(1)';
            productModal.style.transition = 'transform 0.3s ease-out'; // Ensure transition is active
        }
    }

    // Function to hide the product detail view
    function hideProductDetails() {
        // Trigger fade-out/slide-down animation
        if (window.matchMedia('(max-width: 767px)').matches) {
            productContentWrapper.style.transform = 'translateY(100%)'; // Slide down
            productOverlay.classList.remove('show'); // Fade out backdrop
            action_btn_for_small_screens.classList.add('hide-action-btn')
            action_btn_for_small_screens.classList.remove('show-action-btn');
        } else {
            productModal.style.transform = 'scale(0.9)'; // Pop back in
            modalBackdrop.classList.remove('show'); // Fade out backdrop
        }

        // Wait for the animation to complete before hiding completely and restoring scroll
        const transitionEndHandler = () => {
            productOverlay.classList.remove('show'); // Ensure overlay is fully hidden
            modalBackdrop.classList.remove('show'); // Ensure modal is fully hidden
            document.body.style.overflow = ''; // Restore body scrolling
            // Remove the event listener to prevent multiple calls
            productContentWrapper.removeEventListener('transitionend', transitionEndHandler);
            productModal.removeEventListener('transitionend', transitionEndHandler);
        };

        // Add event listeners for transition end
        productContentWrapper.addEventListener('transitionend', transitionEndHandler);
        productModal.addEventListener('transitionend', transitionEndHandler);
    }

    function go_to_sale(link){
        window.open(link, '_blank');
    }

    // Event listeners for "Bekijk" buttons
    viewDetailsButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const salesItem = event.target.closest('.sales-item');
            const scriptTag = salesItem.querySelector('.sale-data[type="application/json"]');

            if (scriptTag) {
                let dealData;
                try {
                    dealData = JSON.parse(scriptTag.textContent);

                    // Ensure store data is directly available or handle its absence
                    if (!dealData.store && dealData.gmail_data && dealData.gmail_data.domain) {
                        dealData.store = {
                            name: dealData.gmail_data.domain,
                            image_url: `https://placehold.co/50x50/F5F5F7/86868B?text=${dealData.gmail_data.domain.charAt(0).toUpperCase()}`
                        };
                    }

                    showProductDetails(dealData);
                } catch (e) {
                    console.error('Error parsing JSON data for sale item:', e);
                    window.displayMessage('error', 'Kon de sale niet laden. Bekijk de console voor meer.');
                }
            } else {
                console.warn('No JSON data found for this sale item.');
                window.displayMessage('error', 'Geen gegevens gevonden.');
            }
        });
    });

    // Event listeners for close buttons (X icon)
    productCloseBtns.forEach(btn => {
        btn.addEventListener('click', hideProductDetails);
    });

    // Close modal/overlay when clicking outside the content (for large screens)
    modalBackdrop.addEventListener('click', (event) => {
        if (event.target === modalBackdrop) { // Ensure click is directly on backdrop, not content
            hideProductDetails();
        }
    });

    // Prevent clicks inside the content from closing the modal/overlay
    productContentWrapper.addEventListener('click', (event) => {
        event.stopPropagation();
    });
    productModal.addEventListener('click', (event) => {
        event.stopPropagation();
    });

    // --- Swipe-down-to-close for Mobile Overlay ---
    productContentWrapper.addEventListener('touchstart', (e) => {
        if (window.matchMedia('(max-width: 767px)').matches) { // Only for mobile overlay
            startY = e.touches[0].clientY;
            // Disable default transition during swipe to allow direct manipulation
            productContentWrapper.style.transition = 'none';
        }
    });

    productContentWrapper.addEventListener('touchmove', (e) => {
        if (window.matchMedia('(max-width: 767px)').matches) { // Only for mobile overlay
            currentY = e.touches[0].clientY;
            diffY = currentY - startY;

            // Only allow swipe down if at the top of the scrollable content
            // and if the swipe is actually downwards
            if (productContentWrapper.scrollTop === 0 && diffY > 0) {
                isSwipingDown = true;
                // Apply transform directly
                productContentWrapper.style.transform = `translateY(${diffY}px)`;
                e.preventDefault(); // Prevent native scroll if we're swiping to dismiss
            } else if (diffY < 0 && productContentWrapper.scrollTop > 0) {
                // If swiping up and not at the top, let native scroll handle it
                isSwipingDown = false; // Ensure swipe-down state is reset
            } else if (productContentWrapper.scrollTop === 0 && diffY < 0) {
                // If at top and trying to swipe up, prevent negative transform
                productContentWrapper.style.transform = `translateY(0px)`;
                isSwipingDown = false;
                e.preventDefault(); // Prevent rubber banding if at top
            }
        }
    });

    productContentWrapper.addEventListener('touchend', () => {
        if (window.matchMedia('(max-width: 767px)').matches) { // Only for mobile overlay
            // Re-enable transition for smooth return/dismissal
            productContentWrapper.style.transition = 'transform 0.3s ease-out';

            if (isSwipingDown && diffY > swipeThreshold) {
                // Dismiss if swipe distance exceeds threshold
                hideProductDetails();
            } else {
                // Snap back to original position
                productContentWrapper.style.transform = 'translateY(0)';
            }

            // Reset swipe state
            startY = 0;
            currentY = 0;
            diffY = 0;
            isSwipingDown = false;
        }
    });

})