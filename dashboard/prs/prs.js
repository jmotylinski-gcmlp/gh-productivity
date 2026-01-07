/**
 * Productivity Tracker - PR Metrics Dashboard
 */

let timeOpenChart = null;
let timeToReviewChart = null;
let repositories = [];

document.addEventListener('DOMContentLoaded', async () => {
    // Set default end date to current month
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    document.getElementById('endDate').value = currentMonth;

    // Load repositories
    await loadRepositories();

    setupEventListeners();
});

async function loadRepositories() {
    const select = document.getElementById('repository');
    const container = document.getElementById('mainContent');

    try {
        const resp = await fetch('/api/pr/repositories');
        repositories = await resp.json();

        if (repositories.length === 0) {
            select.innerHTML = '<option value="">No PR data found - run pr_fetcher first</option>';
            container.innerHTML = `
                <div class="error-message">
                    No PR data found. Run <code>python3 -m src.github.pr_fetcher</code> to fetch PR data.
                </div>
            `;
            return;
        }

        select.innerHTML = '<option value="">Select a repository...</option>' +
            repositories.map(repo => `<option value="${repo}">${repo}</option>`).join('');

        container.innerHTML = `
            <div class="chart-section">
                <p style="text-align: center; color: #666; padding: 40px;">
                    Select a repository to view PR metrics.
                </p>
            </div>
        `;

        console.log(`Loaded ${repositories.length} repositories`);
    } catch (error) {
        console.error('Failed to load repositories:', error);
        select.innerHTML = '<option value="">Failed to load repositories</option>';
        container.innerHTML = `<div class="error-message">Failed to load repositories: ${error.message}</div>`;
    }
}

function setupEventListeners() {
    document.getElementById('searchBtn').addEventListener('click', loadPRData);

    // Allow Enter key to trigger search
    document.getElementById('repository').addEventListener('change', loadPRData);
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

async function loadPRData() {
    const container = document.getElementById('mainContent');
    const repository = document.getElementById('repository').value;

    if (!repository) {
        container.innerHTML = `<div class="error-message">Please select a repository.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading PR data for ${repository}...</p>
        </div>
    `;

    try {
        // Fetch PR stats and monthly data in parallel
        const [statsResp, monthlyResp] = await Promise.all([
            fetch(`/api/pr/stats?repo=${encodeURIComponent(repository)}`),
            fetch(`/api/pr/stats/monthly?repo=${encodeURIComponent(repository)}`)
        ]);

        const stats = await statsResp.json();
        const monthlyData = await monthlyResp.json();

        if (stats.error || monthlyData.error) {
            throw new Error(stats.error || monthlyData.error);
        }

        renderDashboard(stats, monthlyData, repository);
    } catch (error) {
        console.error('Error loading PR data:', error);
        container.innerHTML = `<div class="error-message">Failed to load PR data: ${error.message}</div>`;
    }
}

function renderDashboard(stats, monthlyData, repository) {
    const container = document.getElementById('mainContent');
    const { startDate, endDate } = getDateRange();

    // Filter months by date range
    const months = (monthlyData.months || [])
        .filter(m => m.month >= startDate && m.month <= endDate)
        .sort((a, b) => a.month.localeCompare(b.month));

    if (months.length === 0) {
        container.innerHTML = `
            <div class="error-message">
                No PR data found for ${repository} in the selected date range.
            </div>
        `;
        return;
    }

    // Calculate totals
    const totalPRs = months.reduce((sum, m) => sum + m.pr_count, 0);
    const avgTimeOpen = months.reduce((sum, m) => sum + (m.avg_time_open_hours || 0), 0) / months.length;
    const avgTimeToReview = months.reduce((sum, m) => sum + (m.avg_time_to_first_review_hours || 0), 0) / months.length;

    let html = `
        <!-- Summary Stats -->
        <div class="chart-section" style="margin-bottom: 24px;">
            <h2>Summary: ${formatRepoName(repository)}</h2>
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; margin-top: 20px;">
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #1f6feb;">${formatNumber(totalPRs)}</div>
                    <div style="color: #666;">Total PRs</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #28a745;">${formatHours(avgTimeOpen)}</div>
                    <div style="color: #666;">Avg Time Open</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #6f42c1;">${formatHours(avgTimeToReview)}</div>
                    <div style="color: #666;">Avg Time to First Review</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 2em; font-weight: bold; color: #fd7e14;">${(months.reduce((sum, m) => sum + m.avg_reviewer_count, 0) / months.length).toFixed(1)}</div>
                    <div style="color: #666;">Avg Reviewers</div>
                </div>
            </div>
        </div>

        <!-- Time Open Chart -->
        <div class="chart-section" style="margin-bottom: 24px;">
            <h2 title="Trend line downward is good (faster PR turnaround)" style="cursor: help;">Average PR Time Open by Month</h2>
            <div class="chart-container">
                <canvas id="timeOpenChart"></canvas>
            </div>
        </div>

        <!-- Time to First Review Chart -->
        <div class="chart-section" style="margin-bottom: 24px;">
            <h2 title="Trend line downward is good (faster review response)" style="cursor: help;">Average Time to First Review by Month</h2>
            <div class="chart-container">
                <canvas id="timeToReviewChart"></canvas>
            </div>
        </div>

        <!-- Data Table -->
        <details class="collapsible-section" style="margin-bottom: 24px;">
            <summary class="section-header">
                <span>PR Metrics by Month - Data Table</span>
                <span class="toggle-icon"></span>
            </summary>
            <div class="section-content">
                <div class="table-wrapper">
                    <table class="comparison-table single-user-table">
                        <thead>
                            <tr>
                                <th class="month-col">Month</th>
                                <th class="user-col">PRs</th>
                                <th class="user-col">Avg Time Open</th>
                                <th class="user-col">Median Time Open</th>
                                <th class="user-col">Avg Time to Review</th>
                                <th class="user-col">Avg Reviewers</th>
                                <th class="user-col">Avg Additions</th>
                                <th class="user-col">Avg Deletions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="totals-row">
                                <td><strong>TOTAL/AVG</strong></td>
                                <td><strong>${formatNumber(totalPRs)}</strong></td>
                                <td><strong>${formatHours(avgTimeOpen)}</strong></td>
                                <td><strong>-</strong></td>
                                <td><strong>${formatHours(avgTimeToReview)}</strong></td>
                                <td><strong>${(months.reduce((sum, m) => sum + m.avg_reviewer_count, 0) / months.length).toFixed(1)}</strong></td>
                                <td><strong>${formatNumber(Math.round(months.reduce((sum, m) => sum + m.avg_additions, 0) / months.length))}</strong></td>
                                <td><strong>${formatNumber(Math.round(months.reduce((sum, m) => sum + m.avg_deletions, 0) / months.length))}</strong></td>
                            </tr>
                            ${months.slice().reverse().map(data => `
                                <tr>
                                    <td class="month-cell">${formatMonth(data.month)}</td>
                                    <td>${formatNumber(data.pr_count)}</td>
                                    <td>${formatHours(data.avg_time_open_hours)}</td>
                                    <td>${formatHours(data.median_time_open_hours)}</td>
                                    <td>${formatHours(data.avg_time_to_first_review_hours)}</td>
                                    <td>${data.avg_reviewer_count.toFixed(1)}</td>
                                    <td class="positive">${formatNumber(Math.round(data.avg_additions))}</td>
                                    <td class="negative">${formatNumber(Math.round(data.avg_deletions))}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </details>
    `;

    container.innerHTML = html;

    // Render charts after DOM is updated
    const monthLabels = months.map(m => m.month);
    renderTimeOpenChart(monthLabels, months);
    renderTimeToReviewChart(monthLabels, months);
}

function renderTimeOpenChart(monthLabels, monthsData) {
    const labels = monthLabels.map(formatMonth);
    const values = monthsData.map(m => m.avg_time_open_hours || 0);
    const trendLine = calculateTrendLine(values);
    const annotations = buildAnnotations(monthLabels);

    const ctx = document.getElementById('timeOpenChart').getContext('2d');

    if (timeOpenChart) {
        timeOpenChart.destroy();
    }

    timeOpenChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Avg Time Open (hours)',
                    data: values,
                    backgroundColor: 'rgba(40, 167, 69, 0.7)',
                    borderColor: 'rgba(40, 167, 69, 1)',
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
                    text: 'Average PR Time Open by Month',
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

function renderTimeToReviewChart(monthLabels, monthsData) {
    const labels = monthLabels.map(formatMonth);
    const values = monthsData.map(m => m.avg_time_to_first_review_hours || 0);
    const trendLine = calculateTrendLine(values);
    const annotations = buildAnnotations(monthLabels);

    const ctx = document.getElementById('timeToReviewChart').getContext('2d');

    if (timeToReviewChart) {
        timeToReviewChart.destroy();
    }

    timeToReviewChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Avg Time to First Review (hours)',
                    data: values,
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
                    text: 'Average Time to First Review by Month',
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

function formatRepoName(repo) {
    // Extract just the repo name from org/repo format
    const parts = repo.split('/');
    return parts.length > 1 ? parts[1] : repo;
}

function formatMonth(monthStr) {
    const [year, month] = monthStr.split('-');
    const date = new Date(year, parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
}

function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString();
}

function formatHours(hours) {
    if (hours === null || hours === undefined || isNaN(hours)) return '-';
    if (hours === 0) return '0h';
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${hours.toFixed(1)}h`;
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    if (remainingHours < 1) return `${days}d`;
    return `${days}d ${remainingHours.toFixed(0)}h`;
}
