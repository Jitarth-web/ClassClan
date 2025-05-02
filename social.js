document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Preview image before upload with drag and drop support
    const imageInput = document.querySelector('input[type="file"]');
    const dropZone = document.querySelector('.image-drop-zone');

    if (imageInput && dropZone) {
        // Drag and drop functionality
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                imageInput.files = e.dataTransfer.files;
                handleImagePreview(e.dataTransfer.files[0]);
            }
        });

        // Regular file input handling
        imageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                handleImagePreview(this.files[0]);
            }
        });
    }

    // Handle image preview
    function handleImagePreview(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.createElement('img');
            preview.src = e.target.result;
            preview.className = 'img-fluid mt-2 rounded';
            const previewContainer = dropZone || imageInput.parentElement;
            const existingPreview = previewContainer.querySelector('img');
            if (existingPreview) {
                existingPreview.remove();
            }
            previewContainer.appendChild(preview);
        }
        reader.readAsDataURL(file);
    }

    // Smooth scroll to comments when clicking comment button
    document.querySelectorAll('.comment-button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentSection = this.closest('.card').querySelector('.comment-section');
            commentSection.scrollIntoView({ behavior: 'smooth' });
            commentSection.querySelector('input').focus();
        });
    });

    // Like animation
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', function() {
            const icon = this.querySelector('i');
            icon.classList.add('animate-like');
            setTimeout(() => icon.classList.remove('animate-like'), 500);
        });
    });

    // View counter
    document.querySelectorAll('.post-card').forEach(post => {
        const postId = post.dataset.postId;
        // Only increment view if user is not the author
        if (!post.classList.contains('own-post')) {
            fetch(`/increment_view/${postId}`)
                .then(response => response.json())
                .then(data => {
                    const viewCount = post.querySelector('.view-count');
                    if (viewCount) {
                        viewCount.textContent = data.views;
                    }
                });
        }
    });

    // Character counter for post content
    const postContent = document.querySelector('textarea[name="content"]');
    if (postContent) {
        const maxLength = 500;
        const counter = document.createElement('div');
        counter.className = 'text-muted small mt-1';
        postContent.parentNode.insertBefore(counter, postContent.nextSibling);

        function updateCounter() {
            const remaining = maxLength - postContent.value.length;
            counter.textContent = `${remaining} characters remaining`;
            counter.style.color = remaining < 50 ? '#dc3545' : '';
        }

        postContent.addEventListener('input', updateCounter);
        updateCounter();
    }
});