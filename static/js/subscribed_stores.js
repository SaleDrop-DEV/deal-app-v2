function getCSRFToken() {
    let name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Check if this cookie string begins with the name we want
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const searchBarWrapper = document.getElementById("searchBarWrapper");
    const navbarHeight = document.querySelector("nav")?.offsetHeight || 60;
    const searchResults = document.getElementById("searchResults");
    const resultsContainer = document.querySelector('.searchResults_new');
    const loaderEl = document.getElementById('newStoresLoader');
    let debounceTimer;
    let isLoading = false;
    let hasNextPage = true;
    let lastCard = null; // To keep track of the last card added for observation

    // Scroll behavior when focusing input
    searchInput.addEventListener("focus", function () {
        const rect = searchBarWrapper.getBoundingClientRect();
        const absoluteTop = window.scrollY + rect.top;
        const scrollTarget = absoluteTop - navbarHeight - 10;

        window.scrollTo({
            top: scrollTarget,
            behavior: "smooth"
        });
    });

    searchButton.addEventListener("click", function () {
        const query = searchInput.value.trim();
        resultsContainer.innerHTML = ''; // Clear previous results
        searchResults.setAttribute("data-page", "0"); // Reset page to 0
        hasNextPage = true; // Reset hasNextPage
        if (lastCard) {
            observer.unobserve(lastCard);
        }
        if (query.length > 0) {
            fetchSearchResults(query, 1);
        }
    });


    // Debounce logic to limit API calls
    searchInput.addEventListener("input", function () {
        const query = searchInput.value.trim();
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            resultsContainer.innerHTML = ''; // Clear previous results
            searchResults.setAttribute("data-page", "0"); // Reset page to 0
            hasNextPage = true; // Reset hasNextPage
            if (lastCard) { // Disconnect previous observer if any
                observer.unobserve(lastCard);
            }
            if (query.length > 0) {
                fetchSearchResults(query, 1);
            }
        }, 300); // 300ms debounce
    });

    // Intersection Observer for infinite scroll
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !isLoading && hasNextPage) {
                const query = searchInput.value.trim();
                if (query.length > 0) {
                    let currentPage = parseInt(searchResults.getAttribute("data-page"));
                    fetchSearchResults(query, currentPage + 1);
                }
            }
        });
    }, {
        rootMargin: '100px'  // trigger a bit before last card fully visible
    });

    function fetchSearchResults(query, page) {
        if (!hasNextPage || isLoading) {
            return; // Don't fetch if no more pages or already loading
        }

        isLoading = true;
        loaderEl.style.display = 'block';

        fetch("{% url 'search_stores_api' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({
                query: query,
                page: page
            })
        })
        .then(response => response.json())
        .then(data => {
            const stores = data.stores;
            hasNextPage = data.hasNextPage; // Update hasNextPage based on API response
            searchResults.setAttribute("data-page", page); // Update current page
            
            appendSearchResults(stores);
            if (data.totalFound === 0){
                resultsContainer.innerHTML = `
                    <div class="no-store-found-container">
                        <h5>Geen winkels gevonden.</h5>
                        <p>Stuur deze winkel in om toe te voegen aan de alerts. Wij proberen binnen 2 dagen de winkel toe te voegen.</p>
                        <button class="action-btn suggest-btn">Insturen</button>
                    </div>
                `;
            }
            isLoading = false;
        })
        .catch(error => {
            console.error("Error fetching search results:", error);
            isLoading = false; // Ensure loading is reset even on error
        }).finally(() => {
            loaderEl.style.display = 'none';
        });
    }

    function appendSearchResults(stores) {
        if (lastCard) {
            observer.unobserve(lastCard); // Stop observing the previous last card
        }


        stores.forEach((store, index) => {
            const card = document.createElement('div');
            card.id = `store-card-${store.id}`;
            card.className = 'store-card'; // Apply initial styles (e.g., opacity: 0)
            const isSubscribed = store.is_subscribed;
            let button
            if (isSubscribed) {
                button = `<button id="subscribe-btn-${store.id}" class="action-btn is-subscribed-btn" onclick="unSubscribeToStore(${store.id})">Geabboneerd</button>`;
            } else {
                button = `<button id="subscribe-btn-${store.id}" class="primary-btn subscribe-btn" onclick="subscribeToStore(${store.id})">Abonneer</button>`;
            }


            card.innerHTML = `
                <img src="${store.image_url}" alt="Store Logo" class="store-logo-img">
                <h3 class="store-name">${store.name}</h3>
                ${button}
                <div id="newStoresLoader-${store.id}" style="display: none;" class="loader-spinner" aria-label="Loading..."></div>
            `;

            resultsContainer.appendChild(card);
            void card.offsetHeight; 
            setTimeout(() => {
                card.classList.add('visible');
            }, index * 50);

            if (index === stores.length - 1) {
                lastCard = card;
                observer.observe(lastCard);
            }
        });
    }

    // Helper to get CSRF token from cookies
        
});
function subscribeToStore(storeId) {
    const subscribeBtn = document.getElementById(`subscribe-btn-${storeId}`);
    const loaderEl = document.getElementById(`newStoresLoader-${storeId}`);
    subscribeBtn.style.display = 'none';
    loaderEl.style.display = 'block';
        fetch("{% url 'subscribe_to_store_api' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({
                store_id: storeId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error){
                window.displayMessage('error', data.error);
                return;
            } else{
                subscribeBtn.onclick = function () {
                    unSubscribeToStore(storeId);
                };
                subscribeBtn.innerHTML = 'Geabboneerd';
                subscribeBtn.classList.add('is-subscribed-btn');
                subscribeBtn.classList.add('action-btn');
                subscribeBtn.classList.remove('primary-btn');
                subscribeBtn.classList.remove('subscribe-btn');

                addToSubscribedStores(storeId, data.store_name, data.image_url);

                window.displayMessage('success', data.message);
            }
        })
        .catch(error => {
            window.displayMessage('error', error);
        }).finally(() => {
            subscribeBtn.style.display = 'block';
            loaderEl.style.display = 'none';
        }); 
    }

function unSubscribeToStore(storeId) {
    const subscribeBtn = document.getElementById(`subscribe-btn-${storeId}`);
    const loaderEl = document.getElementById(`newStoresLoader-${storeId}`);
    if (subscribeBtn){
        subscribeBtn.style.display = 'none';
    }
    if (loaderEl){
        loaderEl.style.display = 'block';
    }
        fetch("{% url 'un_subscribe_to_store_api' %}", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({
                store_id: storeId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error){
                window.displayMessage('error', data.error);
                return;
            } else{
                if (subscribeBtn){
                    subscribeBtn.onclick = function () {
                        subscribeToStore(storeId);
                    };
                    subscribeBtn.innerHTML = 'Abonneer';
                    subscribeBtn.classList.remove('is-subscribed-btn');
                    subscribeBtn.classList.remove('action-btn');
                    subscribeBtn.classList.add('primary-btn');
                    subscribeBtn.classList.add('subscribe-btn');
                }

                // ✨ Remove card from subscribed stores
                const subscribedCard = document.getElementById(`subscribed-store-${storeId}`);
                if (subscribedCard) {
                    subscribedCard.classList.add('collapse-out');
                    subscribedCard.addEventListener('animationend', () => {
                        subscribedCard.remove();
                    });
                }

                window.displayMessage('success', data.message);
            }
        })
        .catch(error => {
            window.displayMessage('error', error);
        }).finally(() => {
            if (subscribeBtn){
                subscribeBtn.style.display = 'block';
            }
            if (loaderEl){
                loaderEl.style.display = 'none';
            }
        }); 
}

function addToSubscribedStores(storeId, storeName, imageUrl) {
    const subscribedContainer = document.getElementById("subscribedStoresContainer");
    if (!subscribedContainer) return;

    const card = document.createElement("div");
    card.className = "subscribed-store-card";
    card.id = `subscribed-store-${storeId}`;

    card.innerHTML = `
        <img src="${imageUrl}" alt="Store Logo" class="store-logo-img-small">
        <span class="subscribed-name">${storeName}</span>
        <span id="subscribed-menu-${storeId}" class="subscribed-menu">⋮</span>
        <div style="display: none;" id="actions-container-${storeId}" class="actions-container">
            <div class="action-list">
                <button class="primary-btn" onclick="unSubscribeToStore(${storeId})">Afmelden</button>
                <button class="action-btn last-action-btn">Sluiten</button>
            </div>
        </div>
    `;
    const menu = card.querySelector(`#actions-container-${storeId}`);
    const menuIcon = card.querySelector(`#subscribed-menu-${storeId}`);

    menuIcon.addEventListener("click", function (e) {
        e.stopPropagation();
        closeAllMenus();

        if (menu) {
            menu.classList.remove('fade-out');
            menu.style.display = 'block';
            menu.classList.add('pop-in');
        }
    });

    // Optional: fade-in animation
    card.style.height = '0px';
    card.style.overflow = 'hidden';
    card.style.transition = 'height 300ms ease, opacity 300ms ease';
    card.style.opacity = 0;

    subscribedContainer.prepend(card); // Add at the top

    // Trigger animation after slight delay
    setTimeout(() => {
        card.style.height = card.scrollHeight + "px";
        card.style.opacity = 1;
    }, 10);

    // Remove fixed height after animation to allow auto layout
    setTimeout(() => {
        card.style.overflow = 'visible';
        card.style.height = "";
    }, 350);
}


function closeAllMenus() {
    document.querySelectorAll('.actions-container').forEach((menu) => {
        fadeOutMenu(menu);
    });
}

function fadeOutMenu(menu) {
    if (menu.style.display === 'block') {
        menu.classList.remove('pop-in');
        menu.classList.add('fade-out');

        // Wait for animation to finish before hiding
        menu.addEventListener('animationend', function handleFade() {
            menu.style.display = 'none';
            menu.classList.remove('fade-out');
            menu.removeEventListener('animationend', handleFade);
        });
    }
}

    document.addEventListener("DOMContentLoaded", function () {
    // Handle ⋮ click to toggle menu
    document.querySelectorAll('.subscribed-menu').forEach((menuIcon) => {
        const card = menuIcon.closest('.subscribed-store-card');
        const storeId = card?.id?.split('-')?.pop();
        const menu = document.getElementById(`actions-container-${storeId}`);

        menuIcon.addEventListener("click", function (e) {
            e.stopPropagation();
            closeAllMenus();

            if (menu) {
                menu.classList.remove('fade-out');
                menu.style.display = 'block';
                menu.classList.add('pop-in');
            }
        });
    });

    // Handle close button inside menu
    document.querySelectorAll('.last-action-btn').forEach((btn) => {
        btn.addEventListener("click", function (e) {
            const container = e.target.closest('.actions-container');
            if (container) {
                fadeOutMenu(container);
            }
        });
    });

    // Handle "Afmelden" (Unsubscribe)
    document.querySelectorAll('.action-list .primary-btn').forEach((btn) => {
        btn.addEventListener("click", function (e) {
            const card = e.target.closest('.subscribed-store-card');
            const storeId = card?.id?.split('-')?.pop();
            unSubscribeToStore(storeId);
        });
    });

    // Close all action menus when clicking outside
    document.addEventListener("click", function () {
        closeAllMenus();
    });
});
