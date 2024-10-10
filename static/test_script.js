document.getElementById('runTest').addEventListener('click', async () => {
    const fileInput = document.getElementById('conversationFile');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/run_test', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
    }
});

function displayResults(data) {
    const ctx = document.getElementById('resultChart').getContext('2d');
    
    const datasets = Object.entries(data).map(([approach, values]) => ({
        label: approach,
        data: values.map(([x, y]) => ({x, y})),
        fill: false,
        borderColor: getRandomColor(),
        tension: 0.1
    }));

    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: 'Message Number'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Cumulative Token Count'
                    }
                }
            }
        }
    });
}

function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}