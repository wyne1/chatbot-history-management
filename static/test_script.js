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
    
    const colors = {
        'batch_summary': 'rgb(255, 99, 132)',
        'summary_truncation': 'rgb(255, 159, 64)',
        'hierarchical': 'rgb(255, 205, 86)',
        'keyword': 'rgb(75, 192, 192)',
        'topic': 'rgb(54, 162, 235)',
        'sliding_window': 'rgb(153, 102, 255)',
        'sliding_window_5': 'rgb(201, 203, 207)',
        'hybrid': 'rgb(201, 203, 207)'
    };

    const datasets = Object.entries(data).map(([approach, values]) => ({
        label: approach,
        data: values.map(([x, y]) => ({x, y})),
        fill: false,
        borderColor: colors[approach] || getRandomColor(),
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
                        text: 'Prompt Token Count'
                    }
                }
            }
        }
    });
}