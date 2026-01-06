/**
 * Productivity Tracker - Single User Dashboard
 */

let githubChart = null;
let jiraChart = null;
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
    document.getElementById('jiraEmail').addEventListener('keypress', (e) => {
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
    const jiraEmail = document.getElementById('jiraEmail').value.trim();

    if (!username && !jiraEmail) {
        container.innerHTML = `<div class="error-message">Please enter a GitHub username or JIRA email.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading data...</p>
        </div>
    `;

    try {
        // Fetch GitHub and JIRA data in parallel
        const [githubResp, jiraResp] = await Promise.all([
            username ? fetch('/api/users/all/stats') : Promise.resolve(null),
            jiraEmail ? fetch(`/api/jira/stats/monthly?email=${encodeURIComponent(jiraEmail)}`) : Promise.resolve(null)
        ]);

        let githubData = null;
        let jiraData = null;

        if (githubResp) {
            allUsersData = await githubResp.json();
            if (!allUsersData.error) {
                githubData = allUsersData[username];
            }
        }

        if (jiraResp) {
            jiraData = await jiraResp.json();
            if (jiraData.error) {
                jiraData = null;
            }
        }

        renderDashboard(githubData, jiraData, username, jiraEmail);
    } catch (error) {
        console.error('Error loading data:', error);
        container.innerHTML = `<div class="error-message">Failed to load data: ${error.message}</div>`;
    }
}

function renderDashboard(githubData, jiraData, username, jiraEmail) {
    const container = document.getElementById('mainContent');
    const { startDate, endDate } = getDateRange();

    let html = '';

    // JIRA section (first)
    if (jiraEmail && jiraData && Object.keys(jiraData).length > 0) {
        const jiraMonths = Object.keys(jiraData)
            .filter(m => m >= startDate && m <= endDate)
            .sort();

        if (jiraMonths.length > 0) {
            const totalCycles = jiraMonths.reduce((sum, m) => sum + jiraData[m].cycles, 0);
            const allMeanHours = jiraMonths.map(m => jiraData[m].mean_hours);
            const overallMean = allMeanHours.reduce((a, b) => a + b, 0) / allMeanHours.length;

            html += `
                <div class="chart-section" style="margin-bottom: 24px;">
                    <h2>JIRA: Cycle Time by Month</h2>
                    <div class="chart-container">
                        <canvas id="jiraChart"></canvas>
                    </div>
                </div>
                <details class="collapsible-section" style="margin-bottom: 24px;">
                    <summary class="section-header">
                        <span>JIRA: Cycle Time by Month - Data Table</span>
                        <span class="toggle-icon"></span>
                    </summary>
                    <div class="section-content">
                        <p class="table-subtitle">Mean time from "In Progress" to next state (in hours)</p>
                        <div class="table-wrapper">
                            <table class="comparison-table single-user-table">
                                <thead>
                                    <tr>
                                        <th class="month-col">Month</th>
                                        <th class="user-col">Cycles</th>
                                        <th class="user-col">Mean (hrs)</th>
                                        <th class="user-col">Median (hrs)</th>
                                        <th class="user-col">Min (hrs)</th>
                                        <th class="user-col">Max (hrs)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="totals-row">
                                        <td><strong>TOTAL/AVG</strong></td>
                                        <td><strong>${formatNumber(totalCycles)}</strong></td>
                                        <td><strong>${formatHours(overallMean)}</strong></td>
                                        <td><strong>-</strong></td>
                                        <td><strong>-</strong></td>
                                        <td><strong>-</strong></td>
                                    </tr>
                                    ${jiraMonths.slice().reverse().map(month => {
                                        const data = jiraData[month];
                                        return `
                                            <tr>
                                                <td class="month-cell">${formatMonth(month)}</td>
                                                <td>${formatNumber(data.cycles)}</td>
                                                <td>${formatHours(data.mean_hours)}</td>
                                                <td>${formatHours(data.median_hours)}</td>
                                                <td>${formatHours(data.min_hours)}</td>
                                                <td>${formatHours(data.max_hours)}</td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </details>
            `;
        }
    } else if (jiraEmail) {
        html += `<div class="error-message" style="margin-bottom: 24px;">No JIRA cycle data found for "${jiraEmail}".</div>`;
    }

    // GitHub section (second)
    if (username && githubData) {
        const dailyStats = githubData.daily_stats || {};
        const monthlyData = aggregateByMonth(dailyStats);
        const months = Object.keys(monthlyData)
            .filter(m => m >= startDate && m <= endDate)
            .sort();

        if (months.length > 0) {
            const total = months.reduce((sum, month) => sum + monthlyData[month].absolute, 0);

            html += `
                <div class="chart-section" style="margin-bottom: 24px;">
                    <h2>GitHub: Lines Changed by Month</h2>
                    <div class="chart-container">
                        <canvas id="githubChart"></canvas>
                    </div>
                </div>
                <details class="collapsible-section" style="margin-bottom: 24px;">
                    <summary class="section-header">
                        <span>GitHub: Lines Changed by Month - Data Table</span>
                        <span class="toggle-icon"></span>
                    </summary>
                    <div class="section-content">
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
                </details>
            `;
        }
    } else if (username) {
        html += `<div class="error-message">GitHub user "${username}" not found in cache.</div>`;
    }

    if (!html) {
        html = '<div class="error-message">No data available for the selected criteria.</div>';
    }

    container.innerHTML = html;

    // Render charts after DOM is updated
    if (jiraEmail && jiraData && Object.keys(jiraData).length > 0) {
        const jiraMonths = Object.keys(jiraData)
            .filter(m => m >= startDate && m <= endDate)
            .sort();
        if (jiraMonths.length > 0) {
            renderJiraChart(jiraMonths, jiraData, jiraEmail);
        }
    }

    if (username && githubData) {
        const dailyStats = githubData.daily_stats || {};
        const monthlyData = aggregateByMonth(dailyStats);
        const months = Object.keys(monthlyData)
            .filter(m => m >= startDate && m <= endDate)
            .sort();
        if (months.length > 0) {
            renderGitHubChart(months, monthlyData, username);
        }
    }
}

function renderGitHubChart(months, monthlyData, username) {
    const labels = months.map(formatMonth);
    const values = months.map(m => monthlyData[m].absolute);
    const trendLine = calculateTrendLine(values);
    const annotations = buildAnnotations(months);

    const ctx = document.getElementById('githubChart').getContext('2d');

    if (githubChart) {
        githubChart.destroy();
    }

    githubChart = new Chart(ctx, {
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
                legend: { position: 'top' },
                title: {
                    display: true,
                    text: `GitHub: Lines Changed by Month - ${formatUsername(username)}`,
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toLocaleString()}`;
                        }
                    }
                },
                annotation: { annotations: annotations }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Lines Changed' },
                    ticks: { callback: value => value.toLocaleString() }
                },
                x: { title: { display: true, text: 'Month' } }
            }
        }
    });
}

function renderJiraChart(months, jiraData, jiraEmail) {
    const labels = months.map(formatMonth);
    const meanValues = months.map(m => jiraData[m].mean_hours);
    const trendLine = calculateTrendLine(meanValues);
    const annotations = buildAnnotations(months);

    const ctx = document.getElementById('jiraChart').getContext('2d');

    if (jiraChart) {
        jiraChart.destroy();
    }

    jiraChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Mean Cycle Time (hours)',
                    data: meanValues,
                    backgroundColor: 'rgba(111, 66, 193, 0.7)',
                    borderColor: 'rgba(111, 66, 193, 1)',
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
                legend: { position: 'top' },
                title: {
                    display: true,
                    text: `JIRA: Mean Cycle Time by Month - ${formatEmail(jiraEmail)}`,
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatHours(context.raw)}`;
                        }
                    }
                },
                annotation: { annotations: annotations }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Hours' },
                    ticks: { callback: value => formatHours(value) }
                },
                x: { title: { display: true, text: 'Month' } }
            }
        }
    });
}

function aggregateByMonth(dailyStats) {
    const monthly = {};

    for (const [date, stats] of Object.entries(dailyStats)) {
        const month = date.substring(0, 7);
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

    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;

    for (let i = 0; i < n; i++) {
        sumX += i;
        sumY += values[i];
        sumXY += i * values[i];
        sumX2 += i * i;
    }

    const m = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    const b = (sumY - m * sumX) / n;

    return values.map((_, i) => Math.max(0, m * i + b));
}

function getAnnotationPosition(targetMonth, months) {
    const targetIndex = months.indexOf(targetMonth);
    if (targetIndex !== -1) return targetIndex;

    if (targetMonth < months[0]) {
        const monthsDiff = getMonthsDifference(targetMonth, months[0]);
        return -monthsDiff;
    } else if (targetMonth > months[months.length - 1]) {
        const monthsDiff = getMonthsDifference(months[months.length - 1], targetMonth);
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
    const markers = [
        { month: '2023-07', label: 'GitHub Copilot Enabled', color: 'rgba(40, 167, 69, 0.8)' },
        { month: '2025-02', label: 'Cursor Enabled', color: 'rgba(156, 39, 176, 0.8)' }
    ];

    markers.forEach((marker, index) => {
        const xPos = getAnnotationPosition(marker.month, months);

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
                    font: { size: 11, weight: 'bold' },
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

function formatEmail(email) {
    if (!email) return 'Unknown';
    const name = email.split('@')[0];
    return name.replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatMonth(monthStr) {
    const [year, month] = monthStr.split('-');
    const date = new Date(year, parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
}

function formatNumber(num) {
    return num.toLocaleString();
}

function formatHours(hours) {
    if (hours === 0) return '0h';
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${hours.toFixed(1)}h`;
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    if (remainingHours < 1) return `${days}d`;
    return `${days}d ${remainingHours.toFixed(0)}h`;
}
