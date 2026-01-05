/**
 * GitHub Productivity Tracker - Individual User Stats
 */

let chart = null;

document.addEventListener('DOMContentLoaded', () => {
    const username = getUrlParam('username');
    if (!username) {
        showError('No username provided. Add ?username=your-username to the URL.');
        return;
    }

    document.getElementById('pageTitle').textContent = `${formatUsername(username)} - Stats`;
    loadUserData(username);
});

function getUrlParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

function getDateRange() {
    const startDate = getUrlParam('startDate') || '2023-01';
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    const endDate = getUrlParam('endDate') || currentMonth;
    return { startDate, endDate };
}

async function loadUserData(username) {
    const container = document.getElementById('mainContent');
    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading data for ${formatUsername(username)}...</p>
        </div>
    `;

    try {
        const resp = await fetch('/api/users/all/stats');
        const allUsersData = await resp.json();

        if (allUsersData.error) {
            showError(allUsersData.error);
            return;
        }

        const userData = allUsersData[username];
        if (!userData) {
            showError(`User "${username}" not found.`);
            return;
        }

        renderChart(userData, username);
    } catch (error) {
        console.error('Error loading data:', error);
        showError(`Failed to load data: ${error.message}`);
    }
}

function renderChart(userData, username) {
    const container = document.getElementById('mainContent');
    container.innerHTML = `
        <div class="chart-section">
            <div class="chart-container">
                <canvas id="linesChart"></canvas>
            </div>
        </div>
    `;

    const dailyStats = userData.daily_stats || {};
    const monthlyData = aggregateByMonth(dailyStats);

    // Get date range from URL params and filter
    const { startDate, endDate } = getDateRange();
    const months = Object.keys(monthlyData)
        .filter(m => m >= startDate && m <= endDate)
        .sort();

    if (months.length === 0) {
        showError('No data available for the selected date range.');
        return;
    }

    const labels = months.map(formatMonth);
    const values = months.map(m => monthlyData[m]);

    // Calculate trend line using linear regression
    const trendLine = calculateTrendLine(values);

    // Build annotations for tool enablement markers
    const annotations = buildAnnotations(months);

    const ctx = document.getElementById('linesChart').getContext('2d');
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Lines Changed',
                    data: values,
                    backgroundColor: 'rgba(31, 111, 235, 0.7)',
                    borderColor: 'rgba(31, 111, 235, 1)',
                    borderWidth: 1,
                    order: 2
                },
                {
                    label: 'Trend',
                    data: trendLine,
                    type: 'line',
                    borderColor: 'rgba(220, 53, 69, 0.8)',
                    borderWidth: 3,
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: `Total Lines Changed by Month - ${formatUsername(username)}`,
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            return `${context.dataset.label}: ${value.toLocaleString()}`;
                        }
                    }
                },
                annotation: {
                    annotations: annotations
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Lines Changed (Additions + Deletions)'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Month'
                    }
                }
            }
        }
    });
}

function aggregateByMonth(dailyStats) {
    const monthly = {};

    for (const [date, stats] of Object.entries(dailyStats)) {
        const month = date.substring(0, 7); // YYYY-MM
        if (!monthly[month]) {
            monthly[month] = 0;
        }
        monthly[month] += stats.additions + stats.deletions;
    }

    return monthly;
}

function calculateTrendLine(values) {
    const n = values.length;
    if (n === 0) return [];

    // Calculate linear regression: y = mx + b
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

    for (let i = 0; i < n; i++) {
        sumX += i;
        sumY += values[i];
        sumXY += i * values[i];
        sumX2 += i * i;
    }

    const m = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const b = (sumY - m * sumX) / n;

    // Generate trend line values
    return values.map((_, i) => Math.max(0, m * i + b));
}

function getAnnotationPosition(targetMonth, months) {
    // Find the position of targetMonth relative to the months array
    // targetMonth format: 'YYYY-MM'
    const targetIndex = months.indexOf(targetMonth);
    if (targetIndex !== -1) {
        return targetIndex;
    }

    // If not found, calculate position based on chronological order
    if (targetMonth < months[0]) {
        // Target is before the first month - calculate how many months before
        const firstMonth = months[0];
        const monthsDiff = getMonthsDifference(targetMonth, firstMonth);
        return -monthsDiff;
    } else if (targetMonth > months[months.length - 1]) {
        // Target is after the last month
        const lastMonth = months[months.length - 1];
        const monthsDiff = getMonthsDifference(lastMonth, targetMonth);
        return months.length - 1 + monthsDiff;
    }

    // Target month falls within range but has no data - find closest position
    for (let i = 0; i < months.length - 1; i++) {
        if (targetMonth > months[i] && targetMonth < months[i + 1]) {
            return i + 0.5;
        }
    }

    return 0;
}

function getMonthsDifference(startMonth, endMonth) {
    const [startYear, startMo] = startMonth.split('-').map(Number);
    const [endYear, endMo] = endMonth.split('-').map(Number);
    return (endYear - startYear) * 12 + (endMo - startMo);
}

function buildAnnotations(months) {
    const annotations = {};

    // Tool enablement markers
    const markers = [
        { month: '2023-07', label: 'GitHub Copilot Enabled', color: 'rgba(40, 167, 69, 0.8)' },
        { month: '2025-02', label: 'Cursor Enabled', color: 'rgba(156, 39, 176, 0.8)' }
    ];

    markers.forEach((marker, index) => {
        const xPos = getAnnotationPosition(marker.month, months);

        // Only show if within reasonable range of chart
        if (xPos >= -1 && xPos <= months.length) {
            annotations[`line${index}`] = {
                type: 'line',
                xMin: xPos,
                xMax: xPos,
                borderColor: marker.color,
                borderWidth: 2,
                borderDash: [6, 4],
                label: {
                    display: true,
                    content: marker.label,
                    position: 'end',
                    backgroundColor: marker.color,
                    color: 'white',
                    font: {
                        size: 11,
                        weight: 'bold'
                    },
                    padding: 4
                }
            };
        }
    });

    return annotations;
}

function formatUsername(username) {
    return username.replace(/-gcmlp$/, '').replace(/-gcm$/, '');
}

function formatMonth(monthStr) {
    const [year, month] = monthStr.split('-');
    const date = new Date(year, parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
}

function showError(message) {
    const container = document.getElementById('mainContent');
    container.innerHTML = `<div class="error-message">${message}</div>`;
}
