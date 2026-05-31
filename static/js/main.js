/* ============================================================
   main.js – AJAX live stats, sidebar, toast, utilities
   ============================================================ */

'use strict';

// ── Sidebar Toggle ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('sidebarToggle');
    if (btn) {
        btn.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-collapsed');
            // Mobile
            const sb = document.getElementById('sidebar');
            if (sb) sb.classList.toggle('mobile-open');
        });
    }

    // Highlight active nav link
    const path = window.location.pathname;
    document.querySelectorAll('#sidebar .nav-link').forEach(link => {
        if (link.getAttribute('href') && path.startsWith(link.getAttribute('href')) && link.getAttribute('href') !== '/') {
            link.classList.add('active');
        } else if (path === '/' && link.getAttribute('href') === '/') {
            link.classList.add('active');
        }
    });

    // Init all Bootstrap toasts
    document.querySelectorAll('.toast').forEach(el => {
        new bootstrap.Toast(el, { delay: 5000 }).show();
    });
});

// ── Live Dashboard Stats ─────────────────────────────────────
let dashboardChartInstances = {};

async function refreshDashboardStats() {
    try {
        const resp = await fetch('/api/stats', { credentials: 'same-origin' });
        if (!resp.ok) return;
        const data = await resp.json();

        const map = {
            'stat-total-patients': data.total_patients,
            'stat-admitted': data.admitted_patients,
            'stat-discharged': data.discharged_patients,
            'stat-doctors': data.total_doctors,
            'stat-nurses': data.total_nurses,
            'stat-rooms': data.available_rooms,
            'stat-beds': data.available_beds,
            'stat-revenue': '₹' + Number(data.revenue).toLocaleString('en-IN', { minimumFractionDigits: 2 }),
        };

        Object.entries(map).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el && el.textContent !== String(val)) {
                el.style.transform = 'scale(1.08)';
                el.textContent = val;
                setTimeout(() => { el.style.transform = 'scale(1)'; }, 300);
            }
        });
    } catch (e) { /* silent */ }
}

// Refresh stats every 20 seconds on dashboard page
if (document.getElementById('stat-total-patients')) {
    refreshDashboardStats();
    setInterval(refreshDashboardStats, 20000);
}

// ── Bed Chart (Ward Occupancy) ───────────────────────────────
async function loadBedChart() {
    const canvas = document.getElementById('bedOccupancyChart');
    if (!canvas) return;
    try {
        const resp = await fetch('/api/beds', { credentials: 'same-origin' });
        if (!resp.ok) return;
        const wards = await resp.json();

        if (dashboardChartInstances['bed']) dashboardChartInstances['bed'].destroy();
        dashboardChartInstances['bed'] = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: wards.map(w => `${w.ward} (${w.type})`),
                datasets: [
                    { label: 'Occupied', data: wards.map(w => w.occupied), backgroundColor: '#f87171' },
                    { label: 'Available', data: wards.map(w => w.available), backgroundColor: '#4ade80' },
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' } },
                scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
            }
        });
    } catch (e) { /* silent */ }
}

// ── Admissions Line Chart (static demo data) ─────────────────
function initAdmissionsChart() {
    const canvas = document.getElementById('admissionsChart');
    if (!canvas) return;
    const days = [];
    const now = new Date();
    for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        days.push(d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }));
    }
    if (dashboardChartInstances['adm']) dashboardChartInstances['adm'].destroy();
    dashboardChartInstances['adm'] = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: days,
            datasets: [{
                label: 'Admissions',
                data: [4, 7, 3, 9, 5, 6, 8],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.12)',
                tension: 0.4, fill: true,
                pointBackgroundColor: '#6366f1',
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
        }
    });
}

// ── Department Doughnut ──────────────────────────────────────
function initDeptChart() {
    const canvas = document.getElementById('deptChart');
    if (!canvas) return;
    if (dashboardChartInstances['dept']) dashboardChartInstances['dept'].destroy();
    dashboardChartInstances['dept'] = new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'General'],
            datasets: [{
                data: [22, 17, 15, 20, 26],
                backgroundColor: ['#6366f1','#f59e0b','#10b981','#3b82f6','#f43f5e'],
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initAdmissionsChart();
    initDeptChart();
    loadBedChart();
    setInterval(loadBedChart, 20000);
});

// ── Print Helper ─────────────────────────────────────────────
function printPage() {
    window.print();
}

// ── Confirm Delete ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', e => {
            if (!confirm(form.dataset.confirm)) e.preventDefault();
        });
    });
});
