function formPrepare() {
    const forms = document.querySelectorAll('form');
    forms.forEach((form) => {   
        if (form.getAttribute('static')) {
            return
        }
        form.addEventListener('submit', (event) => {  
            event.preventDefault();
            const formData = new FormData(form);
            const action = form.getAttribute('action');
            const method = form.getAttribute('method') || 'POST';

            fetch(action, {
                method: method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.text())
            .then(data => {
                eval(data)
            })
            .catch(error => {
                console.error('Fetch error:', error);
            });
        })
    })
}

function clearForm(query) {
    const rootElement = document.querySelector(query)
    rootElement.querySelectorAll("[name]").forEach((element) => {
        element.value = ""
    })
}

document.addEventListener("DOMContentLoaded", () => {
    formPrepare();
});