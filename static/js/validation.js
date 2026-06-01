document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Only apply if the form doesn't already have 'novalidate' class (unless we want to override)
        form.setAttribute('novalidate', true);
        form.classList.add('needs-validation');
        
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            // Real-time validation on blur/input
            input.addEventListener('blur', () => validateInput(input));
            input.addEventListener('input', () => {
                if (input.classList.contains('is-invalid') || input.classList.contains('is-valid')) {
                    validateInput(input);
                }
            });
            
            // Required field indicator
            if (input.hasAttribute('required')) {
                const label = form.querySelector(`label[for="${input.id}"]`);
                if (label && !label.innerHTML.includes('<span class="text-danger"> *</span>')) {
                    label.innerHTML += '<span class="text-danger"> *</span>';
                }
            }
        });
        
        form.addEventListener('submit', function (event) {
            let isValid = true;
            inputs.forEach(input => {
                if (!validateInput(input)) {
                    isValid = false;
                }
            });
            
            if (!isValid) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    function validateInput(input) {
        let valid = true;
        let message = '';
        
        // Clear previous validation messages
        const parent = input.parentElement;
        let feedback = parent.querySelector('.invalid-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            parent.appendChild(feedback);
        }
        
        // 1. Required Check
        if (input.hasAttribute('required') && !input.value.trim()) {
            valid = false;
            message = 'This field is required.';
        }
        // 2. Email Validation
        else if (input.type === 'email' && input.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value.trim())) {
                valid = false;
                message = 'Please enter a valid email address.';
            }
        }
        // 3. Phone Validation (starts with digit, 10-15 chars)
        else if ((input.type === 'tel' || input.name.includes('mobile') || input.name.includes('contact')) && input.value.trim()) {
            const phoneRegex = /^\+?[\d\s-]{10,15}$/;
            if (!phoneRegex.test(input.value.trim())) {
                valid = false;
                message = 'Please enter a valid phone number (10-15 digits).';
            }
        }
        // 4. Numeric validation (min/max)
        else if (input.type === 'number' && input.value.trim()) {
            const val = parseFloat(input.value);
            const min = input.getAttribute('min');
            const max = input.getAttribute('max');
            if (isNaN(val)) {
                valid = false;
                message = 'Please enter a valid number.';
            } else if (min !== null && val < parseFloat(min)) {
                valid = false;
                message = `Value must be greater than or equal to ${min}.`;
            } else if (max !== null && val > parseFloat(max)) {
                valid = false;
                message = `Value must be less than or equal to ${max}.`;
            }
        }
        // 5. Length Validation
        else if (input.value.trim()) {
            const minLength = input.getAttribute('minlength');
            const maxLength = input.getAttribute('maxlength');
            if (minLength && input.value.trim().length < parseInt(minLength)) {
                valid = false;
                message = `Minimum length is ${minLength} characters.`;
            } else if (maxLength && input.value.trim().length > parseInt(maxLength)) {
                valid = false;
                message = `Maximum length is ${maxLength} characters.`;
            }
        }
        
        // Apply styling
        if (valid) {
            input.classList.remove('is-invalid');
            if (input.value.trim()) input.classList.add('is-valid');
            feedback.textContent = '';
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
            feedback.textContent = message;
        }
        
        return valid;
    }
});
