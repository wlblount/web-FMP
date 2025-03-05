document.addEventListener('DOMContentLoaded', () => {
    const functionSelector = document.getElementById('functionSelector');
    const stockSymbol = document.getElementById('stockSymbol');
    const periodSelector = document.getElementById('periodSelector');
    const period = document.getElementById('period');
    const searchBtn = document.getElementById('searchBtn');
    const output = document.getElementById('output');
    const description = document.getElementById('description');
    const errorMessage = document.getElementById('error-message');

    // Show/hide period selector based on function selection
    functionSelector.addEventListener('change', () => {
        periodSelector.style.display = 
            functionSelector.value === 'Intraday Data' ? 'flex' : 'none';
    });

    // Handle form submission
    searchBtn.addEventListener('click', async () => {
        const symbol = stockSymbol.value.trim().toUpperCase();
        
        if (!symbol) {
            errorMessage.textContent = 'Please enter a stock symbol';
            return;
        }

        // Show loading state
        searchBtn.disabled = true;
        searchBtn.textContent = 'Loading...';
        errorMessage.textContent = '';
        output.textContent = 'Loading data...';
        description.textContent = '';

        try {
            const formData = new FormData();
            formData.append('function_type', functionSelector.value);
            formData.append('symbol', symbol);
            if (functionSelector.value === 'Intraday Data') {
                formData.append('period', period.value);
            }

            const response = await fetch('/get_data', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                errorMessage.textContent = '';
                output.textContent = data.data;
                if (data.description) {
                    description.textContent = data.description;
                }
            } else {
                errorMessage.textContent = data.error || 'Error fetching data';
                output.textContent = '';
            }
        } catch (error) {
            errorMessage.textContent = 'Error connecting to the server';
            console.error('Error:', error);
            output.textContent = '';
        } finally {
            // Reset button state
            searchBtn.disabled = false;
            searchBtn.textContent = 'Run';
        }
    });

    // Allow Enter key to trigger search
    stockSymbol.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });

    // Set initial state
    periodSelector.style.display = 
        functionSelector.value === 'Intraday Data' ? 'flex' : 'none';
}); 