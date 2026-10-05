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

// --- STEP 1: FILE SELECTION ---
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        fileLabel.innerText = selectedFile.name;
        checkBtn.disabled = false; // Enable the check button
    }
});

// --- STEP 2: ACTUAL EC2 UPLINK ---
checkBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // Switch Views
    uploadView.classList.remove('active');
    processingView.classList.add('active');

    // Setup Processing View
    processingFilename.innerText = selectedFile.name;
    logList.innerHTML = '';
    
    // Convert image to display it later
    const objectURL = URL.createObjectURL(selectedFile);
    resultImage.src = objectURL;

    // Print initial real logs to the UI
    addLog("> Initializing encrypted uplink to 16.112.70.238:8000...");
    addLog("> Transmitting image payload to EC2 container...");

    // Prepare the payload for FastAPI
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        // Fire the payload at your EC2 Public IP
        const response = await fetch("http://16.112.70.238:8000/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Server deployment error: ${response.status}`);
        }

        addLog("> EC2 response received. Decrypting matrix output...");

        // Parse the exact JSON verdict from the Python backend
        const data = await response.json();
        
        addLog("> Analysis complete. Rendering operational report.");
        
        // Brief 800ms delay so you can read the final log before the screen flips
        setTimeout(() => {
            showReport(data);
        }, 800);

    } catch (error) {
        console.error("Uplink failed:", error);
        addLog("> ERROR: Target EC2 server unreachable.");
        addLog("> ABORTING...");
        
        alert("Failed to reach the EC2 server. Ensure the instance is running, Docker is active, and Port 8000 is open in your Security Group.");
        
        // Kick back to the start screen after a failure
        setTimeout(resetUI, 3000); 
    }
});

// Helper function to append terminal lines dynamically
function addLog(message) {
    const li = document.createElement('li');
    li.innerText = message;
    logList.appendChild(li);
}

// --- STEP 3: SHOW REAL REPORT ---
function showReport(data) {
    processingView.classList.remove('active');
    reportView.classList.add('active');
    reportFilename.innerText = selectedFile.name;
    
    // Convert the raw 0.0 to 1.0 probability into a clean percentage
    const confidencePercent = (data.confidence * 100).toFixed(2);

    // Update the UI dynamically based on the FastAPI response
    if (data.is_fake) {
        classificationResult.innerText = `CLASSIFICATION - FAKE (${confidencePercent}%)`;
        classificationResult.className = "classification fake"; 
    } else {
        // If it's authentic, we display the inverse confidence (e.g., 90% sure it's real)
        const authenticPercent = (100 - confidencePercent).toFixed(2);
        classificationResult.innerText = `CLASSIFICATION - AUTHENTIC (${authenticPercent}%)`;
        classificationResult.className = "classification authentic"; 
    }
}

// --- STEP 4: RESET ---
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