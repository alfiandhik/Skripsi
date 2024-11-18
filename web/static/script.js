document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector('form');
    const fileInput = document.querySelector('input[type="file"]');
    const progressBar = document.createElement('div');
    const messageBox = document.createElement('div');
    
    progressBar.style.display = 'none';
    progressBar.style.height = '20px';
    progressBar.style.width = '0';
    progressBar.style.backgroundColor = '#4caf50';
    progressBar.style.marginTop = '10px';
    
    messageBox.style.marginTop = '10px';
    
    form.appendChild(progressBar);
    form.appendChild(messageBox);
    
    function updateProgress(percent) {
        progressBar.style.display = 'block';
        progressBar.style.width = percent + '%';
    }
    
    function validateFile() {
        const allowedExtensions = ['csv', 'txt'];
        const fileName = fileInput.value;
        const fileExtension = fileName.split('.').pop().toLowerCase();
        
        if (!allowedExtensions.includes(fileExtension)) {
            messageBox.innerHTML = '<span style="color:red;">Invalid file type. Please upload a CSV or TXT file.</span>';
            return false;
        }
        
        messageBox.innerHTML = ''; 
        return true;
    }

    form.addEventListener('submit', function(e) {
        if (!validateFile()) {
            e.preventDefault();
            return;
        }
        
        updateProgress(0);
        
        let progress = 0;
        const interval = setInterval(function() {
            progress += 10;
            updateProgress(progress);
            
            if (progress >= 100) {
                clearInterval(interval);
                messageBox.innerHTML = '<span style="color:green;">File has been uploaded successfully!</span>';
            }
        }, 300); 
    });
});
