// Smart Customer Support Ticketing System - Frontend Application

class TicketingApp {
    constructor() {
        this.apiBase = '/api/v1';
        this.token = localStorage.getItem('token');
        this.currentUser = null;
        this.tickets = [];
        this.currentTicket = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
    }

    setupEventListeners() {
        // Auth forms
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('register-form').addEventListener('submit', (e) => this.handleRegister(e));
        document.getElementById('logout-btn').addEventListener('click', () => this.handleLogout());

        // Ticket forms
        document.getElementById('new-ticket-btn').addEventListener('click', () => this.showTicketForm());
        document.getElementById('cancel-ticket-btn').addEventListener('click', () => this.hideTicketForm());
        document.getElementById('ticket-form').addEventListener('submit', (e) => this.handleTicketSubmit(e));

        // Modal events
        document.getElementById('generate-ai-response-btn').addEventListener('click', () => this.generateAIResponse());
    }

    async checkAuthStatus() {
        if (this.token) {
            try {
                const response = await this.apiCall('/auth/me', 'GET');
                this.currentUser = response;
                this.showDashboard();
                this.loadTickets();
            } catch (error) {
                console.error('Auth check failed:', error);
                this.handleLogout();
            }
        } else {
            this.showAuthSection();
        }
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const url = `${this.apiBase}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (this.token) {
            options.headers['Authorization'] = `Bearer ${this.token}`;
        }

        if (data) {
            if (method === 'POST' && endpoint.includes('/login')) {
                // Handle form data for login
                options.body = new URLSearchParams(data);
                options.headers['Content-Type'] = 'application/x-www-form-urlencoded';
            } else {
                options.body = JSON.stringify(data);
            }
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API call failed');
        }

        return await response.json();
    }

    async handleLogin(e) {
        e.preventDefault();

        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await this.apiCall('/auth/login', 'POST', {
                username,
                password
            });

            this.token = response.access_token;
            localStorage.setItem('token', this.token);

            this.showToast('Login successful!', 'success');
            this.checkAuthStatus();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    }

    async handleRegister(e) {
        e.preventDefault();

        const email = document.getElementById('register-email').value;
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const full_name = document.getElementById('register-fullname').value;

        try {
            await this.apiCall('/auth/register', 'POST', {
                email,
                username,
                password,
                full_name
            });

            this.showToast('Registration successful! Please login.', 'success');

            // Switch to login tab
            document.getElementById('login-tab').click();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    }

    handleLogout() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('token');
        this.showAuthSection();
        this.showToast('Logged out successfully!', 'info');
    }

    showAuthSection() {
        document.getElementById('auth-section').style.display = 'block';
        document.getElementById('dashboard-section').style.display = 'none';
        document.getElementById('login-btn').style.display = 'inline-block';
        document.getElementById('logout-btn').style.display = 'none';
        document.getElementById('user-info').style.display = 'none';
    }

    showDashboard() {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('dashboard-section').style.display = 'block';
        document.getElementById('login-btn').style.display = 'none';
        document.getElementById('logout-btn').style.display = 'inline-block';
        document.getElementById('user-info').style.display = 'block';
        document.getElementById('username').textContent = this.currentUser.username;
    }

    showTicketForm() {
        document.getElementById('ticket-form-section').style.display = 'block';
        document.getElementById('ticket-title').focus();
    }

    hideTicketForm() {
        document.getElementById('ticket-form-section').style.display = 'none';
        document.getElementById('ticket-form').reset();
    }

    async handleTicketSubmit(e) {
        e.preventDefault();

        const title = document.getElementById('ticket-title').value;
        const description = document.getElementById('ticket-description').value;
        const priority = document.getElementById('ticket-priority').value;
        const category = document.getElementById('ticket-category').value;

        try {
            const ticketData = {
                title,
                description,
                priority,
                auto_categorize: !category
            };

            if (category) {
                ticketData.category = category;
            }

            await this.apiCall('/tickets/', 'POST', ticketData);

            this.showToast('Ticket created successfully!', 'success');
            this.hideTicketForm();
            this.loadTickets();
        } catch (error) {
            this.showToast(error.message, 'error');
        }
    }

    async loadTickets() {
        try {
            this.tickets = await this.apiCall('/tickets/');
            this.renderTickets();
        } catch (error) {
            console.error('Failed to load tickets:', error);
            this.showToast('Failed to load tickets', 'error');
        }
    }

    renderTickets() {
        const container = document.getElementById('tickets-container');

        if (this.tickets.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-inbox fa-3x mb-3"></i>
                    <p>No tickets found. Create your first ticket!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.tickets.map(ticket => `
            <div class="ticket-item" onclick="app.showTicketDetails(${ticket.id})">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-1">${ticket.title}</h6>
                    <div class="d-flex gap-2">
                        <span class="ticket-status ${ticket.status}">${ticket.status}</span>
                        <span class="ticket-priority ${ticket.priority}">${ticket.priority}</span>
                        ${ticket.category ? `<span class="ticket-category">${ticket.category}</span>` : ''}
                    </div>
                </div>
                <p class="mb-2 text-muted">${ticket.description.substring(0, 100)}${ticket.description.length > 100 ? '...' : ''}</p>
                <div class="ticket-meta">
                    <small>
                        <i class="fas fa-clock"></i> ${new Date(ticket.created_at).toLocaleDateString()}
                        ${ticket.auto_categorized ? '<i class="fas fa-robot ms-2" title="Auto-categorized"></i>' : ''}
                    </small>
                </div>
            </div>
        `).join('');
    }

    async showTicketDetails(ticketId) {
        try {
            this.currentTicket = await this.apiCall(`/tickets/${ticketId}`);
            this.renderTicketDetails();

            const modal = new bootstrap.Modal(document.getElementById('ticketModal'));
            modal.show();
        } catch (error) {
            this.showToast('Failed to load ticket details', 'error');
        }
    }

    renderTicketDetails() {
        const ticket = this.currentTicket;

        document.getElementById('ticket-details').innerHTML = `
            <div class="row">
                <div class="col-md-8">
                    <h5>${ticket.title}</h5>
                    <p class="text-muted">${ticket.description}</p>
                </div>
                <div class="col-md-4">
                    <div class="d-flex flex-column gap-2">
                        <span class="ticket-status ${ticket.status}">${ticket.status}</span>
                        <span class="ticket-priority ${ticket.priority}">${ticket.priority}</span>
                        ${ticket.category ? `<span class="ticket-category">${ticket.category}</span>` : ''}
                    </div>
                    <div class="mt-3">
                        <small class="text-muted">
                            Created: ${new Date(ticket.created_at).toLocaleString()}<br>
                            ${ticket.auto_categorized ? 'Auto-categorized with ' + Math.round(ticket.category_confidence * 100) + '% confidence' : ''}
                        </small>
                    </div>
                </div>
            </div>
        `;

        // Show AI response button for agents/admins
        const generateBtn = document.getElementById('generate-ai-response-btn');
        if (this.currentUser.role === 'agent' || this.currentUser.role === 'admin') {
            generateBtn.style.display = 'inline-block';
        } else {
            generateBtn.style.display = 'none';
        }
    }

    async generateAIResponse() {
        if (!this.currentTicket) return;

        const btn = document.getElementById('generate-ai-response-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="loading-spinner"></span> Generating...';
        btn.disabled = true;

        try {
            const response = await this.apiCall(`/tickets/${this.currentTicket.id}/generate-response`, 'POST');

            document.getElementById('ai-response-content').innerHTML = response.response;
            document.getElementById('ai-confidence').textContent = Math.round(response.confidence * 100);

            const confidenceSpan = document.getElementById('ai-confidence');
            const confidenceValue = response.confidence;

            if (confidenceValue >= 0.8) {
                confidenceSpan.className = 'ai-confidence high';
            } else if (confidenceValue >= 0.5) {
                confidenceSpan.className = 'ai-confidence medium';
            } else {
                confidenceSpan.className = 'ai-confidence low';
            }

            document.getElementById('ai-response-section').style.display = 'block';

            if (response.should_escalate) {
                this.showToast('Low confidence response - consider escalation', 'warning');
            } else {
                this.showToast('AI response generated successfully!', 'success');
            }
        } catch (error) {
            this.showToast('Failed to generate AI response', 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastBody = toast.querySelector('.toast-body');

        toastBody.textContent = message;

        // Update toast styling based on type
        toast.className = `toast ${type === 'error' ? 'bg-danger text-white' :
            type === 'success' ? 'bg-success text-white' :
                type === 'warning' ? 'bg-warning' : 'bg-info text-white'}`;

        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// Initialize the application
const app = new TicketingApp(); 