/**
 * GitHub Productivity Tracker Dashboard
 */

let dailyStats = {};
let summary = {};

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', refreshData);
}

async function loadData() {
    try {
        // Load summary data
        const summaryResp = await fetch('/api/summary');
        const summaryData = await summaryResp.json();
        summary = summaryData.summary;

        // Load daily stats
        const statsResp = await fetch('/api/daily-stats');
        dailyStats = await statsResp.json();

        // Update UI
        updateSummary(summary);
        updateTable(dailyStats);
        updateChart(dailyStats);
        updateLastUpdated(summaryData.updated_at);
    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load data');
    }
}

async function refreshData() {
    try {
        const btn = document.getElementById('refreshBtn');
        btn.disabled = true;
        btn.textContent = 'Refreshing...';

        const resp = await fetch('/api/refresh', { method: 'POST' });
        const data = await resp.json();

        if (data.success) {
            await loadData();
            showSuccess('Data refreshed successfully');
        } else {
            showError(data.error || 'Failed to refresh data');
        }
    } catch (error) {
        console.error('Error refreshing data:', error);
        showError('Failed to refresh data');
    } finally {
        const btn = document.getElementById('refreshBtn');
        btn.disabled = false;
        btn.textContent = 'Refresh Data';
    }
}

function updateSummary(summary) {
    document.getElementById('totalNetLines').textContent =
        formatNumber(summary.net_lines || 0);
    document.getElementById('totalCommits').textContent =
        formatNumber(summary.total_commits || 0);
    document.getElementById('avgDailyLines').textContent =
        formatNumber(Math.round(summary.avg_daily_lines || 0));
    document.getElementById('daysWithCommits').textContent =
        formatNumber(summary.total_days || 0);
}

function updateTable(dailyStats) {
    const tbody = document.getElementById('statsTableBody');
    tbody.innerHTML = '';

    // Sort dates in reverse chronological order
    const dates = Object.keys(dailyStats).sort().reverse();

    dates.forEach(date => {
        const stats = dailyStats[date];
        const repos = Array.isArray(stats.repositories) ? stats.repositories.join(', ') : '';
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${date}</td>
            <td>${stats.commits}</td>
            <td style="color: green;">+${stats.additions}</td>
            <td style="color: red;">-${stats.deletions}</td>
            <td style="font-weight: bold; color: ${stats.net_lines >= 0 ? 'green' : 'red'};">
                ${stats.net_lines >= 0 ? '+' : ''}${stats.net_lines}
            </td>
            <td class="repos-cell">${repos}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateChart(dailyStats) {
    // Simple chart implementation - you may want to use Chart.js
    // For now, we'll create a placeholder
    const chartContainer = document.getElementById('dailyChart');

    // This would be replaced with actual charting library like Chart.js
    console.log('Chart data ready', dailyStats);

    // Example using a simple bar visualization
    const dates = Object.keys(dailyStats).sort();
    const netLines = dates.map(d => dailyStats[d].net_lines);

    // Create a simple SVG visualization
    createSimpleChart(chartContainer, dates, netLines);
}

function createSimpleChart(container, dates, values) {
    // Basic chart creation - replace with Chart.js for better visualization
    if (!values || values.length === 0) {
        container.innerHTML = '<p style="padding: 20px; text-align: center; color: #999;">No data available</p>';
        return;
    }

    const maxValue = Math.max(...values.map(Math.abs));
    if (maxValue === 0) {
        container.innerHTML = '<p style="padding: 20px; text-align: center; color: #999;">No data available</p>';
        return;
    }

    const width = Math.min(800, Math.max(400, dates.length * 20));
    const height = 300;
    const barWidth = width / dates.length;

    let svg = `<svg width="${width}" height="${height}" style="border: 1px solid #e0e0e0; display: block;">`;

    // Draw baseline
    svg += `<line x1="0" y1="${height/2}" x2="${width}" y2="${height/2}" stroke="#ccc" stroke-width="1"/>`;

    // Draw bars
    values.forEach((value, i) => {
        const barHeight = (value / maxValue) * (height / 2 - 20);
        const x = i * barWidth;
        const y = value >= 0 ?
            height / 2 - barHeight :
            height / 2;

        svg += `<rect x="${x + 2}" y="${y}" width="${barWidth - 4}" height="${Math.abs(barHeight)}"
                fill="${value >= 0 ? '#28a745' : '#dc3545'}" opacity="0.7"/>`;
    });

    svg += '</svg>';

    container.innerHTML = svg;
}

function updateLastUpdated(timestamp) {
    const element = document.getElementById('lastUpdated');
    if (timestamp) {
        const date = new Date(timestamp);
        element.textContent = `Updated: ${date.toLocaleString()}`;
    }
}

function formatNumber(num) {
    return num.toLocaleString();
}

function showError(message) {
    console.error(message);
    // TODO: Show toast or alert
}

function showSuccess(message) {
    console.log(message);
    // TODO: Show toast
}
