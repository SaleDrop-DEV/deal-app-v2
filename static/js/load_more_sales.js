let activeLoading = false;
    
function observeLastChildVisibility(containerSelector, callbackFunction, options = {}, observeOnce = true) {
    const container = document.querySelector(containerSelector);

    if (!container) {
        console.warn(`Container with selector "${containerSelector}" not found.`);
        return;
    }

    // Get all direct children of the container
    const children = container.children;

    if (children.length === 0) {
        console.warn(`Container "${containerSelector}" has no children to observe.`);
        return;
    }

    // Select the last child element
    const lastChild = children[children.length - 1];

    // Configure the Intersection Observer
    const observerOptions = {
        root: options.rootSelector ? document.querySelector(options.rootSelector) : null, // null means the viewport
        rootMargin: options.rootMargin || '0px',
        threshold: options.threshold || 0.1 // Trigger when 10% of the target is visible
    };

    const observerCallback = (entries, observer) => {
        entries.forEach(entry => {
            // If the last child is intersecting (visible)
            if (entry.isIntersecting) {
                callbackFunction(); // Trigger the provided function

                if (observeOnce) {
                    observer.unobserve(entry.target); // Stop observing after it's visible once
                }
            }
        });
    };

    // Create the Intersection Observer
    const observer = new IntersectionObserver(observerCallback, observerOptions);

    // Start observing the last child
    observer.observe(lastChild);
}

function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

function displaySales(data) {
    // 1. Get the container where you want to display the sales
    const salesContainer = document.getElementById('sales-container'); // Assuming this is your target ID

    // Check if the container exists
    if (!salesContainer) {
        console.error("Error: 'sales-container-small' not found in the DOM.");
        return; // Exit the function if the container isn't there
    }

    if (!data || !data.deals || !Array.isArray(data.deals)) {
        console.warn("Invalid data format for displaySales. Expected an object with a 'deal' array.");
        return;
    }

    data.deals.forEach(deal => {
        const title = deal.title;
        const grabber = deal.grabber;
        const dateParsed = deal.parsed_date_received;
        const storeName = deal.store.name;
        const personal = deal.personal;
        const json_data = JSON.stringify(deal.deal_json); // Ensure json_data is a proper JSON string

        // Conditional elements for deals.html-like cards
        let newBadgeHtml = '';
        // The template checks for request.user.is_staff, but for dynamically loaded content,
        // we assume if the backend sends is_new_deal_better, it should be displayed.
        if (deal.is_new_deal_better) {
            newBadgeHtml = '<span class="new-badge">NIEUW</span>';
        } else{
            console.log(deal.noDisplay)
        }
        console.log(newBadgeHtml)

        let probabilityBadgeHtml = '';
        if (deal.deal_probability && deal.noDisplay) {
            probabilityBadgeHtml = `<span class="probanility-badge ${deal.noDisplay}">${deal.deal_probability}</span>`;
        }

        // Create a new div element to hold the card content
        const cardDiv = document.createElement('div');
        cardDiv.classList.add('sales-item'); // Add the class to the div
        if (personal){
            cardDiv.classList.add('personal-sale');
        }

        // Use innerHTML to set the content of the card
        cardDiv.innerHTML = `
            <h3 class="sale-title">${title}</h3>
            <p class="sale-grabber">${grabber}
                ${newBadgeHtml}
            </p>
            <p class="store-name accent-color">${storeName}</p>
            <button class="primary-btn view-details-btn">Bekijk</button>
            <p class="sale-date-received">${dateParsed}</p>
            <script class="sale-data" type="application/json">
                ${json_data}
            </script>
            ${probabilityBadgeHtml}`;
        salesContainer.appendChild(cardDiv);
    });
}

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

function addClickToDetailBtn(){
    const viewDetailsButtons = document.querySelectorAll('.view-details-btn');
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
}

// 3. Call the function when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    let currentObserver = null; // To keep track of the active observer
    const paginationLogic = document.getElementsByClassName('pagination-logic')[0];


    function setupInfiniteScrollObserver() {
        if (currentObserver) {
            currentObserver.disconnect(); // Stop observing previous target
        }

        const container = document.getElementById('sales-container');
        if (!container || container.children.length === 0) {
            return;
        }

        const lastChild = container.children[container.children.length - 1];

        const observerOptions = {
            root: null, // viewport
            rootMargin: '0px',
            threshold: 0.1
        };

        const observerCallback = (entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    if (!activeLoading){
                        observer.unobserve(entry.target); // Stop observing the old last item
                        loadMoreItemsAndReobserve(); // Load more and setup observer again
                        setTimeout(() => {
                            activeLoading = false;
                        }, 1);
                    }
                }
            });
        };

        currentObserver = new IntersectionObserver(observerCallback, observerOptions);
        currentObserver.observe(lastChild);
    }

    async function loadMoreContent() {
        const container = document.getElementById('sales-container');
        const hasNextPage = container.getAttribute('data-hasNextPage') === 'True';
        const currentPage = parseInt(container.getAttribute('data-currentPage'));

        if (!hasNextPage || activeLoading) return Promise.resolve(false); // prevent multiple triggers

        activeLoading = true;
        const newSalesLoader = document.getElementById('newSalesLoader');
        newSalesLoader.classList.add('active-loader');
        const slug = document.getElementsByTagName('header')[0].getAttribute('data-slug')
        const apiUrl = `/deals/${slug}/`;  // Adjust based on your route

        
        try {
            try {
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({ page: currentPage + 1 })
                });
                const data_1 = await response.json();
                displaySales(data_1);
                addClickToDetailBtn();
                container.setAttribute('data-currentPage', currentPage + 1);
                container.setAttribute('data-hasNextPage', data_1.has_next_page ? 'True' : 'False');
                if (!data_1.has_next_page){
                    document.getElementById('finalMessage').innerHTML = `<p style="text-align: center;">Geen sales meer.</p>`
                    paginationLogic.classList.remove('pagination-logic-active')
                    paginationLogic.style.display = 'none'
                    document.getElementById('finalMessage').style.display = 'block';
                }
                return true;
            } catch (err) {
                console.log(err)
                window.displayMessage('error', 'Er ging iets mis.');
            }
        } finally {
            newSalesLoader.classList.remove('active-loader');
            activeLoading = false;
        }
    }

    function loadMoreItemsAndReobserve() {
        loadMoreContent().then(success => {
            if (success) {
                // Wait for DOM update, then reobserve new last item
                requestAnimationFrame(() => {
                    setTimeout(() => setupInfiniteScrollObserver(), 1); // delay slightly
                });
            }
        });
    }

    // only use infinite scroll if device width is less than 900px
    if (window.matchMedia('(max-width: 900px)').matches) {
        setupInfiniteScrollObserver();
    } else{
        paginationLogic.classList.add('pagination-logic-active')
    }
    // setupInfiniteScrollObserver();
});
