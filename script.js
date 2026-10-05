// UI Elements
const uploadView = document.getElementById('upload-view');
const processingView = document.getElementById('processing-view');
const reportView = document.getElementById('report-view');

const fileInput = document.getElementById('file-input');
const fileLabel = document.getElementById('file-label');
const checkBtn = document.getElementById('check-btn');

const processingFilename = document.getElementById('processing-filename');
const logList = document.getElementById('log-list');

const reportFilename = document.getElementById('report-filename');
const resultImage = document.getElementById('result-image');
const classificationResult = document.getElementById('classification-result');

const uploadAnotherBtn = document.getElementById('upload-another-btn');
const exitBtn = document.getElementById('exit-btn');

let selectedFile = null;

// File Input
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        fileLabel.innerText = selectedFile.name;
        checkBtn.disabled = false; // Enable the check button
    }
});

// EC2 Comms
checkBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // Switch Views
    uploadView.classList.remove('active');
    processingView.classList.add('active');
    processingFilename.innerText = selectedFile.name;
    logList.innerHTML = '';
    const objectURL = URL.createObjectURL(selectedFile);
    resultImage.src = objectURL;

    addLog("> Initializing encrypted uplink to deepfakeproxy.duckdns.org...");
    addLog("> Transmitting image payload to EC2 container...");

    // payload file to EC2 server
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        
        const response = await fetch("https://deepfakeproxy.duckdns.org/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server deployment error: ${response.status}`);
        }

        addLog("> EC2 response received. Decrypting matrix output...");

        
        const data = await response.json();
        
        addLog("> Analysis complete. Rendering operational report.");
        
        
        setTimeout(() => {
            showReport(data);
        }, 800);

    } catch (error) {
        console.error("Uplink failed:", error);
        addLog("> ERROR: Target EC2 server unreachable.");
        addLog("> ABORTING...");
        
        alert("Failed to reach the EC2 server. Ensure the instance is running, Docker is active, and Port 8000 is open in your Security Group.");
        
        setTimeout(resetUI, 3000); 
    }
});

// Helper function
function addLog(message) {
    const li = document.createElement('li');
    li.innerText = message;
    logList.appendChild(li);
}

// Report generator
function showReport(data) {
    processingView.classList.remove('active');
    reportView.classList.add('active');
    reportFilename.innerText = selectedFile.name;
    
    
    const confidencePercent = (data.confidence * 100).toFixed(2);

    if (data.is_fake) {
        classificationResult.innerText = `CLASSIFICATION - FAKE (${confidencePercent}%)`;
        classificationResult.className = "classification fake"; 
    } else {
        
        const authenticPercent = (100 - confidencePercent).toFixed(2);
        classificationResult.innerText = `CLASSIFICATION - AUTHENTIC (${authenticPercent}%)`;
        classificationResult.className = "classification authentic"; 
    }
}

// RESET Button
uploadAnotherBtn.addEventListener('click', resetUI);
exitBtn.addEventListener('click', resetUI);

function resetUI() {
    selectedFile = null;
    fileLabel.innerText = "UPLOAD FILE";
    fileInput.value = "";
    checkBtn.disabled = true;

    reportView.classList.remove('active');
    processingView.classList.remove('active'); // Added safety clear
    uploadView.classList.add('active');
}