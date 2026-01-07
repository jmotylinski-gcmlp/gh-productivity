/**
 * Productivity Tracker Dashboard - Monthly Comparison
 */

let allUsersData = {};

document.addEventListener('DOMContentLoaded', () => {
    // Set default end date to current month
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    document.getElementById('endDate').value = currentMonth;

    loadAllUsersData();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('compareBtn').addEventListener('click', loadAllUsersData);

    // Allow Enter key to trigger comparison
    document.getElementById('user1').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') loadAllUsersData();
    });
    document.getElementById('user2').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') loadAllUsersData();
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

function getSelectedUsers() {
    const user1 = document.getElementById('user1').value.trim();
    const user2 = document.getElementById('user2').value.trim();
    return [user1, user2].filter(u => u.length > 0);
}

async function loadAllUsersData() {
    const container = document.getElementById('mainContent');
    const selectedUsers = getSelectedUsers();

    if (selectedUsers.length < 2) {
        container.innerHTML = `<div class="error-message">Please enter two usernames to compare.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading data...</p>
        </div>
    `;

    try {
        const resp = await fetch('/api/users/all/stats');
        allUsersData = await resp.json();

        if (allUsersData.error) {
            container.innerHTML = `<div class="error-message">${allUsersData.error}</div>`;
            return;
        }

        // Filter to only selected users
        const filteredData = {};
        const missingUsers = [];

        selectedUsers.forEach(username => {
            if (allUsersData[username]) {
                filteredData[username] = allUsersData[username];
            } else {
                missingUsers.push(username);
            }
        });

        if (missingUsers.length > 0) {
            container.innerHTML = `<div class="error-message">User(s) not found in cache: ${missingUsers.join(', ')}<br><br>Make sure the users are configured in config.json.</div>`;
            return;
        }

        renderMonthlyComparison(filteredData, selectedUsers);
    } catch (error) {
        console.error('Error loading data:', error);
        container.innerHTML = `<div class="error-message">Failed to load data: ${error.message}</div>`;
    }
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

function renderMonthlyComparison(usersData, selectedUsers) {
    const container = document.getElementById('mainContent');
    const usernames = selectedUsers || Object.keys(usersData);

    if (usernames.length === 0) {
        container.innerHTML = '<div class="error-message">No users configured.</div>';
        return;
    }

    // Aggregate monthly data for each user
    const monthlyByUser = {};
    const allMonths = new Set();

    usernames.forEach(username => {
        const dailyStats = usersData[username]?.daily_stats || {};
        monthlyByUser[username] = aggregateByMonth(dailyStats);
        Object.keys(monthlyByUser[username]).forEach(m => allMonths.add(m));
    });

    // Get date range and filter months
    const { startDate, endDate } = getDateRange();
    const months = Array.from(allMonths)
        .filter(m => m >= startDate && m <= endDate)
        .sort()
        .reverse();

    if (months.length === 0) {
        container.innerHTML = '<div class="error-message">No data available for the selected date range.</div>';
        return;
    }

    // Calculate totals for each user (only months in filtered range)
    const userTotals = {};
    usernames.forEach(username => {
        userTotals[username] = months.reduce((sum, month) => {
            const data = monthlyByUser[username][month];
            return sum + (data ? data.absolute : 0);
        }, 0);
    });

    // Find max total for indicator
    const maxTotal = Math.max(...Object.values(userTotals));

    // Helper to get indicator between two values with percentage
    function getIndicator(val1, val2) {
        if (val1 === 0 && val2 === 0) return '<span class="indicator">―</span>';
        if (val1 === val2) return '<span class="indicator">―</span>';

        const winner = Math.max(val1, val2);
        const loser = Math.min(val1, val2);
        const pct = loser > 0 ? Math.round(((winner - loser) / loser) * 100) : 100;

        if (val1 > val2) {
            return `<span class="indicator left">◀ ${pct}%</span>`;
        } else {
            return `<span class="indicator right">${pct}% ▶</span>`;
        }
    }

    // Build the comparison table (assumes 2 users)
    const user1 = usernames[0];
    const user2 = usernames[1];

    let html = `
        <div class="comparison-section">
            <h2>Lines Changed by Month</h2>
            <p class="table-subtitle">Total lines touched (additions + deletions)</p>
            <div class="table-wrapper">
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th class="month-col">Month</th>
                            <th class="user-col"><a href="user.html?username=${encodeURIComponent(user1)}&startDate=${startDate}&endDate=${endDate}" class="user-link">${formatUsername(user1)}</a></th>
                            <th class="indicator-col"></th>
                            <th class="user-col"><a href="user.html?username=${encodeURIComponent(user2)}&startDate=${startDate}&endDate=${endDate}" class="user-link">${formatUsername(user2)}</a></th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="totals-row">
                            <td><strong>TOTAL</strong></td>
                            <td class="${userTotals[user1] >= userTotals[user2] ? 'winner' : ''}">
                                <strong>${formatAbsolute(userTotals[user1])}</strong>
                            </td>
                            <td class="indicator-cell">${getIndicator(userTotals[user1], userTotals[user2])}</td>
                            <td class="${userTotals[user2] >= userTotals[user1] ? 'winner' : ''}">
                                <strong>${formatAbsolute(userTotals[user2])}</strong>
                            </td>
                        </tr>
                        ${months.map(month => {
                            const data1 = monthlyByUser[user1][month];
                            const data2 = monthlyByUser[user2][month];
                            const abs1 = data1 ? data1.absolute : 0;
                            const abs2 = data2 ? data2.absolute : 0;
                            return `
                                <tr>
                                    <td class="month-cell">${formatMonth(month)}</td>
                                    <td class="${abs1 > abs2 ? 'winner' : ''}">${abs1 > 0 ? formatAbsolute(abs1) : '-'}</td>
                                    <td class="indicator-cell">${getIndicator(abs1, abs2)}</td>
                                    <td class="${abs2 > abs1 ? 'winner' : ''}">${abs2 > 0 ? formatAbsolute(abs2) : '-'}</td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

function formatUsername(username) {
    // Remove common suffixes for cleaner display
    return username.replace(/-gcmlp$/, '').replace(/-gcm$/, '');
}

function formatMonth(monthStr) {
    const [year, month] = monthStr.split('-');
    const date = new Date(year, parseInt(month) - 1);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
}

function formatAbsolute(num) {
    return num.toLocaleString();
}
