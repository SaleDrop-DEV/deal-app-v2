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

        // Create a new div element to hold the card content
        const cardDiv = document.createElement('div');
        cardDiv.classList.add('sales-item'); // Add the class to the div
        if (personal){
            cardDiv.classList.add('personal-sale');
        }

        // Use innerHTML to set the content of the card
        cardDiv.innerHTML = `
            <h3 class="sale-title">${title}</h3>
            <p class="sale-grabber">${grabber}</p>
            <p class="store-name accent-color">${storeName}</p>
            <button class="primary-btn view-details-btn">Bekijk</button>
            <p class="sale-date-received">${dateParsed}</p>
            <script class="sale-data" type="application/json">
                ${json_data}
            </script>`;

        salesContainer.appendChild(cardDiv);
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
