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

    // Format data based on function type
    function formatData(data, functionType) {
        if (!data) return '';
        
        try {
            // The data is already parsed by response.json()
            switch(functionType) {
                case 'Company Profile':
                    return formatCompanyProfile(data);
                case 'Earnings Dates':
                    return formatEarningsData(data);
                case 'Intraday Data':
                    return formatIntradayData(data);
                case 'Dividends':
                    return formatDividendsData(data);
                case 'Search Data':
                    return formatSearchData(data);
                default:
                    return JSON.stringify(data, null, 2);
            }
        } catch (e) {
            console.error('Error formatting data:', e);
            return JSON.stringify(data, null, 2);
        }
    }

    // Format company profile data
    function formatCompanyProfile(data) {
        if (!data) return '';
        return `
            <div class="profile-card">
                <h2>${data.name || 'Company Profile'}</h2>
                <div class="profile-grid">
                    <div class="profile-section">
                        <h3>Basic Information</h3>
                        <p><span class="label">Symbol:</span> <span class="symbol">${data.symbol || 'N/A'}</span></p>
                        <p><span class="label">Exchange:</span> ${data.exchange || 'N/A'}</p>
                        <p><span class="label">Industry:</span> ${data.industry || 'N/A'}</p>
                        <p><span class="label">Sector:</span> ${data.sector || 'N/A'}</p>
                        <p><span class="label">Country:</span> ${data.country || 'N/A'}</p>
                        <p><span class="label">Currency:</span> ${data.currency || 'N/A'}</p>
                    </div>
                    <div class="profile-section">
                        <h3>Financial Metrics</h3>
                        <p><span class="label">Market Cap:</span> <span class="number">${formatNumber(data.mktCap)}</span></p>
                        <p><span class="label">Beta:</span> ${formatNumber(data.beta)}</p>
                        <p><span class="label">52 Week High:</span> <span class="number">${formatNumber(data.range?.split('-')[1])}</span></p>
                        <p><span class="label">52 Week Low:</span> <span class="number">${formatNumber(data.range?.split('-')[0])}</span></p>
                        <p><span class="label">Price:</span> <span class="number">${formatNumber(data.price)}</span></p>
                        <p><span class="label">Volume:</span> <span class="number">${formatNumber(data.volume)}</span></p>
                    </div>
                    <div class="profile-section">
                        <h3>Company Details</h3>
                        <p><span class="label">CEO:</span> ${data.ceo || 'N/A'}</p>
                        <p><span class="label">Employees:</span> ${formatNumber(data.employees)}</p>
                        <p><span class="label">Founded:</span> ${data.ipoDate || 'N/A'}</p>
                        <p><span class="label">Website:</span> <a href="${data.website || '#'}" target="_blank">${data.website || 'N/A'}</a></p>
                        <p><span class="label">Address:</span> ${data.address || 'N/A'}</p>
                        <p><span class="label">City:</span> ${data.city || 'N/A'}</p>
                        <p><span class="label">State:</span> ${data.state || 'N/A'}</p>
                    </div>
                </div>
            </div>
        `;
    }

    // Format earnings data
    function formatEarningsData(data) {
        if (!Array.isArray(data) || data.length === 0) return 'No earnings data available';
        
        // Log the raw data
        console.log('Raw earnings data:', data);
        
        // Sort data by date ascending (oldest to newest)
        const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
        
        // Log the first row to see its structure
        if (sortedData.length > 0) {
            console.log('First row data:', sortedData[0]);
            console.log('First row keys:', Object.keys(sortedData[0]));
        }
        
        return `
            <table class="output-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Symbol</th>
                        <th>EPS</th>
                        <th>EPS Estimated</th>
                        <th>Time</th>
                        <th>Revenue</th>
                        <th>Revenue Estimated</th>
                        <th>Updated From</th>
                        <th>Fiscal Date Ending</th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedData.map(row => `
                        <tr>
                            <td class="date">${formatDate(row.date, 'daily')}</td>
                            <td class="symbol">${row.symbol}</td>
                            <td class="number">${row.eps || 'N/A'}</td>
                            <td class="number">${row.epsEstimated || 'N/A'}</td>
                            <td>${row.time || 'N/A'}</td>
                            <td class="number">${formatNumber(row.revenue)}</td>
                            <td class="number">${formatNumber(row.revenueEstimated)}</td>
                            <td class="date">${formatDate(row.updatedFromDate, 'daily')}</td>
                            <td class="date">${formatDate(row.fiscalDateEnding, 'daily')}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // Format intraday data
    function formatIntradayData(data) {
        if (!Array.isArray(data) || data.length === 0) return 'No intraday data available';
        
        // Sort data by date ascending (oldest to newest)
        const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
        
        // Check if this is daily data (period === '1day')
        const isDaily = period.value === '1day';
        
        return `
            <table class="output-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Open</th>
                        <th>High</th>
                        <th>Low</th>
                        <th>Close</th>
                        <th>Volume</th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedData.map(row => `
                        <tr>
                            <td class="date">${formatDate(row.date, isDaily ? 'daily' : 'intraday')}</td>
                            <td class="number">${formatNumber(row.open)}</td>
                            <td class="number">${formatNumber(row.high)}</td>
                            <td class="number">${formatNumber(row.low)}</td>
                            <td class="number">${formatNumber(row.close)}</td>
                            <td class="number">${formatVolume(row.volume)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // Format dividends data
    function formatDividendsData(data) {
        if (!Array.isArray(data) || data.length === 0) return 'No dividends data available';
        
        // Sort data by date ascending (oldest to newest)
        const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
        
        return `
            <table class="output-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Dividend</th>
                        <th>Stock Price</th>
                        <th>Trailing Yield</th>
                        <th>Current Yield</th>
                        <th>Record Date</th>
                        <th>Payment Date</th>
                        <th>Declaration Date</th>
                    </tr>
                </thead>
                <tbody>
                    ${sortedData.map(row => `
                        <tr>
                            <td class="date">${formatDate(row.date, 'daily')}</td>
                            <td class="number">${formatNumber(row.dividend)}</td>
                            <td class="number">${formatNumber(row.stockPrice)}</td>
                            <td class="number">${formatNumber(row.trailYield)}%</td>
                            <td class="number">${formatNumber(row.curYield)}%</td>
                            <td class="date">${formatDate(row.recordDate, 'daily')}</td>
                            <td class="date">${formatDate(row.paymentDate, 'daily')}</td>
                            <td class="date">${formatDate(row.declarationDate, 'daily')}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // Format search data
    function formatSearchData(data) {
        if (!Array.isArray(data) || data.length === 0) return 'No search results available';
        
        return `
            <table class="output-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Name</th>
                        <th>Exchange</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(row => `
                        <tr>
                            <td class="symbol">${row.symbol}</td>
                            <td>${row.name}</td>
                            <td>${row.exchange}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // Helper functions
    function formatNumber(num) {
        if (num === null || num === undefined) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            maximumFractionDigits: 2,
            minimumFractionDigits: 2
        }).format(num);
    }

    function formatVolume(num) {
        if (num === null || num === undefined) return 'N/A';
        return new Intl.NumberFormat('en-US', {
            maximumFractionDigits: 0,
            minimumFractionDigits: 0
        }).format(num);
    }

    function formatDate(dateStr, dataType = 'daily') {
        if (!dateStr) return 'N/A';
        
        // Create date object from UTC string
        const date = new Date(dateStr);
        
        if (dataType === 'intraday') {
            // Add 5 hours to convert from UTC to EST
            date.setHours(date.getHours() + 5);
            
            // Format the date and time
            const formattedDate = date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
            
            const formattedTime = date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
            
            return `${formattedDate}, ${formattedTime} EST`;
        } else {
            // For daily data, show just the date without time
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        }
    }

    // Handle form submission
    searchBtn.addEventListener('click', async () => {
        const symbol = stockSymbol.value.trim().toUpperCase();
        
        if (!symbol) {
            errorMessage.textContent = 'Please enter a stock symbol';
            return;
        }

        // Show loading state
        searchBtn.disabled = true;
        searchBtn.innerHTML = '<span class="loading"></span>Loading...';
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
                output.innerHTML = formatData(data.data, functionSelector.value);
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