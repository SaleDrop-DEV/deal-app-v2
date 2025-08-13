document.addEventListener('DOMContentLoaded', () => {
    // Navbar Script (copied from your previous input)
    const burger = document.getElementById('burger');
    const navOverlay = document.getElementById('navOverlay');
    const navLinksList = document.querySelector('.nav-links'); // The UL element
    const navItems = navLinksList.querySelectorAll('li'); // All LI elements

    burger.addEventListener('click', () => {
        const isOpen = navOverlay.classList.contains('open');

        burger.classList.toggle('open');
        navOverlay.classList.toggle('open');

        if (!isOpen) {
            navItems.forEach(item => {
                item.classList.remove('is-fading-in');
                item.style.transitionDelay = '0s';
            });
            setTimeout(() => {
                navItems.forEach((item, index) => {
                    item.style.transitionDelay = `${index * 0.15}s`;
                    item.classList.add('is-fading-in');
                });
            }, 50);
        } else {
            navItems.forEach(item => {
                item.classList.remove('is-fading-in');
                item.style.transitionDelay = '0s';
            });
        }
    });

    navLinksList.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            if (navOverlay.classList.contains('open')) {
                burger.classList.remove('open');
                navOverlay.classList.remove('open');
                navItems.forEach(item => {
                    item.classList.remove('is-fading-in');
                    item.style.transitionDelay = '0s';
                });
            }
        });
    });

});