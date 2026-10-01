function closeModal(elementId) {
    document.getElementById(elementId).classList.remove('is-active');
}

function openModal(elementId) {
    document.getElementById(elementId).classList.add('is-active');
}

function loadModals() {
    const triggers = document.querySelectorAll('[trigger=modal]')
    triggers.forEach((element) => {
        const query = element.getAttribute("modal")
        if (!query) {
            console.error(`modal attribute not defined for ${element}`)
        } else {
            element.addEventListener('click', function() {
                //run callback if exists
                if (element.getAttribute('callback')) {
                    eval(element.getAttribute('callback'))
                }
                document.querySelector(query).classList.toggle('is-active');
            })
        }
    })
}

document.addEventListener("DOMContentLoaded", () => {
    loadModals()
});