/**
 * JIRA Cycle Time Dashboard
 */

let chart = null;

document.addEventListener('DOMContentLoaded', () => {
    loadData();
});

async function loadData() {
    try {
        // Load overall stats and by-user stats in parallel
        const [statsResp, byUserResp] = await Promise.all([
            fetch('/api/jira/stats'),
            fetch('/api/jira/stats/by-user')
        ]);

        const stats = await statsResp.json();
        const byUser = await byUserResp.json();

        if (stats.error) {
            showError('summaryContent', stats.error);
            return;
        }

        renderSummary(stats);
        renderUserTable(byUser);
        renderChart(byUser);
    } catch (error) {
        console.error('Error loading data:', error);
        showError('summaryContent', error.message);
    }
}

function showError(elementId, message) {
    document.getElementById(elementId).innerHTML = `
        <div class="error-message">Failed to load data: ${message}</div>
    `;
}

function renderSummary(stats) {
    const container = document.getElementById('summaryContent');

    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; text-align: center;">
            <div class="stat-card">
                <div style="font-size: 2em; font-weight: bold; color: #1f6feb;">${formatNumber(stats.total_cycles)}</div>
                <div style="color: #666;">Total Cycles</div>
            </div>
            <div class="stat-card">
                <div style="font-size: 2em; font-weight: bold; color: #28a745;">${formatHours(stats.mean_hours)}</div>
                <div style="color: #666;">Mean Time</div>
            </div>
            <div class="stat-card">
                <div style="font-size: 2em; font-weight: bold; color: #6f42c1;">${formatHours(stats.median_hours)}</div>
                <div style="color: #666;">Median Time</div>
            </div>
            <div class="stat-card">
                <div style="font-size: 2em; font-weight: bold; color: #fd7e14;">${formatHours(stats.min_hours)} - ${formatHours(stats.max_hours)}</div>
                <div style="color: #666;">Min - Max</div>
            </div>
        </div>
    `;
}

function renderUserTable(byUser) {
    const tbody = document.getElementById('userTableBody');

    // Sort users by total cycles descending
    const sortedUsers = Object.entries(byUser)
        .filter(([email, _]) => email !== 'unassigned' && email !== 'null')
        .sort((a, b) => b[1].total_cycles - a[1].total_cycles);

    if (sortedUsers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No data available</td></tr>';
        return;
    }

    tbody.innerHTML = sortedUsers.map(([email, data]) => `
        <tr>
            <td class="month-cell">${formatEmail(email)}</td>
            <td>${formatNumber(data.total_cycles)}</td>
            <td>${formatHours(data.mean_hours)}</td>
            <td>${formatHours(data.median_hours)}</td>
            <td>${formatHours(data.min_hours)}</td>
            <td>${formatHours(data.max_hours)}</td>
        </tr>
    `).join('');
}

function renderChart(byUser) {
    // Sort users by mean cycle time and take top 20
    const sortedUsers = Object.entries(byUser)
        .filter(([email, data]) => email !== 'unassigned' && email !== 'null' && data.total_cycles >= 5)
        .sort((a, b) => b[1].mean_hours - a[1].mean_hours)
        .slice(0, 20);

    const labels = sortedUsers.map(([email, _]) => formatEmail(email));
    const meanValues = sortedUsers.map(([_, data]) => data.mean_hours);
    const medianValues = sortedUsers.map(([_, data]) => data.median_hours);

    const ctx = document.getElementById('cycleTimeChart').getContext('2d');

    if (chart) {
        chart.destroy();
    }

    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Mean (hours)',
                    data: meanValues,
                    backgroundColor: 'rgba(31, 111, 235, 0.7)',
                    borderColor: 'rgba(31, 111, 235, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Median (hours)',
                    data: medianValues,
                    backgroundColor: 'rgba(111, 66, 193, 0.7)',
                    borderColor: 'rgba(111, 66, 193, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: 'Cycle Time by User (users with 5+ cycles)',
                    font: {
                        size: 14
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatHours(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Hours'
                    }
                }
            }
        }
    });
}

function formatEmail(email) {
    if (!email || email === 'null') return 'Unknown';
    // Extract name from email (before @)
    const name = email.split('@')[0];
    // Convert to title case and replace dots/underscores with spaces
    return name
        .replace(/[._]/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
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
