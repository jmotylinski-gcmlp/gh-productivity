/**
 * GitHub Productivity Tracker - Single User Dashboard
 */

let chart = null;
let allUsersData = {};

document.addEventListener('DOMContentLoaded', () => {
    // Set default end date to current month
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    document.getElementById('endDate').value = currentMonth;

    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('searchBtn').addEventListener('click', loadUserData);

    // Allow Enter key to trigger search
    document.getElementById('username').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') loadUserData();
    });
}

function getDateRange() {
    const startDate = document.getElementById('startDate').value || '2023-01';
    const endDate = document.getElementById('endDate').value || getCurrentMonth();
    return { startDate, endDate };
}

function getCurrentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

async function loadUserData() {
    const container = document.getElementById('mainContent');
    const username = document.getElementById('username').value.trim();

    if (!username) {
        container.innerHTML = `<div class="error-message">Please enter a username.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading data for ${formatUsername(username)}...</p>
        </div>
    `;

    try {
        const resp = await fetch('/api/users/all/stats');
        allUsersData = await resp.json();

        if (allUsersData.error) {
            container.innerHTML = `<div class="error-message">${allUsersData.error}</div>`;
            return;
        }

        const userData = allUsersData[username];
        if (!userData) {
            container.innerHTML = `<div class="error-message">User "${username}" not found in cache.<br><br>Make sure the user is configured in config/users.json.</div>`;
            return;
        }

        renderUserStats(userData, username);
    } catch (error) {
        console.error('Error loading data:', error);
        container.innerHTML = `<div class="error-message">Failed to load data: ${error.message}</div>`;
    }
}

function renderUserStats(userData, username) {
    const container = document.getElementById('mainContent');
    const dailyStats = userData.daily_stats || {};
    const monthlyData = aggregateByMonth(dailyStats);

    // Get date range and filter months
    const { startDate, endDate } = getDateRange();
    const months = Object.keys(monthlyData)
        .filter(m => m >= startDate && m <= endDate)
        .sort();

    if (months.length === 0) {
        container.innerHTML = '<div class="error-message">No data available for the selected date range.</div>';
        return;
    }

    // Calculate total
    const total = months.reduce((sum, month) => sum + monthlyData[month].absolute, 0);

    // Build HTML with chart section and table
    container.innerHTML = `
        <div class="chart-section" style="margin-bottom: 24px;">
            <div class="chart-container">
                <canvas id="linesChart"></canvas>
            </div>
        </div>
        <div class="comparison-section">
            <h2>Lines Changed by Month</h2>
            <p class="table-subtitle">Total lines touched (additions + deletions)</p>
            <div class="table-wrapper">
                <table class="comparison-table single-user-table">
                    <thead>
                        <tr>
                            <th class="month-col">Month</th>
                            <th class="user-col">Lines Changed</th>
                            <th class="user-col">Additions</th>
                            <th class="user-col">Deletions</th>
                            <th class="user-col">Commits</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="totals-row">
                            <td><strong>TOTAL</strong></td>
                            <td><strong>${formatNumber(total)}</strong></td>
                            <td><strong>${formatNumber(months.reduce((sum, m) => sum + monthlyData[m].additions, 0))}</strong></td>
                            <td><strong>${formatNumber(months.reduce((sum, m) => sum + monthlyData[m].deletions, 0))}</strong></td>
                            <td><strong>${formatNumber(months.reduce((sum, m) => sum + monthlyData[m].commits, 0))}</strong></td>
                        </tr>
                        ${months.slice().reverse().map(month => {
                            const data = monthlyData[month];
                            return `
                                <tr>
                                    <td class="month-cell">${formatMonth(month)}</td>
                                    <td>${formatNumber(data.absolute)}</td>
                                    <td class="positive">${formatNumber(data.additions)}</td>
                                    <td class="negative">${formatNumber(data.deletions)}</td>
                                    <td>${formatNumber(data.commits)}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    // Render chart
    renderChart(months, monthlyData, username);
}

function renderChart(months, monthlyData, username) {
    const labels = months.map(formatMonth);
    const values = months.map(m => monthlyData[m].absolute);

    // Calculate trend line using linear regression
    const trendLine = calculateTrendLine(values);

    // Build annotations for tool enablement markers
    const annotations = buildAnnotations(months);

    const ctx = document.getElementById('linesChart').getContext('2d');

    if (chart) {
        chart.destroy();
    }

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
            monthly[month] = { absolute: 0, commits: 0, additions: 0, deletions: 0 };
        }
        monthly[month].absolute += stats.additions + stats.deletions;
        monthly[month].commits += stats.commits;
        monthly[month].additions += stats.additions;
        monthly[month].deletions += stats.deletions;
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
    const targetIndex = months.indexOf(targetMonth);
    if (targetIndex !== -1) {
        return targetIndex;
    }

    if (targetMonth < months[0]) {
        const firstMonth = months[0];
        const monthsDiff = getMonthsDifference(targetMonth, firstMonth);
        return -monthsDiff;
    } else if (targetMonth > months[months.length - 1]) {
        const lastMonth = months[months.length - 1];
        const monthsDiff = getMonthsDifference(lastMonth, targetMonth);
        return months.length - 1 + monthsDiff;
    }

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

function formatNumber(num) {
    return num.toLocaleString();
}
