
/**
 * Function to check if we are on the API Reference page
 * @returns {bool} True of on API Reference page. False otherwise.
 */
function shouldDisableScrollSpy() {
    // The API Reference page has <h1>API Reference</h1> as the first h1 element
    var h1Elements =  document.querySelectorAll("h1");
    var h1Array = Array.from(h1Elements);
    var isOnApiReferencePage = h1Array[0].textContent.trim() == 'API Reference'
    return isOnApiReferencePage
}

/**
 * Function to disable the Bootstrap Scroll Spy.
 */
function disableScrollSpy() {
    var scrollSpyBody = document.querySelector('body[data-bs-spy="scroll"][data-bs-target=".bd-toc-nav"]');
    if (scrollSpyBody) {
        scrollSpyBody.removeAttribute('data-bs-spy');
        scrollSpyBody.removeAttribute('data-bs-target');
    }
}

/**
 * Make TOC <li> elements active;
 * Add CSS class "active" to all the <nav.bd-toc-nav> > <ul> > <li> elements.
 */
function makeTocLiElementsActive() {
    // The sidebar TOC is <nav> element with class "bd-toc-nav"
    var navElements = document.querySelectorAll('nav.bd-toc-nav');
    navElements.forEach(function(navElement) {
        navElement.childNodes.forEach(function(node) {
            if (node.tagName === 'UL') {
                makeDirectLiChildrenActive(node);
            };
        });
    });
}


/**
 *  Add CSS class "active" to all the direct <li> type children of a node
 * @param {HTMLElement} node - The node
 */
function makeDirectLiChildrenActive(node) {
    node.childNodes.forEach(function(childNode) {
        if (childNode.tagName === 'LI') {
            childNode.classList.add('active');
        };
    });
}


/**
 *  This (1) Disables scroll spy if required (on API Reference page), and "opens"
 *  the TOC list so that the two first levels of the sidebar TOC are visible.
 */
if (shouldDisableScrollSpy()) {
    disableScrollSpy();
    makeTocLiElementsActive();
};
